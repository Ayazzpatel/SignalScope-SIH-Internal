import { BAND_STYLES, percent } from '../../lib/presentation.ts'
import type { Verdict } from '../../types/api.ts'

export function ConfidenceMeter({ verdict, position }: { verdict: Verdict; position: number }) {
  const { likely_real_max: realMax, likely_ai_min: aiMin } = verdict.thresholds
  const clamped = Math.min(Math.max(position, 0), 1) * 100

  return (
    <div>
      <div
        className="relative flex h-2"
        role="meter"
        aria-label="Likelihood the image is AI-generated"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(verdict.prob_ai * 100)}
        aria-valuetext={`${percent(verdict.prob_ai)} — ${verdict.headline}`}
      >
        <div className={`rounded-l-full ${BAND_STYLES.likely_real.track}`} style={{ width: `${realMax * 100}%` }} />
        <div className={BAND_STYLES.uncertain.track} style={{ width: `${(aiMin - realMax) * 100}%` }} />
        <div className={`flex-1 rounded-r-full ${BAND_STYLES.likely_ai.track}`} />
        <div
          className="absolute top-1/2 h-5.5 w-[3px] -translate-x-1/2 -translate-y-1/2 rounded-sm bg-text shadow-[0_0_0_3px_var(--color-panel)]"
          style={{ left: `${clamped}%` }}
          aria-hidden
        />
      </div>
      <div className="mt-2.5 flex font-mono text-[10.5px] tracking-[0.08em] text-faint uppercase" aria-hidden>
        <span style={{ width: `${realMax * 100}%` }}>Likely real</span>
        <span className="text-center" style={{ width: `${(aiMin - realMax) * 100}%` }}>
          Uncertain
        </span>
        <span className="flex-1 text-right">Likely AI</span>
      </div>
    </div>
  )
}
