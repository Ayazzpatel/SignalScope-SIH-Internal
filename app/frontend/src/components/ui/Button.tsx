import { LoaderCircle } from 'lucide-react'
import type { ButtonHTMLAttributes } from 'react'
import { buttonClass, type ButtonVariant } from './buttonClass.ts'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  loading?: boolean
}

export function Button({ variant = 'signal', loading = false, disabled, className = '', children, ...rest }: ButtonProps) {
  return (
    <button {...rest} disabled={disabled || loading} aria-busy={loading || undefined} className={buttonClass(variant, className)}>
      {loading && <LoaderCircle className="size-4 animate-spin" aria-hidden />}
      {children}
    </button>
  )
}
