import { Lock, TriangleAlert } from 'lucide-react'
import { useEffect, useId, useRef, useState, type DragEvent } from 'react'
import { ACCEPTED_TYPES, MAX_UPLOAD_MB, validateFile } from '../../lib/presentation.ts'
import { SignalWave } from '../brand/SignalWave.tsx'
import { Viewfinder } from '../ui/Viewfinder.tsx'

interface DropzoneProps {
  onFile: (file: File) => void
  error?: string | null
}

function Reticle() {
  return (
    <svg viewBox="0 0 64 64" fill="none" className="size-16" aria-hidden>
      <circle cx="32" cy="32" r="22" className="stroke-signal" strokeWidth="1.5" strokeDasharray="3 5" />
      <circle cx="32" cy="32" r="3" className="fill-signal" />
      <path d="M32 2v12M32 50v12M2 32h12M50 32h12" className="stroke-signal" strokeWidth="1.5" />
    </svg>
  )
}

export function Dropzone({ onFile, error }: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [hovering, setHovering] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const hintId = useId()
  const shownError = localError ?? error ?? null

  const accept = (file: File | undefined) => {
    if (!file) return
    const problem = validateFile(file)
    setLocalError(problem)
    if (!problem) onFile(file)
  }

  // Paste an image from the clipboard anywhere on the page.
  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => {
      const item = Array.from(event.clipboardData?.items ?? []).find((i) => i.kind === 'file')
      const file = item?.getAsFile()
      if (file) {
        event.preventDefault()
        accept(file)
      }
    }
    window.addEventListener('paste', onPaste)
    return () => window.removeEventListener('paste', onPaste)
  })

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragging(false)
    accept(event.dataTransfer.files[0])
  }

  return (
    <div onPointerEnter={() => setHovering(true)} onPointerLeave={() => setHovering(false)}>
      <Viewfinder labels={['Input · 01', `JPEG · PNG · WebP ≤ ${MAX_UPLOAD_MB} MB`]}>
        <div
          role="button"
          tabIndex={0}
          aria-describedby={hintId}
          aria-label="Choose an image to analyse"
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              inputRef.current?.click()
            }
          }}
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={`grid min-h-72 cursor-pointer place-items-center gap-3 rounded-sm border border-dashed px-5 py-8 text-center transition-colors ${
            dragging ? 'border-signal bg-signal-dim' : 'border-line-strong hover:border-signal'
          } bg-[radial-gradient(circle_at_50%_50%,var(--color-signal-dim),transparent_60%)]`}
        >
          <Reticle />
          <p className="text-[22px] font-semibold tracking-tight">
            {dragging ? 'Release to scan' : 'Drop an image to scan'}
          </p>
          <p id={hintId} className="text-sm text-mute">
            or <span className="text-signal underline underline-offset-4">browse your files</span> · paste with{' '}
            <kbd className="rounded-sm border border-line-strong px-1.5 font-mono text-[11px]">Ctrl</kbd>{' '}
            <kbd className="rounded-sm border border-line-strong px-1.5 font-mono text-[11px]">V</kbd>
          </p>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_TYPES.join(',')}
            className="sr-only"
            tabIndex={-1}
            aria-label="Choose an image to analyse"
            onChange={(e) => {
              accept(e.target.files?.[0])
              e.target.value = '' // allow re-selecting the same file
            }}
          />
        </div>

        {shownError ? (
          <p role="alert" className="mt-4 flex items-center gap-2 text-sm text-ai">
            <TriangleAlert className="size-4 shrink-0" aria-hidden />
            {shownError}
          </p>
        ) : (
          <p className="mt-4 flex items-center gap-2 text-[12.5px] text-faint">
            <Lock className="size-3.5" aria-hidden />
            Analysed in memory. Guests' images are never stored.
          </p>
        )}
      </Viewfinder>
      <SignalWave excited={hovering || dragging} className="mt-2 h-20 w-full" />
    </div>
  )
}
