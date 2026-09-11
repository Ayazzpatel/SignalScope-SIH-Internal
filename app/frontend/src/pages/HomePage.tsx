import { AnalyzingState } from '../components/analysis/AnalyzingState.tsx'
import { Dropzone } from '../components/analysis/Dropzone.tsx'
import { ResultView } from '../components/analysis/ResultView.tsx'
import { useAnalysis } from '../hooks/useAnalysis.ts'

const CHECKS = [
  {
    label: 'Visual',
    title: 'Artefacts the eye misses',
    body: 'Warped geometry, lighting that disagrees with itself, textures too smooth to have been photographed.',
  },
  {
    label: 'Spectral',
    title: "The generator's fingerprint",
    body: 'Upsampling layers leave periodic patterns in the frequency spectrum — often surviving compression.',
  },
  {
    label: 'Provenance',
    title: 'What the file declares',
    body: 'Content Credentials, IPTC source type and EXIF — shown beside the verdict, never instead of it.',
  },
]

export function HomePage() {
  const { state, analyze, reset } = useAnalysis()

  if (state.kind === 'done') {
    return (
      <ResultView
        result={state.result}
        previewUrl={state.previewUrl}
        fileName={state.file.name || 'Pasted image'}
        onReset={() => reset()}
      />
    )
  }

  if (state.kind === 'analyzing') {
    return (
      <AnalyzingState
        previewUrl={state.previewUrl}
        fileName={state.file.name || 'Pasted image'}
        fileSize={state.file.size}
        onCancel={() => reset()}
      />
    )
  }

  return (
    <div>
      <section className="relative grid items-center gap-12 pt-4 pb-10 lg:grid-cols-[1.05fr_1fr] lg:gap-14 lg:pt-10">
        <div
          className="graticule pointer-events-none absolute -inset-x-5 inset-y-0 -z-10 [mask-image:radial-gradient(ellipse_70%_80%_at_30%_40%,#000_30%,transparent_75%)]"
          aria-hidden
        />
        <div className="animate-rise">
          <div className="mb-7 flex items-center gap-3.5">
            <span className="h-px w-9 bg-signal" aria-hidden />
            <span className="label">Image authenticity · likelihood assessment</span>
          </div>
          <h1 className="text-[clamp(56px,9.2vw,124px)] leading-[0.92] font-semibold tracking-[-0.045em]">
            Is it <em className="display-em">real</em>?
          </h1>
          <p className="mt-7 max-w-[30rem] text-[17px] leading-relaxed text-mute">
            Drop in any image. SignalScope reads its visual artefacts and provenance metadata, tells you how likely it
            is to be AI-generated — and shows you exactly where it looked.
          </p>
          <dl className="mt-9 flex flex-wrap gap-7">
            {[
              ['Output', 'Calibrated likelihood'],
              ['Explains', 'Heat-map + cues'],
              ['Checks', 'C2PA · EXIF · IPTC'],
            ].map(([term, value]) => (
              <div key={term} className="grid gap-2">
                <dt className="label">{term}</dt>
                <dd className="text-sm font-medium">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="animate-rise [animation-delay:120ms]">
          <Dropzone onFile={analyze} error={state.error} />
        </div>
      </section>

      <section
        aria-label="What SignalScope checks"
        className="grid animate-rise border-t border-line [animation-delay:180ms] md:grid-cols-3"
      >
        {CHECKS.map((check, index) => (
          <div
            key={check.label}
            className={`grid content-start gap-2.5 py-7 md:pr-7 ${index > 0 ? 'border-t border-line md:border-t-0 md:border-l md:pl-7' : ''}`}
          >
            <span className="label">{check.label}</span>
            <h2 className="text-lg font-semibold tracking-tight">{check.title}</h2>
            <p className="max-w-[34ch] text-[14.5px] text-mute">{check.body}</p>
          </div>
        ))}
      </section>

      <section className="mt-2 flex animate-rise flex-wrap items-end justify-between gap-6 border-t border-line pt-8 [animation-delay:240ms]">
        <p className="max-w-[18ch] font-serif text-[clamp(32px,4.6vw,56px)] leading-[1.02]">
          A <em className="text-signal">likelihood,</em> never an accusation.
        </p>
        <p className="max-w-[38ch] text-[14.5px] text-mute">
          Every verdict comes with a calibrated probability, an honest “uncertain” band, and the regions that drove it —
          so people can judge for themselves.
        </p>
      </section>
    </div>
  )
}
