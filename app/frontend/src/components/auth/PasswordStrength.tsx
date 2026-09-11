import { Check, Circle } from 'lucide-react'
import { estimateStrength } from '../../lib/passwordStrength.ts'

const BAR_COLOURS = ['bg-ai', 'bg-ai', 'bg-unsure', 'bg-signal', 'bg-signal']

export function PasswordStrength({ password, email }: { password: string; email: string }) {
  const strength = estimateStrength(password)
  const localPart = email.split('@')[0]?.toLowerCase() ?? ''
  const rules = [
    { ok: password.length >= 10, text: 'At least 10 characters' },
    {
      ok: password.length > 0 && !(localPart.length >= 3 && password.toLowerCase().includes(localPart)),
      text: "Doesn't contain your email name",
    },
  ]

  return (
    <div className="grid gap-2">
      <div className="flex items-center gap-3">
        <div className="flex flex-1 gap-1" aria-hidden>
          {[1, 2, 3, 4].map((segment) => (
            <span
              key={segment}
              className={`h-1 flex-1 rounded-full ${
                password && strength.score >= segment ? BAR_COLOURS[strength.score] : 'bg-line-strong'
              }`}
            />
          ))}
        </div>
        <span className="w-16 text-right font-mono text-[11px] tracking-wide text-mute uppercase" aria-live="polite">
          {password ? strength.label : ''}
        </span>
      </div>
      <ul className="grid gap-0.5">
        {rules.map((rule) => (
          <li key={rule.text} className={`flex items-center gap-1.5 ${rule.ok ? 'text-signal' : 'text-faint'}`}>
            {rule.ok ? <Check className="size-3.5" aria-hidden /> : <Circle className="size-3" aria-hidden />}
            <span>
              {rule.text}
              <span className="sr-only">{rule.ok ? ' (met)' : ' (not met)'}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
