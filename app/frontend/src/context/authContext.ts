import { createContext } from 'react'
import type { User } from '../types/auth.ts'

export type AuthStatus = 'loading' | 'authenticated' | 'guest'

export interface AuthContextValue {
  status: AuthStatus
  user: User | null
  login: (email: string, password: string, remember: boolean) => Promise<User>
  signup: (displayName: string, email: string, password: string) => Promise<User>
  logout: () => Promise<void>
  logoutEverywhere: () => Promise<void>
  setUser: (user: User) => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
