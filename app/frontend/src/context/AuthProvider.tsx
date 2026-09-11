import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { SESSION_EXPIRED_EVENT, api } from '../lib/api.ts'
import type { User } from '../types/auth.ts'
import { AuthContext, type AuthContextValue, type AuthStatus } from './authContext.ts'

// Keeps every open tab in sync when the user signs in or out in one of them.
const channel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('signalscope-auth') : null

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUserState] = useState<User | null>(null)

  const applyUser = useCallback((next: User | null) => {
    setUserState(next)
    setStatus(next ? 'authenticated' : 'guest')
  }, [])

  const reload = useCallback(async () => {
    try {
      applyUser((await api.auth.session()).user)
    } catch {
      applyUser(null)
    }
  }, [applyUser])

  useEffect(() => {
    // State is set only after the async fetch resolves, not synchronously in the effect.
    // oxlint-disable-next-line react/set-state-in-effect
    void reload()
    const onExpired = () => applyUser(null)
    const onMessage = () => void reload()
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    channel?.addEventListener('message', onMessage)
    return () => {
      window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
      channel?.removeEventListener('message', onMessage)
    }
  }, [reload, applyUser])

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      login: async (email, password, remember) => {
        const { user: signedIn } = await api.auth.login({ email, password, remember })
        applyUser(signedIn)
        channel?.postMessage('changed')
        return signedIn
      },
      signup: async (displayName, email, password) => {
        const { user: created } = await api.auth.signup({ display_name: displayName, email, password })
        applyUser(created)
        channel?.postMessage('changed')
        return created
      },
      logout: async () => {
        await api.auth.logout().catch(() => undefined) // signing out locally must always succeed
        applyUser(null)
        channel?.postMessage('changed')
      },
      logoutEverywhere: async () => {
        await api.auth.logoutAll()
        applyUser(null)
        channel?.postMessage('changed')
      },
      setUser: (next) => applyUser(next),
    }),
    [status, user, applyUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
