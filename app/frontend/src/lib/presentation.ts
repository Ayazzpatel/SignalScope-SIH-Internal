import {
  Activity,
  Grid3x3,
  PersonStanding,
  Shapes,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestionMark,
  Sparkles,
  Sun,
  Type,
  Waves,
  type LucideIcon,
} from 'lucide-react'
import type { Attribution, CueType, SignalSource, VerdictBand } from '../types/api.ts'

export const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'] as const
export const MAX_UPLOAD_MB = 20

interface BandStyle {
  icon: LucideIcon
  /** Verdict text / icon colour */
  text: string
  /** Solid fill (chips, markers) */
  fill: string
  /** Soft segment fill for the meter track */
  track: string
}

// Sky / amber / coral: distinguishable with red–green colour blindness, and always paired with an icon + word.
export const BAND_STYLES: Record<VerdictBand, BandStyle> = {
  likely_ai: { icon: ShieldAlert, text: 'text-ai', fill: 'bg-ai', track: 'bg-ai/45' },
  uncertain: { icon: ShieldQuestionMark, text: 'text-unsure', fill: 'bg-unsure', track: 'bg-unsure/45' },
  likely_real: { icon: ShieldCheck, text: 'text-real', fill: 'bg-real', track: 'bg-real/45' },
}

interface CueStyle {
  label: string
  icon: LucideIcon
}

export const CUE_STYLES: Record<CueType, CueStyle> = {
  frequency_artifact: { label: 'Frequency artefacts', icon: Waves },
  texture_inconsistency: { label: 'Unnatural texture', icon: Grid3x3 },
  lighting_inconsistency: { label: 'Lighting mismatch', icon: Sun },
  geometry_error: { label: 'Impossible geometry', icon: Shapes },
  warped_text: { label: 'Warped text', icon: Type },
  anatomical_error: { label: 'Anatomical error', icon: PersonStanding },
  noise_residual: { label: 'Missing sensor noise', icon: Activity },
  other: { label: 'Other cue', icon: Sparkles },
}

export const SIGNAL_SOURCE_LABELS: Record<SignalSource, string> = {
  c2pa: 'Content Credentials',
  xmp: 'IPTC / XMP',
  exif: 'EXIF',
  embedded_text: 'Embedded text',
  none: 'Metadata',
}

export const ATTRIBUTION_LABELS: Record<Attribution['family'], string> = {
  diffusion: 'diffusion-model',
  gan: 'GAN',
  other: 'other generator',
}

/** Instrument tags for cues: localised cues get R1, R2… in order; whole-image cues get ALL. */
export function cueTags(cues: { region: unknown }[]): string[] {
  let n = 0
  return cues.map((cue) => (cue.region ? `R${++n}` : 'ALL'))
}

export function percent(value: number): string {
  return `${Math.round(value * 100)}%`
}

export function strengthLabel(value: number): string {
  if (value >= 0.7) return 'Strong'
  if (value >= 0.4) return 'Moderate'
  return 'Weak'
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function validateFile(file: File): string | null {
  if (!(ACCEPTED_TYPES as readonly string[]).includes(file.type)) {
    return 'Please choose a JPEG, PNG or WebP image.'
  }
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
    return `That file is ${formatBytes(file.size)}. The limit is ${MAX_UPLOAD_MB} MB.`
  }
  if (file.size === 0) return 'That file is empty.'
  return null
}
