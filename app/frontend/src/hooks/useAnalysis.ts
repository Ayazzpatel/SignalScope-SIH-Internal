import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, api } from '../lib/api.ts'
import type { AnalysisResponse } from '../types/api.ts'

export type AnalysisState =
  | { kind: 'idle'; error: string | null }
  | { kind: 'analyzing'; file: File; previewUrl: string }
  | { kind: 'done'; file: File; previewUrl: string; result: AnalysisResponse }

export function useAnalysis() {
  const [state, setState] = useState<AnalysisState>({ kind: 'idle', error: null })
  const controllerRef = useRef<AbortController | null>(null)
  const previewRef = useRef<string | null>(null)

  const releasePreview = () => {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current)
    previewRef.current = null
  }

  const reset = useCallback((error: string | null = null) => {
    controllerRef.current?.abort()
    releasePreview()
    setState({ kind: 'idle', error })
  }, [])

  /** `saveImage` only matters for signed-in users; guests are never stored. */
  const analyze = useCallback(async (file: File, saveImage?: boolean) => {
    controllerRef.current?.abort()
    releasePreview()
    const controller = new AbortController()
    controllerRef.current = controller
    const previewUrl = URL.createObjectURL(file)
    previewRef.current = previewUrl
    setState({ kind: 'analyzing', file, previewUrl })

    try {
      const result = await api.analyze(file, { saveImage, signal: controller.signal })
      setState({ kind: 'done', file, previewUrl, result })
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      releasePreview()
      const message = err instanceof ApiError ? err.message : 'Something went wrong. Please try again.'
      setState({ kind: 'idle', error: message })
    }
  }, [])

  useEffect(
    () => () => {
      controllerRef.current?.abort()
      releasePreview()
    },
    [],
  )

  return { state, analyze, reset }
}
