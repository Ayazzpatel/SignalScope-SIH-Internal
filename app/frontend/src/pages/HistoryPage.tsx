import { Search, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'
import { ScanCard } from '../components/history/ScanCard.tsx'
import { StatsStrip } from '../components/history/StatsStrip.tsx'
import { Alert } from '../components/ui/Alert.tsx'
import { Button } from '../components/ui/Button.tsx'
import { buttonClass } from '../components/ui/buttonClass.ts'
import { api } from '../lib/api.ts'
import { toFormErrors } from '../lib/forms.ts'
import { BAND_SHORT } from '../lib/presentation.ts'
import type { ScanStats, ScanSummary, VerdictBand } from '../types/api.ts'

const PAGE_SIZE = 24
const BANDS: (VerdictBand | undefined)[] = [undefined, 'likely_ai', 'uncertain', 'likely_real']

export function HistoryPage() {
  const [stats, setStats] = useState<ScanStats | null>(null)
  const [items, setItems] = useState<ScanSummary[] | null>(null)
  const [cursor, setCursor] = useState<string | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [band, setBand] = useState<VerdictBand | undefined>()
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<'newest' | 'oldest'>('newest')

  const [selecting, setSelecting] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [confirming, setConfirming] = useState(false)
  const [deleting, setDeleting] = useState(false)

  // Debounce the search box so typing doesn't fire a request per keystroke.
  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(search.trim()), 300)
    return () => window.clearTimeout(timer)
  }, [search])

  const loadStats = useCallback(async () => {
    try {
      setStats(await api.scans.stats())
    } catch {
      /* stats are decorative; the list shows the error */
    }
  }, [])

  const loadFirstPage = useCallback(async () => {
    try {
      const page = await api.scans.list({ band, q: query, sort, limit: PAGE_SIZE })
      setItems(page.items)
      setCursor(page.next_cursor)
      setError(null)
    } catch (err) {
      setError(toFormErrors(err, []).form)
    }
  }, [band, query, sort])

  useEffect(() => {
    // State is set only after the async fetches resolve, not synchronously in the effect.
    // oxlint-disable-next-line react/set-state-in-effect
    void loadFirstPage()
  }, [loadFirstPage])

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    void loadStats()
  }, [loadStats])

  const loadMore = async () => {
    if (!cursor) return
    setLoadingMore(true)
    try {
      const page = await api.scans.list({ band, q: query, sort, cursor, limit: PAGE_SIZE })
      setItems((prev) => [...(prev ?? []), ...page.items])
      setCursor(page.next_cursor)
    } catch (err) {
      setError(toFormErrors(err, []).form)
    } finally {
      setLoadingMore(false)
    }
  }

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const exitSelect = () => {
    setSelecting(false)
    setSelected(new Set())
    setConfirming(false)
  }

  const deleteSelected = async () => {
    setDeleting(true)
    try {
      await api.scans.removeMany([...selected])
      exitSelect()
      await Promise.all([loadFirstPage(), loadStats()])
    } catch (err) {
      setError(toFormErrors(err, []).form)
    } finally {
      setDeleting(false)
    }
  }

  const filtered = Boolean(band || query)

  return (
    <div className="grid animate-rise gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <span className="label">Archive · your scans</span>
          <h1 className="mt-3 text-[clamp(36px,5vw,56px)] leading-none font-semibold tracking-[-0.04em]">
            Scan <em className="display-em">history</em>
          </h1>
          <p className="mt-3 text-mute">
            Private to you. Results expire according to your{' '}
            <Link to="/account#privacy" className="text-text underline underline-offset-4">
              retention setting
            </Link>
            .
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {items && items.length > 0 && (
            <Button variant="ghost" onClick={() => (selecting ? exitSelect() : setSelecting(true))}>
              {selecting ? 'Done' : 'Select'}
            </Button>
          )}
          <Link to="/" className={buttonClass('signal')}>
            New scan
          </Link>
        </div>
      </header>

      {stats && stats.total > 0 && <StatsStrip stats={stats} />}

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter by verdict">
          {BANDS.map((value) => (
            <button
              key={value ?? 'all'}
              type="button"
              aria-pressed={band === value}
              onClick={() => setBand(value)}
              className={`rounded-full border px-3 py-1.5 font-mono text-[11px] tracking-[0.06em] uppercase transition-colors ${
                band === value ? 'border-signal bg-signal-dim text-signal' : 'border-line-strong text-mute hover:text-text'
              }`}
            >
              {value ? BAND_SHORT[value] : 'All'}
            </button>
          ))}
        </div>
        <label className="relative ml-auto min-w-0 flex-1 sm:max-w-64">
          <span className="sr-only">Search by filename</span>
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-faint" aria-hidden />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search filenames"
            className="w-full rounded-md border border-line-strong bg-ink py-2 pr-3 pl-9 text-sm placeholder:text-faint focus:border-signal focus:outline-none"
          />
        </label>
        <label className="flex items-center gap-2">
          <span className="label">Sort</span>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as 'newest' | 'oldest')}
            className="rounded-md border border-line-strong bg-ink px-2.5 py-2 text-sm focus:border-signal focus:outline-none"
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </label>
      </div>

      {selecting && (
        <div className="panel sticky top-18 z-20 flex flex-wrap items-center justify-between gap-3 px-4 py-3">
          <span className="font-mono text-xs tracking-wide text-mute uppercase">{selected.size} selected</span>
          <div className="flex flex-wrap items-center gap-2">
            {confirming ? (
              <>
                <span className="text-sm text-mute">
                  Delete {selected.size} scan{selected.size === 1 ? '' : 's'} and their files?
                </span>
                <Button variant="quiet" onClick={() => setConfirming(false)} disabled={deleting}>
                  Cancel
                </Button>
                <Button variant="danger" loading={deleting} onClick={() => void deleteSelected()}>
                  Yes, delete
                </Button>
              </>
            ) : (
              <Button variant="danger" disabled={selected.size === 0} onClick={() => setConfirming(true)}>
                <Trash2 className="size-4" aria-hidden />
                Delete selected
              </Button>
            )}
          </div>
        </div>
      )}

      {error && <Alert tone="error">{error}</Alert>}
      {items === null && !error && <p className="label py-10 text-center">Loading history…</p>}

      {items && items.length === 0 && (
        <div className="panel grid place-items-center gap-3 px-6 py-16 text-center">
          <span className="label">{filtered ? 'No matches' : 'Empty archive'}</span>
          <p className="max-w-sm text-mute">
            {filtered
              ? 'No scans match these filters.'
              : 'Scans you run while signed in appear here — with the verdict, heat-map and provenance.'}
          </p>
          {!filtered && (
            <Link to="/" className={buttonClass('signal', 'mt-2')}>
              Scan your first image
            </Link>
          )}
        </div>
      )}

      {items && items.length > 0 && (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {items.map((scan) => (
            <li key={scan.id}>
              <ScanCard scan={scan} selecting={selecting} selected={selected.has(scan.id)} onToggle={toggle} />
            </li>
          ))}
        </ul>
      )}

      {cursor && (
        <div className="flex justify-center">
          <Button variant="ghost" loading={loadingMore} onClick={() => void loadMore()}>
            Load more
          </Button>
        </div>
      )}
    </div>
  )
}
