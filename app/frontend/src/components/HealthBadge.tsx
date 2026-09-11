import { useHealth } from '../hooks/useHealth.ts'

export function HealthBadge() {
  const health = useHealth()

  const { dot, label } =
    health.kind === 'loading'
      ? { dot: 'bg-slate-300', label: 'Connecting…' }
      : health.kind === 'offline'
        ? { dot: 'bg-red-500', label: 'API offline' }
        : health.data.status === 'ok'
          ? {
              dot: health.data.detector === 'mock' ? 'bg-amber-400' : 'bg-emerald-500',
              label: health.data.detector === 'mock' ? 'Demo model' : `Model ${health.data.model_version}`,
            }
          : { dot: 'bg-amber-500', label: 'Model loading' }

  return (
    <span
      className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600"
      role="status"
      title={health.kind === 'online' ? `API v${health.data.version} · ${health.data.model_version}` : undefined}
    >
      <span className={`size-2 rounded-full ${dot}`} aria-hidden />
      {label}
    </span>
  )
}
