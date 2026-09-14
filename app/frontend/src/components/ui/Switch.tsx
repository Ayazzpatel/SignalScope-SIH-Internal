import type { ReactNode } from 'react'

interface SwitchProps {
  on: boolean
  onChange: (next: boolean) => void
  children: ReactNode
  disabled?: boolean
}

/** Instrument-style toggle. Renders as a pressed/unpressed button for assistive tech. */
export function Switch({ on, onChange, children, disabled = false }: SwitchProps) {
  return (
    <button
      type="button"
      onClick={() => onChange(!on)}
      aria-pressed={on}
      disabled={disabled}
      className={`inline-flex items-center gap-2.5 text-[13px] transition-colors disabled:opacity-50 ${
        on ? 'text-text' : 'text-mute hover:text-text'
      }`}
    >
      <span
        className={`relative h-3.5 w-6.5 shrink-0 rounded-full border transition-colors ${
          on ? 'border-signal bg-signal-dim' : 'border-line-strong'
        }`}
        aria-hidden
      >
        <span
          className={`absolute top-0.5 left-0.5 size-2 rounded-full transition-transform ${
            on ? 'translate-x-3 bg-signal' : 'bg-mute'
          }`}
        />
      </span>
      {children}
    </button>
  )
}
