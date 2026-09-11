import { Scale } from 'lucide-react'
import { SIGNAL_SOURCE_LABELS } from '../../lib/presentation.ts'
import type { Provenance, SignalDirection } from '../../types/api.ts'

const DIRECTION_DOT: Record<SignalDirection, { dot: string; label: string }> = {
  ai: { dot: 'bg-ai', label: 'Points to AI' },
  real: { dot: 'bg-real', label: 'Points to real' },
  neutral: { dot: 'bg-faint', label: 'Neutral' },
}

const AGREEMENT_TONE = {
  agrees: 'border-signal/35 text-text',
  conflicts: 'border-unsure/50 text-text',
  model_uncertain: 'border-line-strong text-text',
} as const

function Row({ term, value }: { term: string; value: string | null }) {
  return (
    <div className="grid grid-cols-[112px_1fr] gap-3 border-b border-line py-2.5 text-[13.5px] sm:odd:pr-5 sm:even:border-l sm:even:pl-5">
      <dt className="font-mono text-[11px] leading-6 tracking-[0.08em] text-faint uppercase">{term}</dt>
      <dd className={`min-w-0 break-words ${value ? 'text-text' : 'text-mute'}`}>{value ?? '—'}</dd>
    </div>
  )
}

export function ProvenancePanel({ provenance }: { provenance: Provenance }) {
  const { exif, c2pa, signals, agreement, agreement_note } = provenance
  const camera = [exif.camera_make, exif.camera_model].filter(Boolean).join(' ') || null
  const credentials = !c2pa.present
    ? 'Not present'
    : !c2pa.checked
      ? 'Found — could not be read'
      : `${c2pa.validation_state ?? 'Unknown'}${c2pa.claim_generator ? ` · ${c2pa.claim_generator}` : ''}`

  return (
    <section className="panel p-5 sm:p-6" aria-labelledby="provenance-heading">
      <h3 id="provenance-heading" className="label">
        Provenance · specimen sheet
      </h3>

      <dl className="mt-4 grid border-t border-line sm:grid-cols-2">
        <Row term="Credentials" value={credentials} />
        <Row term="Signed by" value={c2pa.present ? c2pa.signer : null} />
        <Row term="Camera" value={camera} />
        <Row term="Software" value={exif.software} />
        <Row term="Captured" value={exif.captured_at} />
        <Row term="Location" value={exif.has_gps ? 'In file · hidden for privacy' : exif.present ? 'No GPS data' : null} />
      </dl>

      {agreement !== 'no_evidence' && agreement_note && (
        <p className={`mt-4 flex gap-2.5 rounded-sm border px-3 py-2.5 text-[13.5px] ${AGREEMENT_TONE[agreement]}`}>
          <Scale className="mt-0.5 size-4 shrink-0 text-mute" aria-hidden />
          {agreement_note}
        </p>
      )}

      <ul className="mt-4 grid gap-2">
        {signals.map((signal, index) => (
          <li key={index} className="flex gap-2.5 text-[13.5px] text-mute">
            <span
              className={`mt-[7px] size-2 shrink-0 rounded-full ${DIRECTION_DOT[signal.direction].dot}`}
              role="img"
              aria-label={DIRECTION_DOT[signal.direction].label}
            />
            <span>
              <span className="text-text">{SIGNAL_SOURCE_LABELS[signal.source]} — </span>
              {signal.message}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
