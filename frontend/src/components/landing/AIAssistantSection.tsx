import { motion, useReducedMotion } from 'framer-motion'
import { Sparkles, AlertTriangle, CheckCircle, ArrowRight, User, Bot, Shield, BookOpen, Wrench, Target, Search, FileText, Code } from 'lucide-react'
import { memo } from 'react'

import { cn } from '../../lib/utils'

const bulletPoints = [
  { icon: AlertTriangle, label: 'Risk explanation', color: 'text-red-400' },
  { icon: Target, label: 'Impact analysis', color: 'text-orange-400' },
  { icon: Search, label: 'Root cause', color: 'text-yellow-400' },
  { icon: Wrench, label: 'Production fix', color: 'text-green-400' },
  { icon: BookOpen, label: 'Best practices', color: 'text-blue-400' },
  { icon: FileText, label: 'Documentation links', color: 'text-purple-400' },
]

const BulletItem = memo(function BulletItem({ point }: { point: typeof bulletPoints[0] }) {
  const Icon = point.icon
  return (
    <motion.div
      className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-white/[0.12] transition-all duration-200"
      whileHover={{ x: 3 }}
      transition={{ duration: 0.2 }}
    >
      <div className={cn('p-1.5 rounded-lg bg-white/[0.04]', point.color)}>
        <Icon className="h-4 w-4" />
      </div>
      <span className="text-sm text-foreground/90">{point.label}</span>
    </motion.div>
  )
})

export function AIAssistantSection() {
  return (
    <section className="py-20 lg:py-32 bg-gradient-to-b from-white/[0.02] to-transparent">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-14 space-y-3">
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/[0.06] border border-primary/20"
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <Sparkles className="h-4 w-4 text-primary/80" />
            <span className="text-sm font-medium text-primary/90">AI-Powered Security Analysis</span>
          </motion.div>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
            AI Security Assistant
          </h2>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            Every finding includes comprehensive AI analysis with explanations, impact assessment, and production-ready fixes
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-10 max-w-6xl mx-auto items-start">
          {/* Left: Feature List */}
          <motion.div
            className="space-y-7"
            initial={{ opacity: 0, x: -16 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
          >
            <div className="space-y-3">
              <h3 className="text-2xl font-bold text-foreground">
                For Every Finding, You Get
              </h3>
              <p className="text-muted-foreground text-[15px]">
                Our AI engine analyzes each security issue and provides comprehensive remediation guidance
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              {bulletPoints.map((point) => (
                <BulletItem key={point.label} point={point} />
              ))}
            </div>

            <div className="p-5 rounded-2xl bg-primary/[0.05] border border-primary/15">
              <div className="flex items-start gap-3">
                <Sparkles className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-foreground">Context-Aware AI</p>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    The AI understands your specific infrastructure context — whether it's Terraform, Kubernetes, Docker, or CI/CD — and provides tailored remediation.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Right: Chat UI Example */}
          <motion.div
            initial={{ opacity: 0, x: 16 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.5, delay: 0.1, ease: [0.25, 0.1, 0.25, 1] }}
          >
            <div className="rounded-2xl border border-white/[0.08] bg-card/40 backdrop-blur-xl overflow-hidden shadow-2xl shadow-black/20">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.06] bg-white/[0.02]">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
                  <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
                  <div className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
                </div>
                <span className="text-xs text-muted-foreground ml-2">AI Security Assistant</span>
              </div>

              <div className="p-4 space-y-4">
                {/* User message */}
                <div className="flex items-start gap-3 justify-end">
                  <div className="max-w-[80%] p-3 rounded-2xl rounded-br-sm bg-primary/15 border border-primary/20">
                    <div className="flex items-center gap-2 mb-1">
                      <User className="h-3.5 w-3.5 text-primary/80" />
                      <span className="text-xs font-medium text-primary/80">Developer</span>
                    </div>
                    <p className="text-sm text-foreground/90">
                      Why is this Terraform resource insecure?
                    </p>
                  </div>
                </div>

                {/* AI message */}
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-xl bg-gradient-to-br from-primary to-indigo-600 flex-shrink-0 shadow-lg shadow-primary/20">
                    <Bot className="h-4 w-4 text-white" />
                  </div>
                  <div className="max-w-[80%] space-y-3">
                    <div className="p-3 rounded-2xl rounded-bl-sm bg-white/[0.04] border border-white/[0.08]">
                      <div className="flex items-center gap-2 mb-2">
                        <Sparkles className="h-3.5 w-3.5 text-yellow-400/80" />
                        <span className="text-xs font-medium text-yellow-400/90">AI Analysis</span>
                      </div>
                      <p className="text-sm text-foreground/90 mb-3 leading-relaxed">
                        This resource allows public access and lacks encryption. The S3 bucket has <code className="px-1 py-0.5 rounded bg-red-500/15 text-red-400 text-xs font-mono">acl = &quot;public-read&quot;</code> which exposes data to the internet.
                      </p>

                      <div className="space-y-2">
                        <div className="flex items-start gap-2 text-xs">
                          <AlertTriangle className="h-3.5 w-3.5 text-red-400/80 mt-0.5 flex-shrink-0" />
                          <span className="text-red-400/90"><strong>Risk:</strong> Data breach — anyone can read, list, or download your objects</span>
                        </div>
                        <div className="flex items-start gap-2 text-xs">
                          <Target className="h-3.5 w-3.5 text-orange-400/80 mt-0.5 flex-shrink-0" />
                          <span className="text-orange-400/90"><strong>Impact:</strong> Potential data exposure costing $4.45M avg. per breach</span>
                        </div>
                      </div>

                      <div className="mt-3 p-2.5 rounded-lg bg-black/30 border border-white/[0.06]">
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <Code className="h-3 w-3 text-green-400/80" />
                          <span className="text-xs font-medium text-green-400/90">Recommended Fix</span>
                        </div>
                        <pre className="text-xs font-mono text-foreground/80 overflow-x-auto">
                          <code>{`resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}`}</code>
                        </pre>
                      </div>

                      <div className="flex items-center gap-2 mt-2.5 text-xs text-primary/80">
                        <CheckCircle className="h-3 w-3" />
                        <span>Fix verified against AWS best practices</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-muted-foreground/70 hover:text-muted-foreground transition-colors cursor-pointer">
                      <BookOpen className="h-3 w-3" />
                      <span>View documentation</span>
                      <ArrowRight className="h-3 w-3" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
