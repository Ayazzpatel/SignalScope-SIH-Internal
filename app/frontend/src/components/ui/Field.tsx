import { Eye, EyeOff } from 'lucide-react'
import { useId, useState, type InputHTMLAttributes, type ReactNode } from 'react'

interface FieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id'> {
  label: string
  error?: string | null
  hint?: ReactNode
}

const inputClass = (error?: string | null) =>
  `block w-full rounded-md border bg-ink px-3 py-2.5 text-sm text-text placeholder:text-faint transition-colors focus:outline-none disabled:text-mute ${
    error ? 'border-ai/70 focus:border-ai' : 'border-line-strong hover:border-mute/60 focus:border-signal'
  }`

export function TextField({ label, error, hint, className = '', ...input }: FieldProps) {
  const id = useId()
  return (
    <div className={className}>
      <label htmlFor={id} className="label mb-2 block">
        {label}
      </label>
      <input
        id={id}
        {...input}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        className={inputClass(error)}
      />
      <FieldMessage id={id} error={error} hint={hint} />
    </div>
  )
}

export function PasswordField({ label, error, hint, className = '', ...input }: FieldProps) {
  const id = useId()
  const [visible, setVisible] = useState(false)
  return (
    <div className={className}>
      <label htmlFor={id} className="label mb-2 block">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          {...input}
          type={visible ? 'text' : 'password'}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
          className={`pr-10 ${inputClass(error)}`}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? 'Hide password' : 'Show password'}
          aria-pressed={visible}
          className="absolute inset-y-0 right-0 flex items-center px-3 text-faint hover:text-text"
        >
          {visible ? <EyeOff className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
        </button>
      </div>
      <FieldMessage id={id} error={error} hint={hint} />
    </div>
  )
}

function FieldMessage({ id, error, hint }: { id: string; error?: string | null; hint?: ReactNode }) {
  if (error) {
    return (
      <p id={`${id}-error`} className="mt-2 text-sm text-ai">
        {error}
      </p>
    )
  }
  if (hint) {
    return (
      <div id={`${id}-hint`} className="mt-2 text-xs text-mute">
        {hint}
      </div>
    )
  }
  return null
}
