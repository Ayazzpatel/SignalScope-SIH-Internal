import { useEffect, useMemo, useRef, useState } from 'react'
import { cueTags, formatBytes } from '../../lib/presentation.ts'
import type { AnalysisResponse } from '../../types/api.ts'
import { Button } from '../ui/Button.tsx'
import { CueList } from './CueList.tsx'
import { DemoBanner } from './DemoBanner.tsx'
import { ImageViewer } from './ImageViewer.tsx'
import { LimitsPanel } from './LimitsPanel.tsx'
import { ProvenancePanel } from './ProvenancePanel.tsx'
import { VerdictCard } from './VerdictCard.tsx'

interface ResultViewProps {
  result: AnalysisResponse
  previewUrl: string
  fileName: string
  onReset: () => void
}

function splitName(name: string): [string, string] {
  const dot = name.lastIndexOf('.')
  return dot > 0 ? [name.slice(0, dot), name.slice(dot)] : [name, '']
}

export function ResultView({ result, previewUrl, fileName, onReset }: ResultViewProps) {
  const [activeCue, setActiveCue] = useState<number | null>(null)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const tags = useMemo(() => cueTags(result.explanation.cues), [result.explanation.cues])
  const [stem, ext] = splitName(fileName)

  // Move focus to the verdict so screen-reader and keyboard users land on the result.
  useEffect(() => {
    headingRef.current?.focus()
  }, [result.request_id])

  return (
    <section className="grid gap-4">
      <div className="mb-2 flex animate-rise flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <span className="label">Analysis result</span>
          <p className="mt-2.5 truncate text-[clamp(28px,3.6vw,44px)] leading-none font-semibold tracking-[-0.035em]" title={fileName}>
            {stem}
            <em className="display-em">{ext}</em>
          </p>
        </div>
        <Button variant="ghost" onClick={onReset}>
          Scan another image
        </Button>
      </div>

      {result.detector === 'mock' && <DemoBanner />}

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="animate-rise [animation-delay:60ms] lg:col-span-7 lg:row-span-2">
          <ImageViewer
            src={previewUrl}
            alt={`Uploaded image: ${fileName}`}
            heatmap={result.explanation.heatmap_png}
            cues={result.explanation.cues}
            tags={tags}
            activeCue={activeCue}
            onActiveCueChange={setActiveCue}
          />
        </div>
        <div className="animate-rise [animation-delay:120ms] lg:col-span-5" aria-live="polite">
          <VerdictCard verdict={result.verdict} attribution={result.attribution} headingRef={headingRef} />
        </div>
        <div className="animate-rise [animation-delay:180ms] lg:col-span-5">
          <CueList
            cues={result.explanation.cues}
            tags={tags}
            band={result.verdict.band}
            activeCue={activeCue}
            onActiveCueChange={setActiveCue}
          />
        </div>
        <div className="animate-rise [animation-delay:180ms] lg:col-span-7">
          <ProvenancePanel provenance={result.provenance} />
        </div>
        <div className="animate-rise [animation-delay:240ms] lg:col-span-5">
          <LimitsPanel verdict={result.verdict} disclaimer={result.disclaimer} />
        </div>
      </div>

      <p className="flex flex-wrap gap-x-5 gap-y-2 font-mono text-[11.5px] tracking-[0.04em] text-faint">
        <span title={result.image.sha256}>
          SHA-256 <b className="font-medium text-mute">{result.image.sha256.slice(0, 12)}…</b>
        </span>
        <span>
          {result.image.width}×{result.image.height} <b className="font-medium text-mute">{result.image.format}</b>
        </span>
        <span>
          Size <b className="font-medium text-mute">{formatBytes(result.image.size_bytes)}</b>
        </span>
        <span>
          Total <b className="font-medium text-mute">{Math.round(result.timings.total_ms)} ms</b>
        </span>
        <span>
          Model <b className="font-medium text-mute">{result.model_version}</b>
        </span>
      </p>
    </section>
  )
}
