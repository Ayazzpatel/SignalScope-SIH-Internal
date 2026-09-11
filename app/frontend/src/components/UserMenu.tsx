import { ChevronDown, LogOut, UserRound } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '../hooks/useAuth.ts'
import { initials } from '../lib/navigation.ts'
import type { User } from '../types/auth.ts'

export function UserMenu({ user }: { user: User }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const menuId = useId()

  useEffect(() => {
    if (!open) return
    const onPointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const signOut = async () => {
    setOpen(false)
    await logout()
    navigate('/', { replace: true })
  }

  const itemClass =
    'flex w-full items-center gap-2.5 rounded-sm px-3 py-2 text-left text-sm text-mute hover:bg-raise hover:text-text focus:bg-raise focus:text-text focus:outline-none'

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        className="flex items-center gap-2 rounded-full border border-line-strong py-1 pr-2.5 pl-1 text-sm text-text transition-colors hover:border-mute"
      >
        <span className="flex size-7 items-center justify-center rounded-full bg-signal font-mono text-[11px] font-semibold text-ink" aria-hidden>
          {initials(user.display_name)}
        </span>
        <span className="hidden max-w-32 truncate sm:inline">{user.display_name}</span>
        <ChevronDown className="size-4 text-faint" aria-hidden />
      </button>

      {open && (
        <div id={menuId} role="menu" className="panel absolute right-0 z-40 mt-2 w-64 p-1.5 shadow-2xl shadow-black/60">
          <div className="border-b border-line px-3 pt-2 pb-3">
            <p className="truncate font-semibold">{user.display_name}</p>
            <p className="truncate font-mono text-xs text-faint">{user.email}</p>
            {user.role !== 'user' && (
              <span className="mt-2 inline-block rounded-sm border border-signal/40 px-1.5 py-1 font-mono text-[10.5px] tracking-widest text-signal uppercase">
                {user.role}
              </span>
            )}
          </div>
          <div className="pt-1.5">
            <Link to="/account" role="menuitem" className={itemClass} onClick={() => setOpen(false)}>
              <UserRound className="size-4" aria-hidden />
              Account & security
            </Link>
            <button type="button" role="menuitem" className={itemClass} onClick={() => void signOut()}>
              <LogOut className="size-4" aria-hidden />
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
