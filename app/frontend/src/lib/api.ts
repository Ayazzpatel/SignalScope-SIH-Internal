import type {
  AnalysisResponse,
  ApiErrorBody,
  HealthResponse,
  ScanDetail,
  ScanListResponse,
  ScanQuery,
  ScanStats,
} from '../types/api.ts'
import type {
  AuthResponse,
  MessageResponse,
  RetentionDays,
  SessionInfo,
  SessionStateResponse,
  User,
} from '../types/auth.ts'

const API_BASE = '/api/v1'

/** Fired when the session can no longer be refreshed; AuthProvider listens and switches to guest. */
export const SESSION_EXPIRED_EVENT = 'signalscope:session-expired'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly field: string | null
  readonly requestId: string | null

  constructor(status: number, code: string, message: string, field: string | null = null, requestId: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.field = field
    this.requestId = requestId
  }
}

let refreshInFlight: Promise<boolean> | null = null

/** Rotate the session once, shared by all concurrent callers (avoids refresh stampedes). */
function refreshSession(): Promise<boolean> {
  refreshInFlight ??= fetch(`${API_BASE}/auth/refresh`, { method: 'POST', credentials: 'include' })
    .then(async (response) => {
      if (response.ok) return true
      const body = (await response.json().catch(() => null)) as Partial<ApiErrorBody> | null
      // Another tab rotated a moment ago; the shared cookie jar already holds the new tokens.
      return body?.error?.code === 'token_rotated'
    })
    .catch(() => false)
    .finally(() => {
      refreshInFlight = null
    })
  return refreshInFlight
}

async function request<T>(path: string, init: RequestInit = {}, allowRefresh = true): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { credentials: 'include', ...init })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiError(0, 'network_error', 'Could not reach the SignalScope server. Check your connection.')
  }

  if (response.ok) {
    return (response.status === 204 ? undefined : await response.json()) as T
  }

  const body = (await response.json().catch(() => null)) as Partial<ApiErrorBody> | null
  const error = new ApiError(
    response.status,
    body?.error?.code ?? 'http_error',
    body?.error?.message ?? `Request failed (${response.status}).`,
    body?.error?.field ?? null,
    body?.error?.request_id ?? response.headers.get('X-Request-ID'),
  )

  if (response.status === 401 && error.code === 'token_expired' && allowRefresh) {
    if (await refreshSession()) return request<T>(path, init, false)
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
  }
  throw error
}

function json(method: string, body?: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  }
}

export const api = {
  health: (signal?: AbortSignal) => request<HealthResponse>('/health', { signal }),

  analyze: (file: File, options: { saveImage?: boolean; signal?: AbortSignal } = {}) => {
    const form = new FormData()
    form.append('file', file)
    if (options.saveImage !== undefined) form.append('save_image', String(options.saveImage))
    return request<AnalysisResponse>('/analyze', { method: 'POST', body: form, signal: options.signal })
  },

  scans: {
    list: (query: ScanQuery = {}, signal?: AbortSignal) => {
      const params = new URLSearchParams()
      for (const [key, value] of Object.entries(query)) {
        if (value !== undefined && value !== '') params.set(key, String(value))
      }
      const qs = params.toString()
      return request<ScanListResponse>(`/scans${qs ? `?${qs}` : ''}`, { signal })
    },
    stats: () => request<ScanStats>('/scans/stats'),
    get: (id: string) => request<ScanDetail>(`/scans/${id}`),
    remove: (id: string) => request<MessageResponse>(`/scans/${id}`, json('DELETE')),
    removeMany: (ids: string[]) => request<{ deleted: number }>('/scans/bulk-delete', json('POST', { ids })),
    removeAll: () => request<{ deleted: number }>('/scans', json('DELETE')),
  },

  account: {
    updatePreferences: (body: { save_images_default?: boolean; retention_days?: RetentionDays | null }) =>
      request<User>('/account/preferences', json('PATCH', body)),
    exportData: () => request<unknown>('/account/export'),
    deleteAccount: (password: string) => request<MessageResponse>('/account/delete', json('POST', { password })),
  },

  auth: {
    session: () => request<SessionStateResponse>('/auth/session'),
    signup: (body: { email: string; password: string; display_name: string }) =>
      request<AuthResponse>('/auth/signup', json('POST', body)),
    login: (body: { email: string; password: string; remember: boolean }) =>
      request<AuthResponse>('/auth/login', json('POST', body)),
    logout: () => request<MessageResponse>('/auth/logout', json('POST')),
    logoutAll: () => request<MessageResponse>('/auth/logout-all', json('POST')),
    updateProfile: (body: { display_name: string }) => request<User>('/auth/me', json('PATCH', body)),
    changePassword: (body: { current_password: string; new_password: string }) =>
      request<MessageResponse>('/auth/change-password', json('POST', body)),
    sessions: () => request<{ sessions: SessionInfo[] }>('/auth/sessions'),
    revokeSession: (id: string) => request<MessageResponse>(`/auth/sessions/${id}`, json('DELETE')),
  },
}
