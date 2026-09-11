import { percent } from '../../lib/presentation.ts'
import type { Verdict } from '../../types/api.ts'

export function LimitsPanel({ verdict, disclaimer }: { verdict: Verdict; disclaimer: string }) {
  const pct = percent(verdict.prob_ai)
  const perHundred = Math.round(verdict.prob_ai * 100)

  return (
    <section className="panel p-5 sm:p-6" aria-labelledby="limits-heading">
      <h3 id="limits-heading" className="label">
        Read this before sharing
      </h3>
      <div className="mt-4 grid gap-3 text-[13.5px] text-mute">
        <p>
          <strong className="font-medium text-text">{pct} is calibrated:</strong> across many images scored like this,
          about {perHundred} in 100 turned out to be AI-generated. It is not certainty about this one.
        </p>
        <p>
          <strong className="font-medium text-text">“Uncertain” is an honest answer</strong> — the evidence is genuinely
          mixed, not a failure.
        </p>
        <p>
          <strong className="font-medium text-text">The heat-map shows where to look,</strong> not proof of manipulation.
        </p>
        <p>
          <strong className="font-medium text-text">Weak spots:</strong> heavy compression, screenshots, filters and very
          new generators reduce accuracy.
        </p>
        <p className="border-t border-line pt-3 text-xs text-faint">{disclaimer}</p>
      </div>
    </section>
  )
}
