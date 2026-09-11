import type { HealthResponse } from '../types/api.ts'

const API_BASE = '/api/v1'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { credentials: 'include', ...init })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.detail ?? response.statusText)
  }
  return response.json() as Promise<T>
}

export const api = {
  health: (signal?: AbortSignal) => request<HealthResponse>('/health', { signal }),
}
