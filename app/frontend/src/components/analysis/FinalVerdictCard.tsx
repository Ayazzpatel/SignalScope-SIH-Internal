import type { Ref } from 'react'
import { BAND_STYLES } from '../../lib/presentation.ts'
import type { ModelScore, Verdict } from '../../types/api.ts'

interface FinalVerdictCardProps {
  verdict: Verdict
  models: ModelScore[]
  headingRef?: Ref<HTMLHeadingElement>
}

/** The one combined call across every detector — deliberately no per-model breakdown or score. */
export function FinalVerdictCard({ verdict, models, headingRef }: FinalVerdictCardProps) {
  const style = BAND_STYLES[verdict.band]
  const Icon = style.icon
  const used = models.filter((m) => m.error === null).length
  const total = models.length
  const noun = `detection model${total === 1 ? '' : 's'}`

  return (
    <section className="panel p-5 sm:p-6" aria-labelledby="verdict-heading">
      <span className="label">Result</span>
      <h2
        id="verdict-heading"
        ref={headingRef}
        tabIndex={-1}
        className={`mt-4 flex items-center gap-3 text-[clamp(28px,3vw,36px)] leading-tight font-semibold tracking-[-0.03em] focus:outline-none ${style.text}`}
      >
        <Icon className="size-8 shrink-0" aria-hidden />
        {verdict.headline}
      </h2>
      <p className="mt-3 max-w-[42ch] text-[14.5px] text-mute">{verdict.summary}</p>
      <p className="mt-5 border-t border-line pt-4 font-mono text-[11.5px] tracking-[0.04em] text-faint">
        {used === total ? `Checked by ${total} ${noun}` : `Checked by ${used} of ${total} ${noun}`}
      </p>
    </section>
  )
}
