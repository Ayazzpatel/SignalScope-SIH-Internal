import { BAND_SHORT, BAND_STYLES } from '../../lib/presentation.ts'
import type { ScanStats, VerdictBand } from '../../types/api.ts'

const ORDER: VerdictBand[] = ['likely_ai', 'uncertain', 'likely_real']

/** Totals plus a distribution bar of verdicts across the whole history. */
export function StatsStrip({ stats }: { stats: ScanStats }) {
  const total = Math.max(stats.total, 1)

  return (
    <section className="panel grid gap-5 p-5 sm:grid-cols-[auto_auto_1fr] sm:items-center sm:gap-10" aria-label="History totals">
      <div>
        <span className="label">Scans</span>
        <p className="mt-2 font-mono text-4xl leading-none font-medium tracking-tight tabular-nums">{stats.total}</p>
      </div>
      <div>
        <span className="label">This week</span>
        <p className="mt-2 font-mono text-4xl leading-none font-medium tracking-tight tabular-nums">{stats.this_week}</p>
      </div>
      <div className="min-w-0">
        <div
          className="flex h-2 overflow-hidden rounded-full bg-raise"
          role="img"
          aria-label={ORDER.map((b) => `${BAND_SHORT[b]}: ${stats.by_band[b]}`).join(', ')}
        >
          {ORDER.map((band) => (
            <div key={band} className={BAND_STYLES[band].fill} style={{ width: `${(stats.by_band[band] / total) * 100}%` }} />
          ))}
        </div>
        <div className="mt-2.5 flex flex-wrap gap-x-5 gap-y-1">
          {ORDER.map((band) => (
            <span key={band} className="inline-flex items-center gap-2 font-mono text-[11px] tracking-[0.06em] text-mute uppercase">
              <span className={`size-2 rounded-full ${BAND_STYLES[band].fill}`} aria-hidden />
              {BAND_SHORT[band]} <b className="font-medium text-text tabular-nums">{stats.by_band[band]}</b>
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
