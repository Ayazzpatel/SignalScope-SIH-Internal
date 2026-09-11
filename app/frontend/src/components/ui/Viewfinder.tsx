import type { HTMLAttributes, ReactNode } from 'react'

const CORNERS = [
  '-top-px -left-px border-t-2 border-l-2',
  '-top-px -right-px border-t-2 border-r-2',
  '-bottom-px -left-px border-b-2 border-l-2',
  '-right-px -bottom-px border-r-2 border-b-2',
]

interface ViewfinderProps extends HTMLAttributes<HTMLDivElement> {
  /** Left / right instrument labels above the content. */
  labels?: [ReactNode, ReactNode?]
}

/** Camera-viewfinder frame: hairline panel with signal-coloured corner marks. */
export function Viewfinder({ labels, className = '', children, ...rest }: ViewfinderProps) {
  return (
    <div {...rest} className={`panel relative p-4 sm:p-5 ${className}`}>
      {CORNERS.map((position) => (
        <span key={position} className={`pointer-events-none absolute size-4.5 border-signal ${position}`} aria-hidden />
      ))}
      {labels && (
        <div className="mb-4 flex flex-wrap justify-between gap-3">
          <span className="label">{labels[0]}</span>
          {labels[1] && <span className="label">{labels[1]}</span>}
        </div>
      )}
      {children}
    </div>
  )
}
