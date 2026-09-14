import { Cpu } from 'lucide-react'
import type { Ref } from 'react'
import { useCountUp } from '../../hooks/useCountUp.ts'
import { ATTRIBUTION_LABELS, BAND_STYLES, percent } from '../../lib/presentation.ts'
import type { Attribution, Verdict } from '../../types/api.ts'
import { ConfidenceMeter } from './ConfidenceMeter.tsx'

function roundProb(v: number): number {
  return Math.round(v * 10000) / 10000
}

interface VerdictCardProps {
  verdict: Verdict
  attribution: Attribution | null
  headingRef?: Ref<HTMLHeadingElement>
  label?: string
  aiProbability?: number
  realProbability?: number
  confidence?: number
  title?: string
}

export function VerdictCard({
  verdict,
  attribution,
  headingRef,
  label,
  aiProbability,
  realProbability,
  confidence,
  title,
}: VerdictCardProps) {
  const style = BAND_STYLES[verdict.band]
  const Icon = style.icon
  const effectiveAiProb = aiProbability !== undefined ? aiProbability : verdict.prob_ai
  const effectiveRealProb = realProbability !== undefined ? realProbability : roundProb(1 - effectiveAiProb)
  const effectiveConfidence = confidence !== undefined ? confidence : Math.max(effectiveAiProb, effectiveRealProb)
  const effectiveLabel = label || (effectiveAiProb >= 0.5 ? 'AI-generated' : 'Real')

  const reading = useCountUp(effectiveAiProb)

  return (
    <section className="panel p-5 sm:p-6" aria-labelledby="verdict-heading">
      <div className="flex items-center justify-between">
        <span className="label">{title || 'Reading · AI likelihood'}</span>
        <span
          className={`inline-flex items-center rounded-sm px-2.5 py-0.5 font-mono text-[12px] font-semibold tracking-wide uppercase ${
            effectiveLabel === 'AI-generated'
              ? 'bg-ai/15 text-ai border border-ai/30'
              : 'bg-real/15 text-real border border-real/30'
          }`}
        >
          {effectiveLabel}
        </span>
      </div>

      <p className="mt-3.5 flex items-baseline gap-2" aria-hidden>
        <span className="font-mono text-[clamp(64px,8vw,104px)] leading-[0.9] font-medium tracking-[-0.06em] tabular-nums">
          {Math.round(reading * 100)}
        </span>
        <span className="font-mono text-[22px] text-mute">%</span>
      </p>

      {/* Probabilities and Confidence breakdown */}
      <div className="mt-4 grid grid-cols-3 gap-2 border-y border-line py-3">
        <div>
          <span className="font-mono text-[10.5px] uppercase tracking-wider text-faint">AI Prob</span>
          <p className="font-mono text-[15px] font-semibold text-text">
            {(effectiveAiProb * 100).toFixed(1)}%
          </p>
        </div>
        <div>
          <span className="font-mono text-[10.5px] uppercase tracking-wider text-faint">Real Prob</span>
          <p className="font-mono text-[15px] font-semibold text-text">
            {(effectiveRealProb * 100).toFixed(1)}%
          </p>
        </div>
        <div>
          <span className="font-mono text-[10.5px] uppercase tracking-wider text-faint">Confidence</span>
          <p className="font-mono text-[15px] font-semibold text-signal">
            {(effectiveConfidence * 100).toFixed(1)}%
          </p>
        </div>
      </div>

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
