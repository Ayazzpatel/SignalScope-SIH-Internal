export interface Strength {
  score: 0 | 1 | 2 | 3 | 4
  label: string
}

const LABELS = ['Too weak', 'Weak', 'Fair', 'Good', 'Strong'] as const

/** A lightweight heuristic for live feedback. The server enforces the real policy. */
export function estimateStrength(password: string): Strength {
  if (password.length < 10) return { score: 0, label: LABELS[0] }
  let points = 1
  if (password.length >= 14) points++
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) points++
  if (/\d/.test(password)) points++
  if (/[^A-Za-z0-9]/.test(password)) points++
  if (new Set(password).size < 6) points = Math.min(points, 1)
  const score = Math.min(points, 4) as Strength['score']
  return { score, label: LABELS[score] }
}
