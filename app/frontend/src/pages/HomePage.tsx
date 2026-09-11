export function HomePage() {
  return (
    <section className="mx-auto max-w-3xl text-center">
      <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">Is this image real or AI-generated?</h1>
      <p className="mt-4 text-lg text-slate-600">
        Upload an image to get a calibrated likelihood, a heat-map of the regions behind the verdict, and any
        provenance metadata it carries.
      </p>

      {/* Upload flow is implemented in Phase 1. */}
      <div
        className="mt-10 rounded-2xl border-2 border-dashed border-slate-300 bg-white px-6 py-16 text-slate-500"
        aria-disabled
      >
        <p className="font-medium text-slate-700">Drag & drop an image here</p>
        <p className="mt-1 text-sm">JPEG, PNG or WebP · coming in the next build</p>
      </div>
    </section>
  )
}
