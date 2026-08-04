import { useRef, useState, useEffect, memo } from 'react'
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
      {/* Video element — ambient opacity, GPU accelerated */}
      {showVideo && (
        <video
          ref={videoRef}
          className="absolute inset-0 w-full h-full"
          style={{
            objectFit: 'cover',
            opacity: 0.22,
            willChange: 'transform',
            transform: 'translateZ(0)',
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

      {/* Layer 1: Heavy blur + dim filter over video */}
      <div
        className="absolute inset-0"
        style={{
          backdropFilter: 'blur(10px) brightness(18%) contrast(75%) saturate(70%)',
          WebkitBackdropFilter: 'blur(10px) brightness(18%) contrast(75%) saturate(70%)',
        }}
      />

      {/* Layer 2: Radial spotlight — bright center, dark edges */}
      <div
        className="absolute inset-0"
        style={{
          background: `
            radial-gradient(ellipse 55% 50% at 35% 45%, rgba(15, 20, 40, 0.2) 0%, transparent 70%),
            radial-gradient(ellipse 80% 70% at 50% 50%, rgba(8, 10, 24, 0.5) 0%, rgba(3, 0, 15, 0.92) 100%)
          `,
        }}
      />

      {/* Layer 3: Soft vignette — tight around viewport edges */}
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse 65% 50% at 50% 50%, transparent 0%, rgba(2, 0, 12, 0.7) 100%)',
        }}
      />

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
          background: 'linear-gradient(to top, rgba(2, 0, 12, 0.8) 0%, transparent 100%)',
        }}
      />

      {/* Top gradient for navbar readability */}
      <div
        className="absolute inset-x-0 top-0 h-[12%]"
        style={{
          background: 'linear-gradient(to bottom, rgba(2, 0, 12, 0.5) 0%, transparent 100%)',
        }}
      />
    </div>
  )
})
