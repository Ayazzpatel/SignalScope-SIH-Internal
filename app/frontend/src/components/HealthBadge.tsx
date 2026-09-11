import { useHealth } from '../hooks/useHealth.ts'

export function HealthBadge() {
  const health = useHealth()

  const { dot, label } =
    health.kind === 'loading'
      ? { dot: 'bg-faint', label: 'Connecting' }
      : health.kind === 'offline'
        ? { dot: 'bg-ai shadow-[0_0_10px_var(--color-ai)]', label: 'API offline' }
        : health.data.status === 'ok'
          ? { dot: 'bg-signal shadow-[0_0_10px_var(--color-signal)]', label: `Model ${health.data.model_version} · online` }
          : { dot: 'bg-unsure', label: 'Degraded' }

  return (
    <span
      role="status"
      className="inline-flex items-center gap-2 rounded-full border border-line px-3 py-1.5 font-mono text-[11px] tracking-[0.06em] text-mute uppercase"
      title={health.kind === 'online' ? `API v${health.data.version} · database ${health.data.database}` : undefined}
    >
      <span className={`size-1.5 rounded-full ${dot}`} aria-hidden />
      {label}
    </span>
  )
}
