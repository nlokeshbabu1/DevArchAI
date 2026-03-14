import { motion } from 'framer-motion'
import { Shield, Zap, Cloud, Code, Lock } from 'lucide-react'

export function ScanningAnimation() {
  return (
    <div className="relative w-full max-w-2xl mx-auto">
      {/* Main scanning circle */}
      <div className="relative flex items-center justify-center">
        {/* Outer rotating ring */}
        <motion.div
          className="absolute w-64 h-64 rounded-full border-2 border-dashed border-primary/30"
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
        />
        
        {/* Middle rotating ring (opposite direction) */}
        <motion.div
          className="absolute w-48 h-48 rounded-full border-2 border-dashed border-indigo-500/30"
          animate={{ rotate: -360 }}
          transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
        />
        
        {/* Inner pulsing circle */}
        <motion.div
          className="w-32 h-32 rounded-full bg-gradient-to-br from-primary/20 to-indigo-600/20 flex items-center justify-center"
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <Shield className="h-12 w-12 text-primary" />
        </motion.div>

        {/* Orbiting icons */}
        {[
          { Icon: Code, delay: 0, radius: 140 },
          { Icon: Cloud, delay: 0.5, radius: 140 },
          { Icon: Lock, delay: 1, radius: 140 },
          { Icon: Zap, delay: 1.5, radius: 140 },
        ].map(({ Icon, delay, radius }, index) => (
          <motion.div
            key={index}
            className="absolute"
            style={{ width: radius * 2, height: radius * 2 }}
            animate={{ rotate: 360 }}
            transition={{
              duration: 10,
              repeat: Infinity,
              ease: 'linear',
              delay: delay * 2,
            }}
          >
            <motion.div
              className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 p-2 rounded-lg bg-gradient-to-br from-primary/20 to-indigo-600/20 border border-primary/30"
              animate={{ scale: [1, 1.2, 1] }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                delay: delay,
              }}
            >
              <Icon className="h-5 w-5 text-primary" />
            </motion.div>
          </motion.div>
        ))}
      </div>

      {/* Scanning beam effect */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: 'conic-gradient(from 0deg, transparent, rgba(99, 102, 241, 0.3), transparent)',
        }}
        animate={{ rotate: 360 }}
        transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  )
}

export function LoadingDots() {
  return (
    <div className="flex items-center gap-1">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-2 h-2 rounded-full bg-primary"
          animate={{ y: [0, -8, 0] }}
          transition={{
            duration: 0.6,
            repeat: Infinity,
            delay: i * 0.1,
          }}
        />
      ))}
    </div>
  )
}

export function PulseGlow({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div
      className={className}
      animate={{
        boxShadow: [
          '0 0 20px rgba(99, 102, 241, 0.3)',
          '0 0 40px rgba(99, 102, 241, 0.6)',
          '0 0 20px rgba(99, 102, 241, 0.3)',
        ],
      }}
      transition={{ duration: 2, repeat: Infinity }}
    >
      {children}
    </motion.div>
  )
}
