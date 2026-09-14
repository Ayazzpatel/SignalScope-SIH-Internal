import { CheckCircle, Clock, Loader, TriangleAlert, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { BatchItem } from '../../hooks/useBatchAnalysis.ts'
import { cueTags, formatBytes } from '../../lib/presentation.ts'
import { Button } from '../ui/Button.tsx'
import { CueList } from './CueList.tsx'
import { DemoBanner } from './DemoBanner.tsx'
import { EvidencePanel } from './EvidencePanel.tsx'
import { ImageViewer } from './ImageViewer.tsx'
import { LimitsPanel } from './LimitsPanel.tsx'
import { ProvenancePanel } from './ProvenancePanel.tsx'
import { VerdictCard } from './VerdictCard.tsx'

interface BatchResultViewProps {
  items: BatchItem[]
  activeId: string
  onSetActive: (id: string) => void
  onReset: () => void
  onAddMore: () => void
}

function StatusIcon({ status }: { status: BatchItem['status'] }) {
  if (status === 'done') return <CheckCircle className="size-3.5 text-real shrink-0" />
  if (status === 'error') return <TriangleAlert className="size-3.5 text-ai shrink-0" />
  if (status === 'analyzing') return <Loader className="size-3.5 text-signal shrink-0 animate-spin" />
  return <Clock className="size-3.5 text-faint shrink-0" />
}

function LabelChip({ item }: { item: BatchItem }) {
  if (item.status === 'done' && item.result) {
    const isAI = item.result.e1.ai_probability >= 0.5
    return (
      <span
        className={`ml-auto shrink-0 rounded-sm px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wide ${
          isAI ? 'bg-ai/15 text-ai border border-ai/30' : 'bg-real/15 text-real border border-real/30'
        }`}
      >
        {isAI ? 'AI' : 'Real'}
      </span>
    )
  }
  if (item.status === 'error') {
    return (
      <span className="ml-auto shrink-0 rounded-sm px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wide bg-ai/15 text-ai border border-ai/30">
        Err
      </span>
    )
  }
  return null
}

export function BatchResultView({ items, activeId, onSetActive, onReset, onAddMore }: BatchResultViewProps) {
  const active = items.find((i) => i.id === activeId) ?? items[0]
  const [activeCue, setActiveCue] = useState<number | null>(null)
  const headingRef = useRef<HTMLHeadingElement>(null)

  const tags = useMemo(
    () => cueTags(active?.result?.e1.explanation.cues ?? []),
    [active?.result?.e1.explanation.cues],
  )

  useEffect(() => {
    setActiveCue(null)
    headingRef.current?.focus()
  }, [activeId])

  const doneCount = items.filter((i) => i.status === 'done').length
  const totalCount = items.length
  const aiCount = items.filter((i) => i.result && i.result.e1.ai_probability >= 0.5).length
  const realCount = items.filter((i) => i.result && i.result.e1.ai_probability < 0.5).length

  return (
    <section className="grid gap-4">
      {/* Header row */}
      <div className="mb-2 flex animate-rise flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4 min-w-0">
          <div>
            <span className="label">Batch scan</span>
            <p className="mt-1 text-[15px] font-semibold tracking-tight">
              {doneCount}/{totalCount} complete
              {doneCount > 0 && (
                <span className="ml-3 font-mono text-[12px] font-normal text-mute">
                  <span className="text-ai">{aiCount} AI</span>
                  {' · '}
                  <span className="text-real">{realCount} Real</span>
                </span>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" onClick={onAddMore} id="add-more-images-btn">
            + Add more images
          </Button>
          <Button variant="ghost" onClick={onReset} id="new-batch-btn">
            <X className="size-4 mr-1" />
            Clear all
          </Button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
        {/* Sidebar — image queue */}
        <div className="animate-rise [animation-delay:60ms]">
          <div className="panel overflow-hidden">
            <div className="border-b border-line px-3 py-2.5">
              <span className="label text-[10px]">Queue · {totalCount} image{totalCount !== 1 ? 's' : ''}</span>
            </div>
            <ul className="max-h-[calc(100vh-220px)] overflow-y-auto divide-y divide-line">
              {items.map((item) => (
                <li key={item.id}>
                  <button
                    onClick={() => onSetActive(item.id)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2.5 text-left transition-colors hover:bg-signal-dim ${
                      item.id === activeId ? 'bg-signal-dim border-l-2 border-signal' : ''
                    }`}
                    aria-current={item.id === activeId ? 'true' : undefined}
                  >
                    {/* Thumbnail */}
                    <img
                      src={item.previewUrl}
                      alt=""
                      className="size-9 rounded-sm object-cover shrink-0 bg-surface"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[12px] font-medium leading-tight" title={item.file.name}>
                        {item.file.name}
                      </p>
                      <p className="text-[10.5px] text-faint mt-0.5">{formatBytes(item.file.size)}</p>
                    </div>
                    <div className="flex flex-col items-end gap-1 shrink-0">
                      <StatusIcon status={item.status} />
                      <LabelChip item={item} />
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Main result area */}
        <div className="min-w-0">
          {!active ? null : active.status === 'queued' ? (
            <div className="animate-rise panel flex min-h-64 items-center justify-center p-8 text-center">
              <div>
                <Clock className="size-8 mx-auto mb-3 text-faint" />
                <p className="text-[15px] font-semibold">Queued</p>
                <p className="mt-1 text-sm text-mute max-w-[24ch]">
                  {active.file.name} is waiting to be scanned.
                </p>
              </div>
            </div>
          ) : active.status === 'analyzing' ? (
            <div className="animate-rise panel flex min-h-64 items-center justify-center p-8 text-center">
              <div>
                <div className="relative mx-auto mb-4 size-12">
                  <img src={active.previewUrl} alt="" className="size-12 rounded-sm object-cover opacity-40" />
                  <div className="absolute inset-x-0 top-0 h-0.5 animate-sweep bg-signal shadow-[0_0_12px_3px_rgb(212_255_58/0.6)]" />
                </div>
                <Loader className="size-5 mx-auto mb-2 text-signal animate-spin" />
                <p className="text-[15px] font-semibold">Scanning…</p>
                <p className="mt-1 text-sm text-mute">{active.file.name}</p>
              </div>
            </div>
          ) : active.status === 'error' ? (
            <div className="animate-rise panel flex min-h-64 items-center justify-center p-8 text-center">
              <div>
                <TriangleAlert className="size-8 mx-auto mb-3 text-ai" />
                <p className="text-[15px] font-semibold">Scan failed</p>
                <p className="mt-1 text-sm text-mute max-w-[30ch]">{active.error}</p>
              </div>
            </div>
          ) : active.result ? (
            <div className="grid gap-4">
              {active.result.e1.detector === 'mock' && <DemoBanner />}
              <div className="grid gap-4 lg:grid-cols-12">
                <div className="animate-rise [animation-delay:60ms] lg:col-span-7 lg:row-span-2">
                  <ImageViewer
                    src={active.previewUrl}
                    alt={`Uploaded image: ${active.file.name}`}
                    heatmap={active.result.e1.explanation.heatmap_png}
                    cues={active.result.e1.explanation.cues}
                    tags={tags}
                    activeCue={activeCue}
                    onActiveCueChange={setActiveCue}
                  />
                </div>
                <div className="animate-rise [animation-delay:120ms] lg:col-span-5 flex flex-col gap-4" aria-live="polite">
                  <VerdictCard
                    title={`E1 Model · ${active.result.e1.model_version}`}
                    verdict={active.result.e1.verdict}
                    attribution={active.result.e1.attribution}
                    headingRef={headingRef}
                    label={active.result.e1.label}
                    aiProbability={active.result.e1.ai_probability}
                    realProbability={active.result.e1.real_probability}
                    confidence={active.result.e1.confidence}
                  />
                  {active.result.standalone.error ? (
                    <div className="panel p-5 sm:p-6 flex flex-col items-center justify-center text-center text-ai border-ai/20 bg-ai/5">
                       <TriangleAlert className="size-6 mb-2" />
                       <p className="text-sm font-medium">Standalone-M failed</p>
                       <p className="text-xs mt-1 text-mute/80">{active.result.standalone.error}</p>
                    </div>
                  ) : (
                    <VerdictCard
                      title={`Standalone-M · ${active.result.standalone.model_version}`}
                      verdict={active.result.standalone.verdict}
                      attribution={null}
                      label={active.result.standalone.label}
                      aiProbability={active.result.standalone.ai_probability}
                      realProbability={active.result.standalone.real_probability}
                      confidence={active.result.standalone.confidence}
                    />
                  )}
                </div>
                <div className="animate-rise [animation-delay:180ms] lg:col-span-5">
                  <CueList
                    cues={active.result.e1.explanation.cues}
                    tags={tags}
                    band={active.result.e1.verdict.band}
                    activeCue={activeCue}
                    onActiveCueChange={setActiveCue}
                  />
                </div>
                {active.result.e1.evidence && (
                  <div className="animate-rise [animation-delay:180ms] lg:col-span-7">
                    <EvidencePanel evidence={active.result.e1.evidence} />
                  </div>
                )}
                <div className="animate-rise [animation-delay:210ms] lg:col-span-7">
                  <ProvenancePanel provenance={active.result.e1.provenance} />
                </div>
                <div className="animate-rise [animation-delay:240ms] lg:col-span-5">
                  <LimitsPanel verdict={active.result.e1.verdict} disclaimer={active.result.e1.disclaimer} />
                </div>
              </div>
              <p className="flex flex-wrap gap-x-5 gap-y-2 font-mono text-[11.5px] tracking-[0.04em] text-faint">
                <span title={active.result.e1.image.sha256}>
                  SHA-256 <b className="font-medium text-mute">{active.result.e1.image.sha256.slice(0, 12)}…</b>
                </span>
                <span>
                  {active.result.e1.image.width}×{active.result.e1.image.height}{' '}
                  <b className="font-medium text-mute">{active.result.e1.image.format}</b>
                </span>
                <span>Size <b className="font-medium text-mute">{formatBytes(active.result.e1.image.size_bytes)}</b></span>
                <span>E1 <b className="font-medium text-mute">{Math.round(active.result.e1.timings.total_ms)} ms</b></span>
                <span>M <b className="font-medium text-mute">{Math.round(active.result.standalone.inference_ms)} ms</b></span>
              </p>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}
