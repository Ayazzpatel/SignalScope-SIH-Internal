import { Cpu } from 'lucide-react'
import type { Ref } from 'react'
import { useCountUp } from '../../hooks/useCountUp.ts'
import { ATTRIBUTION_LABELS, BAND_STYLES, percent } from '../../lib/presentation.ts'
import type { Attribution, Verdict } from '../../types/api.ts'
import { ConfidenceMeter } from './ConfidenceMeter.tsx'

interface VerdictCardProps {
  verdict: Verdict
  attribution: Attribution | null
  headingRef?: Ref<HTMLHeadingElement>
}

export function VerdictCard({ verdict, attribution, headingRef }: VerdictCardProps) {
  const style = BAND_STYLES[verdict.band]
  const Icon = style.icon
  const reading = useCountUp(verdict.prob_ai)

  return (
    <section className="panel p-5 sm:p-6" aria-labelledby="verdict-heading">
      <span className="label">Reading · AI likelihood</span>
      <p className="mt-3.5 flex items-baseline gap-2" aria-hidden>
        <span className="font-mono text-[clamp(64px,8vw,104px)] leading-[0.9] font-medium tracking-[-0.06em] tabular-nums">
          {Math.round(reading * 100)}
        </span>
        <span className="font-mono text-[22px] text-mute">%</span>
      </p>

      <h2
        id="verdict-heading"
        ref={headingRef}
        tabIndex={-1}
        className={`mt-4 flex items-center gap-2.5 text-[26px] font-semibold tracking-[-0.025em] focus:outline-none ${style.text}`}
      >
        <Icon className="size-6.5 shrink-0" aria-hidden />
        {verdict.headline}
        <span className="sr-only"> — {percent(verdict.prob_ai)} likelihood of being AI-generated</span>
      </h2>
      <p className="mt-2 max-w-[42ch] text-[14.5px] text-mute">{verdict.summary}</p>

      <div className="mt-6">
        <ConfidenceMeter verdict={verdict} position={reading} />
      </div>

      {attribution && verdict.band !== 'likely_real' && (
        <p className="mt-5 flex items-center gap-2.5 border-t border-line pt-4 text-[13.5px] text-mute">
          <Cpu className="size-4 shrink-0" aria-hidden />
          <span>
            Artefact pattern consistent with a <b className="font-medium text-text">{ATTRIBUTION_LABELS[attribution.family]}</b>{' '}
            generator · {percent(attribution.confidence)}
          </span>
        </p>
      )}
    </section>
  )
}
