import { LoaderCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import { Navigate, useLocation, useSearchParams } from 'react-router'
import { useAuth } from '../../hooks/useAuth.ts'
import { safeNext } from '../../lib/navigation.ts'

function FullPageSpinner() {
  return (
    <div className="flex justify-center py-24" role="status">
      <LoaderCircle className="size-6 animate-spin text-signal" aria-hidden />
      <span className="sr-only">Loading…</span>
    </div>
  )
}

/** Signed-in users only; guests are sent to /login and brought back afterwards. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <FullPageSpinner />
  if (status === 'guest') {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  return children
}

/** Login / signup pages: already signed-in users skip straight to where they were going. */
export function GuestOnly({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const [params] = useSearchParams()

  if (status === 'loading') return <FullPageSpinner />
  if (status === 'authenticated') return <Navigate to={safeNext(params.get('next'))} replace />
  return children
}
