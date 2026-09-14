import { useState } from 'react'
import { CUE_STYLES } from '../../lib/presentation.ts'
import type { Cue } from '../../types/api.ts'
import { Switch } from '../ui/Switch.tsx'
import { Viewfinder } from '../ui/Viewfinder.tsx'

interface ImageViewerProps {
  /** Image to display; null when only the result was kept (a blank specimen is drawn instead). */
  src: string | null
  alt: string
  width: number
  height: number
  heatmap: string | null
  cues: Cue[]
  tags: string[]
  activeCue: number | null
  onActiveCueChange: (index: number | null) => void
}

const coord = (value: number) => value.toFixed(2).replace(/^0/, '')

export function ImageViewer({ src, alt, width, height, heatmap, cues, tags, activeCue, onActiveCueChange }: ImageViewerProps) {
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [showRegions, setShowRegions] = useState(true)
  const [opacity, setOpacity] = useState(0.75)
  const regionCues = cues.map((cue, index) => ({ cue, index })).filter(({ cue }) => cue.region)

  return (
    <Viewfinder
      labels={[src ? 'Specimen · heat-map overlay' : 'Specimen · image not kept', `Regions · ${regionCues.length}`]}
      className="h-full"
    >
      <div className="flex justify-center rounded-sm bg-black">
        {/* Wrapper matches the rendered image box so overlays line up exactly. */}
        <div
          className="relative inline-block"
          style={src ? undefined : { aspectRatio: `${width} / ${height}`, width: `min(100%, calc(34rem * ${width} / ${height}))` }}
        >
          {src ? (
            <img src={src} alt={alt} className="block max-h-[34rem] w-auto max-w-full" />
          ) : (
            <div className="scope-grid absolute inset-0 grid place-items-center p-4 text-center">
              <span className="label leading-relaxed">
                Result only — the image wasn't kept
                <br />
                {width} × {height}
              </span>
            </div>
          )}

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
            <Switch on={showHeatmap} onChange={setShowHeatmap}>
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
          <Switch on={showRegions} onChange={setShowRegions}>
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
