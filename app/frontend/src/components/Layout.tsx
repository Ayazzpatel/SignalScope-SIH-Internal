import { NavLink, Outlet } from 'react-router'
import { HealthBadge } from './HealthBadge.tsx'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
    isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:text-slate-900'
  }`

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <img src="/favicon.svg" alt="" className="size-7" />
            SignalScope
          </NavLink>
          <nav className="flex items-center gap-1" aria-label="Main">
            <NavLink to="/" end className={navClass}>
              Analyze
            </NavLink>
          </nav>
          <HealthBadge />
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <p className="mx-auto max-w-6xl px-4 py-4 text-xs text-slate-500">
          SignalScope gives a <strong>likelihood assessment</strong>, not a definitive judgement. Results can be
          wrong — especially for heavily edited or compressed images. Never use them as the sole basis for an
          accusation.
        </p>
      </footer>
    </div>
  )
}
