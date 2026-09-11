import { Link } from 'react-router'

export function NotFoundPage() {
  return (
    <section className="mx-auto max-w-md text-center">
      <h1 className="text-3xl font-bold">Page not found</h1>
      <p className="mt-3 text-slate-600">The page you are looking for does not exist.</p>
      <Link to="/" className="mt-6 inline-block font-medium text-brand-600 hover:text-brand-700">
        Back to Analyze
      </Link>
    </section>
  )
}
