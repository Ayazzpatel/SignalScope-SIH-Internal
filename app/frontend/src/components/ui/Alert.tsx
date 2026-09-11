import { CircleCheck, Info, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'

type Tone = 'error' | 'success' | 'info'

const TONES: Record<Tone, { box: string; icon: typeof Info }> = {
  error: { box: 'border-ai/40 bg-ai/8 text-[#ffb3aa]', icon: TriangleAlert },
  success: { box: 'border-signal/40 bg-signal/8 text-signal', icon: CircleCheck },
  info: { box: 'border-line-strong bg-raise text-mute', icon: Info },
}

export function Alert({ tone = 'info', children }: { tone?: Tone; children: ReactNode }) {
  const { box, icon: Icon } = TONES[tone]
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={`flex items-start gap-2.5 rounded-md border px-3 py-2.5 text-sm ${box}`}>
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div>{children}</div>
    </div>
  )
}
