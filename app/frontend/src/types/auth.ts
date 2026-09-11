// Mirrors backend schemas/auth.py

export type UserRole = 'user' | 'reviewer' | 'admin'

export interface User {
  id: string
  email: string
  display_name: string
  role: UserRole
  created_at: string
}

export interface AuthResponse {
  user: User
}

export interface SessionStateResponse {
  user: User | null
}

export interface SessionInfo {
  id: string
  device: string
  ip_address: string | null
  signed_in_at: string
  last_active_at: string
  expires_at: string
  remember: boolean
  current: boolean
}

export interface MessageResponse {
  message: string
}
