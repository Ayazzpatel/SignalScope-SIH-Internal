import { Link } from 'react-router'
import { SignalWave } from '../components/brand/SignalWave.tsx'
import { buttonClass } from '../components/ui/buttonClass.ts'

export function NotFoundPage() {
  return (
    <section className="mx-auto max-w-xl animate-rise py-10 text-center">
      <span className="label">Error · 404 · no signal</span>
      <h1 className="mt-4 text-[clamp(44px,7vw,80px)] leading-none font-semibold tracking-[-0.04em]">
        Nothing <em className="display-em">here</em>.
      </h1>
      <p className="mt-4 text-mute">The page you're looking for doesn't exist or has moved.</p>
      <SignalWave className="mx-auto mt-8 h-16 w-full max-w-sm opacity-60" />
      <Link to="/" className={buttonClass('signal', 'mt-8')}>
        Back to Analyze
      </Link>
    </section>
  )
}
