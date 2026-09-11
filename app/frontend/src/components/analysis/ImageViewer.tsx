import { useState } from 'react'
import { CUE_STYLES } from '../../lib/presentation.ts'
import type { Cue } from '../../types/api.ts'
import { Viewfinder } from '../ui/Viewfinder.tsx'

interface ImageViewerProps {
  src: string
  alt: string
  heatmap: string | null
  cues: Cue[]
  tags: string[]
  activeCue: number | null
  onActiveCueChange: (index: number | null) => void
}

function Switch({ on, onClick, children }: { on: boolean; onClick: () => void; children: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={on}
      className={`inline-flex items-center gap-2 text-[13px] transition-colors ${on ? 'text-text' : 'text-mute hover:text-text'}`}
    >
      <span
        className={`relative h-3.5 w-6.5 rounded-full border transition-colors ${on ? 'border-signal bg-signal-dim' : 'border-line-strong'}`}
        aria-hidden
      >
        <span
          className={`absolute top-0.5 left-0.5 size-2 rounded-full transition-transform ${on ? 'translate-x-3 bg-signal' : 'bg-mute'}`}
        />
      </span>
      {children}
    </button>
  )
}

const coord = (value: number) => value.toFixed(2).replace(/^0/, '')

export function ImageViewer({ src, alt, heatmap, cues, tags, activeCue, onActiveCueChange }: ImageViewerProps) {
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [showRegions, setShowRegions] = useState(true)
  const [opacity, setOpacity] = useState(0.75)
  const regionCues = cues.map((cue, index) => ({ cue, index })).filter(({ cue }) => cue.region)

  return (
    <Viewfinder labels={['Specimen · heat-map overlay', `Regions · ${regionCues.length}`]} className="h-full">
      <div className="flex justify-center rounded-sm bg-black">
        {/* Wrapper shrinks to the rendered image so overlays line up exactly. */}
        <div className="relative inline-block">
          <img src={src} alt={alt} className="block max-h-[34rem] w-auto max-w-full" />

          {heatmap && showHeatmap && (
            <img
              src={heatmap}
              alt=""
              aria-hidden
              className="pointer-events-none absolute inset-0 size-full transition-opacity"
              style={{ opacity }}
            />
          )}

          {showRegions &&
            regionCues.map(({ cue, index }) => {
              const [x, y, w, h] = cue.region!
              const active = activeCue === index
              return (
                <button
                  key={index}
                  type="button"
                  aria-label={`${tags[index]}: ${CUE_STYLES[cue.type].label}`}
                  onMouseEnter={() => onActiveCueChange(index)}
                  onMouseLeave={() => onActiveCueChange(null)}
                  onFocus={() => onActiveCueChange(index)}
                  onBlur={() => onActiveCueChange(null)}
                  className={`absolute rounded-sm border-[1.5px] transition-colors focus:outline-none ${
                    active ? 'border-solid border-signal bg-signal/10' : 'border-dashed border-white/85'
                  }`}
                  style={{ left: `${x * 100}%`, top: `${y * 100}%`, width: `${w * 100}%`, height: `${h * 100}%` }}
                >
                  <span className="absolute -top-5.5 -left-px rounded-[2px] bg-signal px-1.5 py-1 font-mono text-[10.5px] leading-none font-semibold tracking-wide whitespace-nowrap text-ink">
                    {tags[index]} · x{coord(x)} y{coord(y)}
                  </span>
                </button>
              )
            })}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-3">
        {heatmap && (
          <>
            <Switch on={showHeatmap} onClick={() => setShowHeatmap((v) => !v)}>
              Heat-map
            </Switch>
            <label className="flex items-center gap-2">
              <span className="label">Opacity</span>
              <input
                type="range"
                min={0.2}
                max={1}
                step={0.05}
                value={opacity}
                disabled={!showHeatmap}
                onChange={(e) => setOpacity(Number(e.target.value))}
                className="w-24 accent-signal"
              />
            </label>
          </>
        )}
        {regionCues.length > 0 && (
          <Switch on={showRegions} onClick={() => setShowRegions((v) => !v)}>
            Regions
          </Switch>
        )}
        {heatmap && (
          <span className="label flex items-center gap-2 sm:ml-auto">
            Low
            <span className="h-1.5 w-16 rounded-full bg-gradient-to-r from-[#fde047] via-[#f97316] to-[#dc2626]" />
            High influence
          </span>
        )}
      </div>
    </Viewfinder>
  )
}
