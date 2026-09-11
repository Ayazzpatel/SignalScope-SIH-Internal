// Mirrors backend Pydantic schemas (app/backend/signalscope/schemas).

export interface HealthResponse {
  status: 'ok' | 'degraded'
  version: string
  environment: string
  detector: 'mock' | 'ml'
  detector_ready: boolean
  model_version: string
  database: 'ok' | 'unavailable'
  demo_accounts: boolean
}

export type VerdictBand = 'likely_real' | 'uncertain' | 'likely_ai'

export type CueType =
  | 'frequency_artifact'
  | 'texture_inconsistency'
  | 'lighting_inconsistency'
  | 'geometry_error'
  | 'warped_text'
  | 'anatomical_error'
  | 'noise_residual'
  | 'other'

/** Normalised [x, y, w, h] in 0–1, relative to image width/height. */
export type Region = [number, number, number, number]

export interface Cue {
  type: CueType
  description: string
  region: Region | null
  strength: number
}

export interface Attribution {
  family: 'diffusion' | 'gan' | 'other'
  confidence: number
}

export interface Verdict {
  band: VerdictBand
  prob_ai: number
  headline: string
  summary: string
  thresholds: { likely_real_max: number; likely_ai_min: number }
}

export type SignalSource = 'c2pa' | 'xmp' | 'exif' | 'embedded_text' | 'none'
export type SignalDirection = 'ai' | 'real' | 'neutral'

export interface ProvenanceSignal {
  source: SignalSource
  direction: SignalDirection
  message: string
}

export interface ExifInfo {
  present: boolean
  camera_make: string | null
  camera_model: string | null
  lens_model: string | null
  software: string | null
  captured_at: string | null
  has_gps: boolean
}

export interface C2PAInfo {
  present: boolean
  checked: boolean
  validation_state: string | null
  claim_generator: string | null
  signer: string | null
  signed_at: string | null
  actions: string[]
  digital_source_types: string[]
  error: string | null
}

export interface Provenance {
  exif: ExifInfo
  c2pa: C2PAInfo
  signals: ProvenanceSignal[]
  agreement: 'agrees' | 'conflicts' | 'model_uncertain' | 'no_evidence'
  agreement_note: string | null
}

export interface AnalysisResponse {
  request_id: string
  detector: 'mock' | 'ml'
  model_version: string
  verdict: Verdict
  explanation: { heatmap_png: string | null; cues: Cue[] }
  attribution: Attribution | null
  provenance: Provenance
  image: { width: number; height: number; format: string; size_bytes: number; sha256: string }
  timings: { inference_ms: number; total_ms: number }
  disclaimer: string
}

export interface ApiErrorBody {
  error: { code: string; message: string; request_id: string | null; field?: string }
}
