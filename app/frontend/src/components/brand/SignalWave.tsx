import { useEffect, useRef } from 'react'

interface SignalWaveProps {
  /** Amplify the trace, e.g. while the user hovers the drop zone. */
  excited?: boolean
  className?: string
}

/** Ambient oscilloscope trace. Canvas-drawn; freezes to a still frame for reduced-motion users. */
export function SignalWave({ excited = false, className = 'h-20 w-full' }: SignalWaveProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const excitedRef = useRef(excited)

  useEffect(() => {
    excitedRef.current = excited
  }, [excited])

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    let energy = 0
    let frame = 0

    const resize = () => {
      canvas.width = canvas.clientWidth * dpr
      canvas.height = canvas.clientHeight * dpr
    }
    resize()
    const observer = new ResizeObserver(resize)
    observer.observe(canvas)

    const draw = (time: number) => {
      energy += ((excitedRef.current ? 1 : 0) - energy) * 0.06
      const { width: w, height: h } = canvas
      ctx.clearRect(0, 0, w, h)

      ctx.strokeStyle = 'rgb(214 240 222 / 0.08)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, h / 2)
      ctx.lineTo(w, h / 2)
      ctx.stroke()

      ctx.strokeStyle = '#d4ff3a'
      ctx.lineWidth = 1.5 * dpr
      ctx.shadowColor = 'rgb(212 255 58 / 0.6)'
      ctx.shadowBlur = 8 * dpr
      ctx.beginPath()
      for (let x = 0; x <= w; x += 2) {
        const p = x / w
        const envelope = Math.sin(p * Math.PI)
        const carrier = Math.sin(p * 18 + time / 420) * 0.7 + Math.sin(p * 47 - time / 260) * 0.3 * (1 + energy)
        const y = h / 2 + envelope * h * (0.16 + energy * 0.2) * carrier
        if (x === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.stroke()
      ctx.shadowBlur = 0

      if (!reduced) frame = requestAnimationFrame(draw)
    }
    draw(0)

    return () => {
      cancelAnimationFrame(frame)
      observer.disconnect()
    }
  }, [])

  return <canvas ref={canvasRef} className={`block ${className}`} aria-hidden />
}
