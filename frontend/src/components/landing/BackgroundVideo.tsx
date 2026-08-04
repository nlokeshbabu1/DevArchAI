import { useRef, useState, useEffect, memo, type CSSProperties } from 'react'
import { useReducedMotion } from 'framer-motion'
import bgVideo from '@/assets/videos/Background_SaaS.mp4'

function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${breakpoint}px)`)
    setIsMobile(mq.matches)
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [breakpoint])
  return isMobile
}

export const BackgroundVideo = memo(function BackgroundVideo() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const prefersReducedMotion = useReducedMotion()
  const isMobile = useIsMobile()
  const [canAutoplay, setCanAutoplay] = useState(true)

  useEffect(() => {
    const vid = videoRef.current
    if (!vid || prefersReducedMotion) return

    const tryPlay = async () => {
      try {
        await vid.play()
      } catch {
        setCanAutoplay(false)
      }
    }
    tryPlay()
  }, [prefersReducedMotion])

  const showVideo = !prefersReducedMotion && canAutoplay

  return (
    <div
      className="fixed inset-0 w-full h-full overflow-hidden"
      style={{ zIndex: 0 }}
      aria-hidden="true"
    >
      {/* Video element — ambient opacity, GPU accelerated, focal point centered */}
      {showVideo && (
        <video
          ref={videoRef}
          className="absolute inset-0 w-full h-full"
          style={{
            objectFit: 'cover',
            opacity: 0.48,
            willChange: 'transform',
            transform: 'translateZ(0) translateX(-5%) scale(1.1)',
          }}
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
          disablePictureInPicture
          disableRemotePlayback
        >
          <source src={bgVideo} type="video/mp4" />
        </video>
      )}

      {/* Layer 1: Soft blur + gentle dim filter over video */}
      <div
        className="absolute inset-0"
        style={{
          backdropFilter: 'blur(8px) brightness(32%) contrast(82%) saturate(92%)',
          WebkitBackdropFilter: 'blur(8px) brightness(32%) contrast(82%) saturate(92%)',
        }}
      />

      {/* Layer 2: Radial spotlight — soft center light, gentle dark edges */}
      <div
        className="absolute inset-0"
        style={{
          background: `
            radial-gradient(ellipse 55% 50% at 50% 45%, rgba(18, 24, 48, 0.22) 0%, transparent 70%),
            radial-gradient(ellipse 80% 70% at 50% 50%, rgba(6, 8, 20, 0.45) 0%, rgba(5, 7, 18, 0.6) 100%)
          `,
        }}
      />

      {/* Layer 3: Soft vignette — subtle, tight around viewport edges */}
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse 65% 50% at 50% 50%, transparent 0%, rgba(2, 0, 12, 0.45) 100%)',
        }}
      />

      {/* Layer 3.5: Aurora blobs — screen-blended ambient light */}
      <div
        className="absolute inset-0 overflow-hidden"
        style={{ maskImage: 'radial-gradient(ellipse 90% 70% at 50% 45%, black 30%, transparent 100%)', WebkitMaskImage: 'radial-gradient(ellipse 90% 70% at 50% 45%, black 30%, transparent 100%)' }}
      >
        <div
          className="aurora-blob animate-aurora-a"
          style={{
            width: '55vw',
            height: '55vw',
            left: '-8%',
            top: '-12%',
            background: 'radial-gradient(circle at 35% 35%, rgba(124, 92, 255, 0.32), transparent 70%)',
          }}
        />
        <div
          className="aurora-blob animate-aurora-b"
          style={{
            width: '48vw',
            height: '48vw',
            right: '-10%',
            top: '22%',
            background: 'radial-gradient(circle at 60% 40%, rgba(79, 141, 255, 0.28), transparent 70%)',
          }}
        />
        <div
          className="aurora-blob animate-aurora-c"
          style={{
            width: '40vw',
            height: '40vw',
            left: '18%',
            bottom: '-18%',
            background: 'radial-gradient(circle at 50% 50%, rgba(0, 229, 255, 0.18), transparent 70%)',
          }}
        />
      </div>

      {/* Layer 3.6: Floating particles — neural-network ambience */}
      {!prefersReducedMotion && (
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          {[
            { left: '8%', size: 3, dur: 16, delay: 0, drift: 14, glow: 6 },
            { left: '16%', size: 2, dur: 21, delay: 2.5, drift: -10, glow: 5 },
            { left: '27%', size: 4, dur: 19, delay: 5, drift: 18, glow: 8 },
            { left: '38%', size: 2, dur: 24, delay: 1.2, drift: -14, glow: 5 },
            { left: '49%', size: 3, dur: 17, delay: 7, drift: 10, glow: 6 },
            { left: '58%', size: 2, dur: 22, delay: 3.8, drift: -8, glow: 4 },
            { left: '67%', size: 3, dur: 18, delay: 0.6, drift: 12, glow: 7 },
            { left: '76%', size: 2, dur: 25, delay: 6.2, drift: -12, glow: 5 },
            { left: '84%', size: 3, dur: 20, delay: 4.4, drift: 16, glow: 6 },
            { left: '92%', size: 2, dur: 23, delay: 8.5, drift: -6, glow: 4 },
          ].map((p, i) => (
            <div
              key={i}
              className="particle-dot"
              style={{
                left: p.left,
                '--size': `${p.size}px`,
                '--dur': `${p.dur}s`,
                '--delay': `${p.delay}s`,
                '--drift-x': `${p.drift}px`,
                '--glow': `${p.glow}px`,
              } as CSSProperties}
            />
          ))}
        </div>
      )}

      {/* Layer 4: Very subtle animated noise texture */}
      <div
        className="absolute inset-0 opacity-[0.03] mix-blend-overlay pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
          backgroundRepeat: 'repeat',
          backgroundSize: '256px 256px',
          animation: 'noiseShift 8s steps(4) infinite',
        }}
      />

      {/* Bottom gradient for footer readability */}
      <div
        className="absolute inset-x-0 bottom-0 h-[35%]"
        style={{
          background: 'linear-gradient(to top, rgba(2, 0, 12, 0.6) 0%, transparent 100%)',
        }}
      />

      {/* Top gradient for navbar readability */}
      <div
        className="absolute inset-x-0 top-0 h-[12%]"
        style={{
          background: 'linear-gradient(to bottom, rgba(2, 0, 12, 0.45) 0%, transparent 100%)',
        }}
      />
    </div>
  )
})
