import { FileCode, Gauge, Radio, Sparkles } from 'lucide-react'
import type { EvidenceInfo } from '../../types/api.ts'

interface EvidencePanelProps {
  evidence?: EvidenceInfo
}

export function EvidencePanel({ evidence }: EvidencePanelProps) {
  if (!evidence) {
    return null
  }

  const items = [
    {
      label: 'Image Dimensions',
      value: evidence.image_size,
      subtext: 'Original pixel resolution',
      icon: FileCode,
    },
    {
      label: 'Laplacian Sharpness',
      value: evidence.sharpness_laplacian_var.toFixed(2),
      subtext: 'Edge focus & gradient variance',
      icon: Gauge,
    },
    {
      label: 'High-Freq Noise (Std)',
      value: evidence.high_frequency_noise_std.toFixed(2),
      subtext: 'Residual above 5x5 Gaussian blur',
      icon: Radio,
    },
    {
      label: 'EXIF Metadata',
      value: evidence.exif_present ? 'Present' : 'None detected',
      subtext: evidence.exif_present ? 'Hardware / capture tags found' : 'Stripped or absent header tags',
      icon: Sparkles,
      highlight: evidence.exif_present,
    },
  ]

  return (
    <section className="panel p-5 sm:p-6" aria-labelledby="evidence-heading">
      <div className="flex items-center justify-between">
        <h3 id="evidence-heading" className="label">
          Forensic Evidence · Measured Signals
        </h3>
        <span className="font-mono text-[11px] text-faint">Lightweight extraction</span>
      </div>

      <p className="mt-2 text-[13.5px] text-mute">
        Computed directly from image pixel gradients, frequency residuals, and header payloads.
      </p>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {items.map((item) => {
          const Icon = item.icon
          return (
            <div
              key={item.label}
              className="flex items-start gap-3 rounded-sm border border-line bg-panel-bright/30 p-3"
            >
              <div className="mt-0.5 rounded-sm bg-signal/10 p-2 text-signal">
                <Icon className="size-4" aria-hidden />
              </div>
              <div className="min-w-0 flex-1">
                <span className="font-mono text-[11px] uppercase tracking-wider text-faint">
                  {item.label}
                </span>
                <p className="font-mono text-[16px] font-semibold text-text truncate">
                  {item.value}
                </p>
                <p className="text-[12px] text-mute mt-0.5">{item.subtext}</p>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
