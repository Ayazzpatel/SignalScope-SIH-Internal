import { FlaskConical } from 'lucide-react'

export function DemoBanner() {
  return (
    <div role="note" className="flex items-start gap-3 rounded-md border border-unsure/40 bg-unsure/[0.07] px-4 py-3 text-sm">
      <FlaskConical className="mt-0.5 size-4.5 shrink-0 text-unsure" aria-hidden />
      <p className="text-mute">
        <strong className="font-semibold text-unsure">Demo model — results are simulated.</strong> The real detector
        isn't connected yet, so the verdict, heat-map and cues are placeholders. Provenance metadata is real.
      </p>
    </div>
  )
}
