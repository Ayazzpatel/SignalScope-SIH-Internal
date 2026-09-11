// Mirrors backend Pydantic schemas (app/backend/signalscope/schemas).

export interface HealthResponse {
  status: 'ok' | 'degraded'
  version: string
  environment: string
  detector: 'mock' | 'ml'
  detector_ready: boolean
  model_version: string
}
