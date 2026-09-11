import { CUE_STYLES, strengthLabel } from '../../lib/presentation.ts'
import type { Cue, VerdictBand } from '../../types/api.ts'

interface CueListProps {
  cues: Cue[]
  tags: string[]
  band: VerdictBand
  activeCue: number | null
  onActiveCueChange: (index: number | null) => void
}

function StrengthBars({ value }: { value: number }) {
  const filled = value >= 0.7 ? 3 : value >= 0.4 ? 2 : 1
  return (
    <span className="inline-flex items-center gap-[3px]" role="img" aria-label={`${strengthLabel(value)} signal`}>
      {[1, 2, 3].map((bar) => (
        <span key={bar} className={`h-1 w-2.5 rounded-[1px] ${bar <= filled ? 'bg-ai' : 'bg-line-strong'}`} />
      ))}
    </span>
  )
}

export function CueList({ cues, tags, band, activeCue, onActiveCueChange }: CueListProps) {
  return (
    <section className="panel p-5 sm:p-6" aria-labelledby="cues-heading">
      <h3 id="cues-heading" className="label">
        What the model noticed
      </h3>

      {cues.length === 0 ? (
        <p className="mt-4 text-sm text-mute">
          {band === 'likely_real'
            ? 'No specific AI-generation cues stood out in this image.'
            : 'The model did not localise specific cues; its judgement rests on overall patterns.'}
        </p>
      ) : (
        <ul className="mt-4 grid gap-2.5">
          {cues.map((cue, index) => {
            const { label, icon: Icon } = CUE_STYLES[cue.type]
            const active = activeCue === index
            const local = Boolean(cue.region)
            return (
              <li
                key={index}
                onMouseEnter={() => local && onActiveCueChange(index)}
                onMouseLeave={() => local && onActiveCueChange(null)}
                className={`grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 rounded-sm border p-3 transition-colors ${
                  active ? 'border-signal bg-signal/[0.04]' : 'border-line'
                }`}
              >
                <span
                  className={`row-span-2 self-start rounded-[2px] px-1.5 py-1 font-mono text-[11px] leading-none font-semibold ${
                    local ? 'bg-signal text-ink' : 'border border-line-strong bg-raise text-mute'
                  }`}
                >
                  {tags[index]}
                </span>
                <div className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2 text-[14.5px] font-semibold">
                    <Icon className="size-4 text-faint" aria-hidden />
                    {label}
                  </span>
                  <StrengthBars value={cue.strength} />
                </div>
                <p className="text-[13.5px] text-mute">{cue.description}</p>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
