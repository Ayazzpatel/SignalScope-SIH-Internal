import { useEffect, useState } from 'react'
import { api } from '../lib/api.ts'
import type { HealthResponse } from '../types/api.ts'

type HealthState =
  | { kind: 'loading' }
  | { kind: 'online'; data: HealthResponse }
  | { kind: 'offline' }

const POLL_MS = 30_000

export function useHealth(): HealthState {
  const [state, setState] = useState<HealthState>({ kind: 'loading' })

  useEffect(() => {
    let controller = new AbortController()

    const check = () => {
      controller.abort()
      controller = new AbortController()
      api
        .health(controller.signal)
        .then((data) => setState({ kind: 'online', data }))
        .catch((err: unknown) => {
          if (!(err instanceof DOMException && err.name === 'AbortError')) setState({ kind: 'offline' })
        })
    }

    check()
    const timer = window.setInterval(check, POLL_MS)
    return () => {
      window.clearInterval(timer)
      controller.abort()
    }
  }, [])

  return state
}
