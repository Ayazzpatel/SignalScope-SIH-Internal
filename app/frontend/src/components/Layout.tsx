import { Link, NavLink, Outlet, useLocation } from 'react-router'
import { useAuth } from '../hooks/useAuth.ts'
import { LogoMark } from './brand/Logo.tsx'
import { buttonClass } from './ui/buttonClass.ts'
import { HealthBadge } from './HealthBadge.tsx'
import { UserMenu } from './UserMenu.tsx'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm transition-colors ${isActive ? 'bg-raise text-text' : 'text-mute hover:text-text'}`

function AuthControls() {
  const { status, user } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <span className="h-9 w-20" aria-hidden />
  if (status === 'authenticated' && user) return <UserMenu user={user} />

  const onAuthPage = location.pathname === '/login' || location.pathname === '/signup'
  const next = onAuthPage ? '' : `?next=${encodeURIComponent(location.pathname)}`
  return (
    <div className="flex items-center gap-2">
      <Link to={`/login${next}`} className={buttonClass('quiet', 'px-3 py-2')}>
        Sign in
      </Link>
      <Link to={`/signup${next}`} className={buttonClass('ghost', 'px-3 py-2')}>
        Create account
      </Link>
    </div>
  )
}

export function Layout() {
  const { status } = useAuth()
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 border-b border-line bg-ink">
        <div className="mx-auto flex max-w-[1180px] flex-wrap items-center justify-between gap-3 px-4 py-3.5 sm:px-5">
          <div className="flex items-center gap-8">
            <NavLink to="/" className="flex items-center gap-2.5 text-[17px] font-semibold tracking-tight">
              <LogoMark />
              SignalScope
            </NavLink>
            <nav className="hidden items-center gap-1 sm:flex" aria-label="Main">
              <NavLink to="/" end className={navClass}>
                Analyze
              </NavLink>
              {status === 'authenticated' && (
                <NavLink to="/history" className={navClass}>
                  History
                </NavLink>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden md:inline-flex">
              <HealthBadge />
            </span>
            <AuthControls />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1180px] flex-1 px-4 pt-10 pb-20 sm:px-5">
        <Outlet />
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-[1180px] flex-wrap items-center justify-between gap-3 px-4 py-5 sm:px-5">
          <p className="max-w-2xl text-xs text-faint">
            SignalScope gives a <span className="text-mute">likelihood assessment</span>, not a definitive judgement.
            Results can be wrong — especially for heavily edited or compressed images. Never use them as the sole basis
            for an accusation.
          </p>
          <span className="label">SIH 2026 · PS-2</span>
        </div>
      </footer>
    </div>
  )
}
