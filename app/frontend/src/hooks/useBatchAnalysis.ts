import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, api } from '../lib/api.ts'
import type { EnsembleAnalysisResponse } from '../types/api.ts'

export interface BatchItem {
  id: string
  file: File
  previewUrl: string
  status: 'queued' | 'analyzing' | 'done' | 'error'
  result?: EnsembleAnalysisResponse
  error?: string
}

export type BatchState =
  | { kind: 'idle'; error: string | null }
  | { kind: 'batch'; items: BatchItem[]; activeId: string }

let _nextId = 1
const nextId = () => String(_nextId++)

export function useBatchAnalysis() {
  const [state, setState] = useState<BatchState>({ kind: 'idle', error: null })
  const controllerRef = useRef<AbortController | null>(null)
  const previewUrls = useRef<Set<string>>(new Set())

  const releaseAll = () => {
    previewUrls.current.forEach((u) => URL.revokeObjectURL(u))
    previewUrls.current.clear()
  }

  const reset = useCallback((error: string | null = null) => {
    controllerRef.current?.abort()
    releaseAll()
    setState({ kind: 'idle', error })
  }, [])

  /** Process one item in the batch queue. */
  const processNext = useCallback(async (items: BatchItem[]) => {
    const queuedIndex = items.findIndex((i) => i.status === 'queued')
    if (queuedIndex === -1) return

    const item = items[queuedIndex]
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    // Mark as analyzing
    setState((prev) => {
      if (prev.kind !== 'batch') return prev
      const next = prev.items.map((i) =>
        i.id === item.id ? { ...i, status: 'analyzing' as const } : i,
      )
      return { kind: 'batch', items: next, activeId: item.id }
    })

    try {
      const result = await api.analyzeEnsemble(item.file, controller.signal)
      setState((prev) => {
        if (prev.kind !== 'batch') return prev
        const next = prev.items.map((i) =>
          i.id === item.id ? { ...i, status: 'done' as const, result } : i,
        )
        // Auto-advance active to first unfinished or stay on current
        const nextQueued = next.find((i) => i.status === 'queued')
        const nextActive = nextQueued?.id ?? item.id
        // kick off next item
        const queuedItems = next.filter((i) => i.status === 'queued')
        if (queuedItems.length > 0) setTimeout(() => processNext(next), 0)
        return { kind: 'batch', items: next, activeId: nextActive }
      })
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      const message = err instanceof ApiError ? err.message : 'Something went wrong.'
      setState((prev) => {
        if (prev.kind !== 'batch') return prev
        const next = prev.items.map((i) =>
          i.id === item.id ? { ...i, status: 'error' as const, error: message } : i,
        )
        const queuedItems = next.filter((i) => i.status === 'queued')
        if (queuedItems.length > 0) setTimeout(() => processNext(next), 0)
        return { kind: 'batch', items: next, activeId: item.id }
      })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  /** Add one or more files to the batch and start processing. */
  const addFiles = useCallback(
    (files: File[]) => {
      const newItems: BatchItem[] = files.map((file) => {
        const previewUrl = URL.createObjectURL(file)
        previewUrls.current.add(previewUrl)
        return { id: nextId(), file, previewUrl, status: 'queued' as const }
      })

      setState((prev) => {
        if (prev.kind === 'idle') {
          setTimeout(() => processNext(newItems), 0)
          return { kind: 'batch', items: newItems, activeId: newItems[0].id }
        }
        // Already in batch — append; only kick off if nothing is currently running
        const items = [...prev.items, ...newItems]
        const isIdle = !prev.items.some((i) => i.status === 'analyzing' || i.status === 'queued')
        if (isIdle) setTimeout(() => processNext(items), 0)
        return { kind: 'batch', items, activeId: prev.activeId }
      })
    },
    [processNext],
  )

  const setActive = useCallback((id: string) => {
    setState((prev) => {
      if (prev.kind !== 'batch') return prev
      return { ...prev, activeId: id }
    })
  }, [])

  useEffect(
    () => () => {
      controllerRef.current?.abort()
      releaseAll()
    },
    [],
  )

  return { state, addFiles, setActive, reset }
}
