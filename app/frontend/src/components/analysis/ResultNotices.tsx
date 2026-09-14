import { ArrowUpRight, History, Users, Zap } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { BAND_SHORT } from '../../lib/presentation.ts'
import { timeAgo } from '../../lib/navigation.ts'
import type { AnalysisResponse } from '../../types/api.ts'

function Notice({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <li className="flex items-start gap-2.5 text-[13.5px] text-mute">
      <span className="mt-0.5 shrink-0 text-signal">{icon}</span>
      <span>{children}</span>
    </li>
  )
}

const linkClass = 'inline-flex items-center gap-0.5 font-medium text-signal hover:underline'

/** What happened to this result: saved? seen before? reused from cache? */
export function ResultNotices({ result, signedIn }: { result: AnalysisResponse; signedIn: boolean }) {
  const { scan, seen_before: seen, cached } = result
  const yours = seen?.yours

  return (
    <ul className="panel grid gap-2.5 px-4 py-3.5" aria-label="About this result">
      {scan ? (
        <Notice icon={<History className="size-4" aria-hidden />}>
          Saved to your history — {scan.image_saved ? 'result and image' : 'result only, image not kept'}.{' '}
          <Link to={`/history/${scan.id}`} className={linkClass}>
            Open <ArrowUpRight className="size-3.5" aria-hidden />
          </Link>
        </Notice>
      ) : (
        <Notice icon={<History className="size-4" aria-hidden />}>
          Not saved — guest scans leave no trace.{' '}
          {!signedIn && (
            <Link to="/signup" className={linkClass}>
              Create an account to keep a history
            </Link>
          )}
        </Notice>
      )}

      {yours && (
        <Notice icon={<History className="size-4" aria-hidden />}>
          You scanned {yours.exact ? 'this exact file' : 'a visually identical image'} {timeAgo(yours.scanned_at)} —{' '}
          {yours.band === result.verdict.band ? 'same verdict' : `verdict then: ${BAND_SHORT[yours.band]}`}.{' '}
          <Link to={`/history/${yours.scan_id}`} className={linkClass}>
            View <ArrowUpRight className="size-3.5" aria-hidden />
          </Link>
        </Notice>
      )}

      {seen?.others_count && (
        <Notice icon={<Users className="size-4" aria-hidden />}>
          Similar images were analysed by {seen.others_count} other people on SignalScope —{' '}
          {seen.consistent ? 'verdicts were consistent' : 'verdicts differed'}.
        </Notice>
      )}

      {cached && (
        <Notice icon={<Zap className="size-4" aria-hidden />}>
          Instant result — reused the analysis of an identical file under the same model.
        </Notice>
      )}
    </ul>
  )
}
