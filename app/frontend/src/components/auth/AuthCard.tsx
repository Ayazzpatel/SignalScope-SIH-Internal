import type { ReactNode } from 'react'
import { SignalWave } from '../brand/SignalWave.tsx'
import { Viewfinder } from '../ui/Viewfinder.tsx'

interface AuthCardProps {
  eyebrow: string
  title: ReactNode
  subtitle?: ReactNode
  children: ReactNode
  footer?: ReactNode
}

/** Split layout: brand statement + live trace on the left, the form in a viewfinder on the right. */
export function AuthCard({ eyebrow, title, subtitle, children, footer }: AuthCardProps) {
  return (
    <section className="grid items-center gap-10 lg:grid-cols-[1fr_minmax(0,440px)] lg:gap-16">
      <div className="hidden animate-rise lg:block">
        <span className="label">SignalScope · account</span>
        <p className="mt-6 max-w-[14ch] font-serif text-[clamp(40px,4.8vw,64px)] leading-[1.02]">
          Keep a private record of <em className="text-signal">what you checked.</em>
        </p>
        <ul className="mt-8 grid max-w-sm gap-3 text-[14.5px] text-mute">
          <li className="flex gap-3">
            <span className="label pt-1.5 text-signal">01</span>Scan history you can search, reopen and delete.
          </li>
          <li className="flex gap-3">
            <span className="label pt-1.5 text-signal">02</span>You choose whether images are kept — results only by
            default.
          </li>
          <li className="flex gap-3">
            <span className="label pt-1.5 text-signal">03</span>See and sign out every device, any time.
          </li>
        </ul>
        <SignalWave className="mt-10 h-24 w-full max-w-md" />
      </div>

      <div className="mx-auto w-full max-w-[440px] animate-rise [animation-delay:80ms]">
        <Viewfinder className="p-6 sm:p-8">
          <span className="label">{eyebrow}</span>
          <h1 className="mt-3 text-[32px] leading-tight font-semibold tracking-[-0.03em]">{title}</h1>
          {subtitle && <p className="mt-2 text-sm text-mute">{subtitle}</p>}
          <div className="mt-7">{children}</div>
        </Viewfinder>
        {footer && <div className="mt-5 text-center text-sm text-mute">{footer}</div>}
      </div>
    </section>
  )
}
