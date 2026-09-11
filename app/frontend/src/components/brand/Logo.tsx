export function LogoMark({ className = 'size-8' }: { className?: string }) {
  return (
    <svg viewBox="0 0 34 34" fill="none" className={className} aria-hidden>
      <rect x=".5" y=".5" width="33" height="33" rx="6" className="fill-panel stroke-line-strong" />
      <path
        d="M5 19 L10 19 L12.5 11 L15.5 25 L18.5 8 L21 21 L23 16 L29 16"
        className="stroke-signal"
        strokeWidth="1.8"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}
