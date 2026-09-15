export function LimitsPanel({ disclaimer }: { disclaimer: string }) {
  return (
    <section className="panel p-5 sm:p-6" aria-labelledby="limits-heading">
      <h3 id="limits-heading" className="label">
        Read this before sharing
      </h3>
      <div className="mt-4 grid gap-3 text-[13.5px] text-mute">
        <p>
          <strong className="font-medium text-text">Our models must agree:</strong> the verdict needs at least two of
          our detection models to agree. Some real photos can still be flagged, and some AI images missed.
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
