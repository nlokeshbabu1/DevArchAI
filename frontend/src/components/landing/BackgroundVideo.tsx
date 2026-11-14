import { useReducedMotion } from 'framer-motion'
import { useRef, useState, useEffect, memo, type CSSProperties } from 'react'

import bgVideo from '@/assets/videos/Background_SaaS.mp4'

const POSTER_GRADIENT =
  'radial-gradient(ellipse 70% 60% at 50% 40%, rgba(18, 24, 48, 0.9) 0%, rgba(5, 7, 18, 1) 100%)'

function useCoarsePointerOrMobile() {
  const [reduceMotionMedia, setReduceMotionMedia] = useState(false)
  const [narrowViewport, setNarrowViewport] = useState(false)

  useEffect(() => {
    const motionMq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const narrowMq = window.matchMedia('(max-width: 768px)')
    const update = () => {
      setReduceMotionMedia(motionMq.matches)
      setNarrowViewport(narrowMq.matches)
    }
    update()
    motionMq.addEventListener('change', update)
    narrowMq.addEventListener('change', update)
    return () => {
      motionMq.removeEventListener('change', update)
      narrowMq.removeEventListener('change', update)
    }
  }, [])

  return reduceMotionMedia || narrowViewport
}

export const BackgroundVideo = memo(function BackgroundVideo() {
  const containerRef = useRef<HTMLDivElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const prefersReducedMotion = useReducedMotion()
  const skipVideo = useCoarsePointerOrMobile()
  const [isVisible, setIsVisible] = useState(true)
  const [videoReady, setVideoReady] = useState(false)

  useEffect(() => {
    if (import.meta.env.MODE === 'test') {
      setIsVisible(true)
      return
    }
    const node = containerRef.current
    if (!node) {return}
    const observer = new IntersectionObserver(
      ([entry]) => setIsVisible(entry.isIntersecting),
      { root: null, threshold: 0.05 }
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const vid = videoRef.current
    if (!vid || skipVideo || prefersReducedMotion) {return}

    if (isVisible) {
      if (vid.preload === 'none') {
        vid.preload = 'auto'
        vid.load()
      }
      void vid.play().catch(() => {
        /* autoplay blocked — poster gradient remains */
      })
    } else {
      vid.pause()
    }
  }, [isVisible, skipVideo, prefersReducedMotion])

  const showVideo = !skipVideo && !prefersReducedMotion

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 w-full h-full overflow-hidden pointer-events-none"
      style={{ zIndex: 0 }}
      aria-hidden="true"
    >
      <div
        className="absolute inset-0"
        style={{ background: POSTER_GRADIENT }}
        aria-hidden
      />

      {showVideo && (
        <video
          ref={videoRef}
          className="absolute inset-0 w-full h-full transition-opacity duration-700"
          style={{
            objectFit: 'cover',
            objectPosition: 'center center',
            opacity: videoReady ? 0.45 : 0,
            transform: 'translateZ(0)',
          }}
          muted
          loop
          playsInline
          preload="none"
          disablePictureInPicture
          disableRemotePlayback
          poster=""
          onCanPlay={() => setVideoReady(true)}
        >
          <source src={bgVideo} type="video/mp4" />
        </video>
      )}

      {/* Lighter overlay on mobile — avoids full-viewport backdrop-filter cost */}
      <div
        className="absolute inset-0 md:hidden"
        style={{
          background: `
            linear-gradient(to bottom, rgba(2, 0, 12, 0.55) 0%, rgba(5, 7, 18, 0.85) 100%)
          `,
        }}
      />
      <div
        className="absolute inset-0 hidden md:block"
        style={{
          background: `
            radial-gradient(ellipse 55% 50% at 50% 45%, rgba(18, 24, 48, 0.22) 0%, transparent 70%),
            radial-gradient(ellipse 80% 70% at 50% 50%, rgba(6, 8, 20, 0.45) 0%, rgba(5, 7, 18, 0.6) 100%)
          `,
        }}
      />

      <div
        className="absolute inset-0 hidden md:block"
        style={{
          background: 'radial-gradient(ellipse 65% 50% at 50% 50%, transparent 0%, rgba(2, 0, 12, 0.45) 100%)',
        }}
      />

      {!prefersReducedMotion && (
        <div
          className={`absolute inset-0 overflow-hidden hidden lg:block ${isVisible ? '' : '[&_.aurora-blob]:![animation-play-state:paused]'}`}
          style={{
            maskImage: 'radial-gradient(ellipse 90% 70% at 50% 45%, black 30%, transparent 100%)',
            WebkitMaskImage: 'radial-gradient(ellipse 90% 70% at 50% 45%, black 30%, transparent 100%)',
          }}
        >
          <div
            className="aurora-blob animate-aurora-a"
            style={{
              width: '55vw',
              height: '55vw',
              left: '-8%',
              top: '-12%',
              background: 'radial-gradient(circle at 35% 35%, rgba(124, 92, 255, 0.28), transparent 70%)',
            }}
          />
          <div
            className="aurora-blob animate-aurora-b"
            style={{
              width: '48vw',
              height: '48vw',
              right: '-10%',
              top: '22%',
              background: 'radial-gradient(circle at 60% 40%, rgba(79, 141, 255, 0.22), transparent 70%)',
            }}
          />
          <div
            className="aurora-blob animate-aurora-c"
            style={{
              width: '40vw',
              height: '40vw',
              left: '18%',
              bottom: '-18%',
              background: 'radial-gradient(circle at 50% 50%, rgba(0, 229, 255, 0.14), transparent 70%)',
            }}
          />
        </div>
      )}

      {!prefersReducedMotion && isVisible && (
        <div className="absolute inset-0 overflow-hidden pointer-events-none hidden lg:block">
          {[
            { left: '8%', size: 3, dur: 16, delay: 0, drift: 14, glow: 6 },
            { left: '49%', size: 3, dur: 17, delay: 7, drift: 10, glow: 6 },
            { left: '84%', size: 3, dur: 20, delay: 4.4, drift: 16, glow: 6 },
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

      <div
        className="absolute inset-x-0 bottom-0 h-[20%] pointer-events-none"
        style={{
          background: 'linear-gradient(to top, rgba(2, 0, 12, 0.35) 0%, transparent 100%)',
        }}
      />
      <div
        className="absolute inset-x-0 top-0 h-[12%] pointer-events-none"
        style={{
          background: 'linear-gradient(to bottom, rgba(2, 0, 12, 0.45) 0%, transparent 100%)',
        }}
      />
    </div>
  )
})
