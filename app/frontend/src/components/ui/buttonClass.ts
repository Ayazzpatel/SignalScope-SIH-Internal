export type ButtonVariant = 'signal' | 'ghost' | 'danger' | 'quiet'

const VARIANTS: Record<ButtonVariant, string> = {
  signal: 'bg-signal text-ink hover:bg-signal-hover',
  ghost: 'border border-line-strong text-text hover:border-mute',
  danger: 'border border-ai/50 text-ai hover:bg-ai/10',
  quiet: 'text-mute hover:bg-raise hover:text-text',
}

/** Button styling, also used for links that should look like buttons. */
export const buttonClass = (variant: ButtonVariant = 'signal', extra = '') =>
  `inline-flex items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${extra}`
