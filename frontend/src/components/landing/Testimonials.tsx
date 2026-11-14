import { motion, useReducedMotion } from 'framer-motion'
import { Quote, Star } from 'lucide-react'
import { memo, useState, useEffect } from 'react'

interface Testimonial {
  id: number
  name: string
  role: string
  company: string
  content: string
  rating: number
  avatar: string
}

const testimonials: Testimonial[] = [
  {
    id: 1,
    name: 'Sarah Chen',
    role: 'Head of Platform Engineering',
    company: 'Meridian Health',
    content: 'DevArchAI caught 3 critical misconfigurations in our Terraform modules that our previous scanner missed entirely. The AI-generated fixes saved us days of research.',
    rating: 5,
    avatar: 'SC',
  },
  {
    id: 2,
    name: 'Marcus Rodriguez',
    role: 'Senior DevOps Engineer',
    company: 'Atlas Financial',
    content: 'We integrated DevArchAI into our GitHub Actions pipeline and it reduced our security review time from 2 hours to 15 minutes per PR. The compliance reports are a game-changer.',
    rating: 5,
    avatar: 'MR',
  },
  {
    id: 3,
    name: 'Priya Patel',
    role: 'CISO',
    company: 'NovaTech',
    content: 'Finally, a security scanner that speaks the language of DevOps. The Kubernetes and Helm detection is incredibly accurate, and the AI remediation actually works.',
    rating: 5,
    avatar: 'PP',
  },
  {
    id: 4,
    name: 'James O\'Brien',
    role: 'SRE Lead',
    company: 'CloudScale Systems',
    content: 'The 30-second scan time is no joke. We run it on every push across 40+ repositories and it never slows down our deployment velocity. The posture tracking dashboard is brilliant.',
    rating: 5,
    avatar: 'JO',
  },
  {
    id: 5,
    name: 'Elena Vasquez',
    role: 'DevSecOps Architect',
    company: 'Quantum Labs',
    content: 'We evaluated 6 different IaC security tools. DevArchAI was the only one that covered all our technologies — Docker, K8s, Terraform, and GitHub Actions — in a single scan.',
    rating: 5,
    avatar: 'EV',
  },
  {
    id: 6,
    name: 'David Kim',
    role: 'Engineering Manager',
    company: 'Streamline Inc',
    content: 'The SOC 2 compliance reports alone justify the Pro plan. Our auditors were impressed by the detailed findings and clear remediation steps.',
    rating: 5,
    avatar: 'DK',
  },
]

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

const TestimonialCard = memo(function TestimonialCard({ testimonial }: { testimonial: Testimonial }) {
  return (
    <div className="testimonial-card rounded-2xl p-6 min-w-[340px] max-w-[380px] flex-shrink-0">
      {/* Quote icon */}
      <div className="mb-4">
        <Quote className="h-6 w-6 text-primary/40" />
      </div>

      {/* Rating */}
      <div className="flex items-center gap-1 mb-3">
        {Array.from({ length: testimonial.rating }).map((_, i) => (
          <Star key={i} className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
        ))}
      </div>

      {/* Content */}
      <p className="text-sm text-slate-300 leading-relaxed mb-5">
        &ldquo;{testimonial.content}&rdquo;
      </p>

      {/* Author */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-primary/15 border border-primary/20 flex items-center justify-center">
          <span className="text-xs font-semibold text-primary">{testimonial.avatar}</span>
        </div>
        <div>
          <p className="text-sm font-medium text-white">{testimonial.name}</p>
          <p className="text-xs text-slate-400">{testimonial.role} at {testimonial.company}</p>
        </div>
      </div>
    </div>
  )
})

export const Testimonials = memo(function Testimonials() {
  const prefersReducedMotion = useReducedMotion()
  const isMobile = useIsMobile()

  return (
    <section className="py-16 lg:py-24 overflow-hidden" aria-label="Testimonials">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 mb-10">
        <div className="text-center space-y-3">
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/[0.06] border border-primary/20"
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <Star className="h-4 w-4 text-amber-400 fill-amber-400" />
            <span className="text-sm font-medium text-primary/90">Trusted by Engineering Teams</span>
          </motion.div>

          <motion.h2
            className="display-lg text-white"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            Loved by DevOps engineers
          </motion.h2>
          <motion.p
            className="text-base text-slate-400 max-w-2xl mx-auto"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          >
            See what engineering teams are saying about DevArchAI
          </motion.p>
        </div>
      </div>

      {isMobile ? (
        /* Static grid on mobile */
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid gap-4">
            {testimonials.slice(0, 3).map((t) => (
              <TestimonialCard key={t.id} testimonial={t} />
            ))}
          </div>
        </div>
      ) : (
        /* Scrolling marquee on desktop */
        <div className="relative">
          {/* Fade edges */}
          <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-[#0B1020] to-transparent z-10 pointer-events-none" />
          <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-[#0B1020] to-transparent z-10 pointer-events-none" />

          {/* Scrolling container */}
          <div
            className={`flex gap-4 ${!prefersReducedMotion ? 'animate-infinite-scroll' : ''}`}
            style={{ width: 'max-content' }}
          >
            {[...testimonials, ...testimonials].map((t, i) => (
              <TestimonialCard key={`${t.id}-${i}`} testimonial={t} />
            ))}
          </div>
        </div>
      )}
    </section>
  )
})
