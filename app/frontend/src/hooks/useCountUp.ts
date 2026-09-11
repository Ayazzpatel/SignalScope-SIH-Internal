import { useEffect, useState } from 'react'

/** Animate from 0 to `target` (ease-out). Jumps straight to the value for reduced-motion users. */
export function useCountUp(target: number, durationMs = 1100): number {
  const [value, setValue] = useState(0)

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let frame = 0
    const start = performance.now()
    const tick = (now: number) => {
      const progress = reduced ? 1 : Math.min((now - start) / durationMs, 1)
      setValue(target * (1 - Math.pow(1 - progress, 3)))
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, durationMs])

  return value
}
