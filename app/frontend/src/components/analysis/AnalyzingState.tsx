import { formatBytes } from '../../lib/presentation.ts'
import { Button } from '../ui/Button.tsx'
import { Viewfinder } from '../ui/Viewfinder.tsx'

interface AnalyzingStateProps {
  previewUrl: string
  fileName: string
  fileSize: number
  onCancel: () => void
}

// The checks the server runs for every upload (see backend services/analysis.py).
const STEPS = [
  'decode & normalise image',
  'read content credentials (C2PA)',
  'read EXIF / IPTC metadata',
  'run visual artefact model',
  'locate influential regions',
  'calibrate verdict',
]

export function AnalyzingState({ previewUrl, fileName, fileSize, onCancel }: AnalyzingStateProps) {
  return (
    <section className="animate-rise">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <h1 className="min-w-0 text-[clamp(28px,3.6vw,44px)] leading-none font-semibold tracking-[-0.035em]">
          Scanning <em className="display-em break-all">{fileName}</em>
        </h1>
        <span className="label">{formatBytes(fileSize)}</span>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.25fr_1fr]">
        <Viewfinder>
          <div className="relative overflow-hidden rounded-sm bg-black">
            <img src={previewUrl} alt="" className="mx-auto block max-h-[34rem] w-auto max-w-full opacity-80" />
            <div className="scope-grid pointer-events-none absolute inset-0" aria-hidden />
            <div
              className="absolute inset-x-0 top-0 h-0.5 animate-sweep bg-signal shadow-[0_0_18px_4px_rgb(212_255_58/0.55),0_-60px_80px_rgb(212_255_58/0.12)]"
              aria-hidden
            />
          </div>
        </Viewfinder>

        <div className="panel grid content-start gap-1 p-5 font-mono text-[13px] leading-8 text-mute" role="status" aria-live="polite">
          <span className="label mb-2">Lab log · running</span>
          {STEPS.map((step, index) => (
            <div key={step} className="flex items-center gap-2">
              <span className="text-faint">›</span>
              <span>{step}</span>
              {index === STEPS.length - 1 && <span className="inline-block h-4 w-2 animate-blink bg-signal" aria-hidden />}
            </div>
          ))}
          <p className="mt-4 border-t border-line pt-4 font-sans text-xs leading-relaxed text-faint">
            These checks run together in one request, so there's no progress percentage to show — you'll see the
            result the moment it's ready.
          </p>
          <div className="mt-3">
            <Button variant="quiet" onClick={onCancel} className="px-0 hover:bg-transparent">
              Cancel scan
            </Button>
          </div>
        </div>
      </div>
    </section>
  )
}
