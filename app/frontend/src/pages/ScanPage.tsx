import { ArrowLeft, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { ResultView } from '../components/analysis/ResultView.tsx'
import { Alert } from '../components/ui/Alert.tsx'
import { Button } from '../components/ui/Button.tsx'
import { buttonClass } from '../components/ui/buttonClass.ts'
import { ApiError, api } from '../lib/api.ts'
import { formatDate } from '../lib/navigation.ts'
import type { ScanDetail } from '../types/api.ts'

type LoadState = { kind: 'loading' } | { kind: 'ready'; scan: ScanDetail } | { kind: 'error'; message: string; missing: boolean }

export function ScanPage() {
  const { scanId = '' } = useParams()
  const navigate = useNavigate()
  const [state, setState] = useState<LoadState>({ kind: 'loading' })
  const [confirming, setConfirming] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api.scans
      .get(scanId)
      .then((scan) => !cancelled && setState({ kind: 'ready', scan }))
      .catch((err: unknown) => {
        if (cancelled) return
        const missing = err instanceof ApiError && (err.status === 404 || err.status === 422)
        setState({
          kind: 'error',
          missing,
          message: missing ? 'This scan does not exist or has been deleted.' : 'Could not load this scan.',
        })
      })
    return () => {
      cancelled = true
    }
  }, [scanId])

  const remove = async () => {
    setDeleting(true)
    try {
      await api.scans.remove(scanId)
      navigate('/history', { replace: true })
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : 'Could not delete this scan.')
      setDeleting(false)
    }
  }

  const back = (
    <Link to="/history" className={buttonClass('quiet', 'px-3')}>
      <ArrowLeft className="size-4" aria-hidden />
      History
    </Link>
  )

  if (state.kind === 'loading') return <p className="label py-16 text-center">Loading scan…</p>
  if (state.kind === 'error') {
    return (
      <div className="mx-auto grid max-w-md gap-4 py-10 text-center">
        <span className="label">{state.missing ? 'Error · 404' : 'Error'}</span>
        <p className="text-mute">{state.message}</p>
        <div className="flex justify-center">{back}</div>
      </div>
    )
  }

  const { scan } = state
  return (
    <div className="grid gap-4">
      {deleteError && <Alert tone="error">{deleteError}</Alert>}
      <ResultView
        result={scan}
        resultKey={scan.id}
        imageUrl={scan.image_url}
        fileName={scan.filename ?? 'Untitled image'}
        eyebrow={`Saved scan · ${formatDate(scan.created_at)}`}
        storedLabel={scan.image_url ? 'result + image' : 'result only'}
        actions={
          <>
            {back}
            {confirming ? (
              <>
                <Button variant="quiet" onClick={() => setConfirming(false)} disabled={deleting}>
                  Cancel
                </Button>
                <Button variant="danger" loading={deleting} onClick={() => void remove()}>
                  Yes, delete scan
                </Button>
              </>
            ) : (
              <Button variant="ghost" onClick={() => setConfirming(true)}>
                <Trash2 className="size-4" aria-hidden />
                Delete
              </Button>
            )}
          </>
        }
      />
    </div>
  )
}
