import { motion, AnimatePresence } from 'framer-motion'
import { Smartphone, Brain, User, Sparkles } from 'lucide-react'
import { useState, useEffect, memo } from 'react'

const EASE = [0.16, 1, 0.3, 1] as const

interface DialogueLine {
  speaker: 'lokesh' | 'nova' | 'narrator'
  text?: string
  action?: string
  delay: number
  duration: number
}

const script: DialogueLine[] = [
  { speaker: 'narrator', action: 'A customer arrives holding a phone with a new app idea.', delay: 0, duration: 2400 },
  { speaker: 'narrator', action: 'Nova looks curious.', delay: 2400, duration: 1600 },
  { speaker: 'lokesh', text: '"We have a plan."', delay: 4000, duration: 2200 },
  { speaker: 'narrator', action: 'Pause.', delay: 6200, duration: 1000 },
  { speaker: 'lokesh', text: '"But how do we know exactly what the customer wants?"', delay: 7200, duration: 2800 },
  { speaker: 'narrator', action: 'Pause.', delay: 10000, duration: 1000 },
  { speaker: 'nova', text: '"We should ask them."', delay: 11000, duration: 2200 },
  { speaker: 'narrator', action: 'Lokesh smiles.', delay: 13200, duration: 1400 },
  { speaker: 'lokesh', text: '"Exactly."', delay: 14600, duration: 1600 },
  { speaker: 'narrator', action: 'Fade out.', delay: 16200, duration: 1400 },
  { speaker: 'narrator', action: 'No text.', delay: 17600, duration: 1200 },
]

function useCurrentLine(t: number) {
  for (let i = script.length - 1; i >= 0; i--) {
    if (t >= script[i].delay) {return script[i]}
  }
  return script[0]
}

const SpeakerAvatar = memo(function SpeakerAvatar({
  speaker,
  active,
}: {
  speaker: 'lokesh' | 'nova'
  active: boolean
}) {
  const isLokesh = speaker === 'lokesh'
  return (
    <motion.div
      className={`relative w-10 h-10 rounded-full flex items-center justify-center border transition-all duration-500 ${
        active
          ? isLokesh
            ? 'bg-primary/20 border-primary/40 shadow-[0_0_20px_rgba(99,102,241,0.2)]'
            : 'bg-cyan-500/20 border-cyan-500/40 shadow-[0_0_20px_rgba(6,182,212,0.2)]'
          : 'bg-white/[0.04] border-white/[0.08]'
      }`}
      animate={active ? { scale: [1, 1.05, 1] } : { scale: 1 }}
      transition={{ duration: 0.6, ease: EASE }}
    >
      {isLokesh ? (
        <User className={`h-4 w-4 transition-colors duration-500 ${active ? 'text-primary' : 'text-white/40'}`} />
      ) : (
        <Brain className={`h-4 w-4 transition-colors duration-500 ${active ? 'text-cyan-400' : 'text-white/40'}`} />
      )}
      {active && (
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            background: isLokesh
              ? 'radial-gradient(circle, rgba(99,102,241,0.15), transparent 70%)'
              : 'radial-gradient(circle, rgba(6,182,212,0.15), transparent 70%)',
          }}
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        />
      )}
    </motion.div>
  )
})

const PhoneMockup = memo(function PhoneMockup({ active }: { active: boolean }) {
  return (
    <motion.div
      className="relative w-14 h-24 rounded-xl border border-white/[0.1] bg-[#0a0f1e] overflow-hidden shadow-lg"
      animate={active ? { y: -4, boxShadow: '0 8px 30px rgba(99,102,241,0.15)' } : { y: 0 }}
      transition={{ duration: 0.5, ease: EASE }}
    >
      {/* Screen content */}
      <div className="absolute inset-0 p-1.5 flex flex-col gap-1">
        {/* Status bar */}
        <div className="h-1 w-full bg-white/[0.06] rounded-full" />
        {/* App mockup lines */}
        <div className="flex-1 flex flex-col justify-center gap-1 pt-2">
          <div className="h-1 w-3/4 bg-primary/20 rounded" />
          <div className="h-1 w-1/2 bg-white/[0.06] rounded" />
          <div className="h-1 w-2/3 bg-white/[0.04] rounded" />
          <div className="mt-1 h-3 w-full bg-primary/10 border border-primary/20 rounded" />
        </div>
      </div>
      {/* Glow when active */}
      {active && (
        <motion.div
          className="absolute inset-0 rounded-xl pointer-events-none"
          style={{ boxShadow: 'inset 0 0 15px rgba(99,102,241,0.1)' }}
          animate={{ opacity: [0.3, 0.7, 0.3] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}
    </motion.div>
  )
})

export const CustomerScene = memo(function CustomerScene() {
  const LOOP = 19200
  const [t, setT] = useState(0)
  const [playing, setPlaying] = useState(true)

  useEffect(() => {
    if (!playing) {return}
    let raf: number
    const start = performance.now()
    const tick = (now: number) => {
      const elapsed = now - start
      setT(elapsed % LOOP)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [playing])

  const line = useCurrentLine(t)
  const isNarator = line.speaker === 'narrator'
  const isLokesh = line.speaker === 'lokesh'
  const isNova = line.speaker === 'nova'
  const fadeOut = line.action === 'Fade out.' || line.action === 'No text.'

  return (
    <div
      className="w-full max-w-lg mx-auto"
      role="region"
      aria-label="Customer dialogue scene"
    >
      {/* Scene container */}
      <motion.div
        className="relative rounded-2xl border border-white/[0.06] bg-[#0a0f1e]/80 backdrop-blur-md overflow-hidden"
        animate={fadeOut ? { opacity: 0.3 } : { opacity: 1 }}
        transition={{ duration: 1, ease: EASE }}
      >
        {/* Top bar — scene header */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <Sparkles className="h-3 w-3 text-primary/60" />
            <span className="text-[10px] font-medium text-slate-400">DevArchAI — Customer Scene</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPlaying(!playing)}
              className="px-2 py-0.5 rounded text-[9px] font-medium text-slate-400 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] transition-all"
              aria-label={playing ? 'Pause scene' : 'Play scene'}
            >
              {playing ? 'Pause' : 'Play'}
            </button>
            <div className="w-1.5 h-1.5 rounded-full bg-green-400/70 animate-pulse" />
          </div>
        </div>

        {/* Scene area */}
        <div className="p-5 min-h-[220px] flex flex-col justify-between">
          {/* Characters row */}
          <div className="flex items-center justify-between mb-6">
            {/* Customer + Phone */}
            <div className="flex flex-col items-center gap-2">
              <PhoneMockup active={line.speaker === 'lokesh' && !isNarator} />
              <div className="flex items-center gap-1.5">
                <User className="h-3 w-3 text-slate-400/50" />
                <span className="text-[9px] text-slate-400/50 font-medium">Customer</span>
              </div>
            </div>

            {/* Lokesh */}
            <div className="flex flex-col items-center gap-2">
              <SpeakerAvatar speaker="lokesh" active={isLokesh} />
              <span className={`text-[9px] font-medium transition-colors duration-500 ${isLokesh ? 'text-primary/80' : 'text-slate-400/50'}`}>
                Lokesh
              </span>
            </div>

            {/* Nova */}
            <div className="flex flex-col items-center gap-2">
              <SpeakerAvatar speaker="nova" active={isNova} />
              <span className={`text-[9px] font-medium transition-colors duration-500 ${isNova ? 'text-cyan-400/80' : 'text-slate-400/50'}`}>
                Nova
              </span>
            </div>
          </div>

          {/* Dialogue area */}
          <div className="min-h-[80px] flex items-center justify-center">
            <AnimatePresence mode="wait">
              {isNarator ? (
                <motion.p
                  key={line.action}
                  className="text-sm text-slate-400 italic text-center leading-relaxed"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.3, ease: EASE }}
                >
                  {line.action}
                </motion.p>
              ) : (
                <motion.div
                  key={line.text}
                  className={`px-4 py-3 rounded-xl border max-w-xs ${
                    isLokesh
                      ? 'bg-primary/[0.06] border-primary/20 mr-auto ml-12'
                      : 'bg-cyan-500/[0.06] border-cyan-500/20 ml-auto mr-12'
                  }`}
                  initial={{ opacity: 0, y: 8, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.97 }}
                  transition={{ duration: 0.3, ease: EASE }}
                >
                  <p className={`text-sm font-medium ${
                    isLokesh ? 'text-white' : 'text-cyan-100'
                  }`}>
                    {line.text}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-0.5 bg-white/[0.04]">
          <motion.div
            className="h-full bg-gradient-to-r from-primary/50 to-cyan-500/50"
            style={{ width: `${(t / LOOP) * 100}%` }}
          />
        </div>
      </motion.div>
    </div>
  )
})
