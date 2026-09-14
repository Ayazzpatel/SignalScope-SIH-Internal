import { Check } from 'lucide-react'
import { Link } from 'react-router'
import { BAND_SHORT, BAND_STYLES, percent } from '../../lib/presentation.ts'
import { formatDate } from '../../lib/navigation.ts'
import type { ScanSummary } from '../../types/api.ts'

interface ScanCardProps {
  scan: ScanSummary
  selecting: boolean
  selected: boolean
  onToggle: (id: string) => void
}

/** Contact-sheet frame: thumbnail (or blank specimen), verdict chip, reading, filename and date. */
export function ScanCard({ scan, selecting, selected, onToggle }: ScanCardProps) {
  const style = BAND_STYLES[scan.band]
  const name = scan.filename ?? 'Untitled image'

  const body = (
    <>
      <div className="relative aspect-[4/3] overflow-hidden rounded-sm bg-black">
        {scan.image_url ? (
          <img
            src={scan.image_url}
            alt=""
            loading="lazy"
            className="size-full object-cover opacity-90 transition-opacity group-hover:opacity-100"
          />
        ) : (
          <div className="scope-grid grid size-full place-items-center">
            <span className="label">Result only</span>
          </div>
        )}
        <span className="absolute top-2 left-2 inline-flex items-center gap-1.5 rounded-[2px] bg-ink/85 px-1.5 py-1 font-mono text-[10.5px] leading-none tracking-wide uppercase">
          <span className={`size-1.5 rounded-full ${style.fill}`} aria-hidden />
          <span className={style.text}>{BAND_SHORT[scan.band]}</span>
        </span>
        {selecting && (
          <span
            className={`absolute top-2 right-2 grid size-5 place-items-center rounded-[3px] border ${
              selected ? 'border-signal bg-signal text-ink' : 'border-white/70 bg-ink/60'
            }`}
            aria-hidden
          >
            {selected && <Check className="size-3.5" />}
          </span>
        )}
      </div>
      <div className="mt-3 flex items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium" title={name}>
            {name}
          </p>
          <p className="mt-0.5 font-mono text-[11px] text-faint">
            {formatDate(scan.created_at)} · {scan.width}×{scan.height}
          </p>
        </div>
        <span className="font-mono text-2xl leading-none font-medium tracking-tight tabular-nums">{percent(scan.prob_ai)}</span>
      </div>
    </>
  )

  const frame = `group panel block p-3 text-left transition-colors hover:border-line-strong ${
    selected ? 'border-signal hover:border-signal' : ''
  }`

  if (selecting) {
    return (
      <button type="button" aria-pressed={selected} onClick={() => onToggle(scan.id)} className={frame}>
        <span className="sr-only">{selected ? 'Deselect' : 'Select'} </span>
        {body}
      </button>
    )
  }
  return (
    <Link to={`/history/${scan.id}`} className={frame} aria-label={`${name} — ${BAND_SHORT[scan.band]}, ${percent(scan.prob_ai)}`}>
      {body}
    </Link>
  )
}
