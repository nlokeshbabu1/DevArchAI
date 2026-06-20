import { motion } from 'framer-motion'
import { Brain, Sparkles, Code, Lightbulb, AlertTriangle, CheckCircle, ArrowRight, User, Bot, Shield, BookOpen, FileText, Wrench, Target, Search } from 'lucide-react'
import { cn } from '../../lib/utils'

const bulletPoints = [
  { icon: AlertTriangle, label: 'Risk explanation', color: 'text-red-400' },
  { icon: Target, label: 'Impact analysis', color: 'text-orange-400' },
  { icon: Search, label: 'Root cause', color: 'text-yellow-400' },
  { icon: Wrench, label: 'Production fix', color: 'text-green-400' },
  { icon: BookOpen, label: 'Best practices', color: 'text-blue-400' },
  { icon: FileText, label: 'Documentation links', color: 'text-purple-400' },
]

export function AIAssistantSection() {
  return (
    <section className="py-20 lg:py-32 bg-gradient-to-b from-white/[0.02] to-transparent">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16 space-y-4">
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/30"
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">AI-Powered Security Analysis</span>
          </motion.div>
          <h2 className="text-4xl md:text-5xl font-bold gradient-text">
            AI Security Assistant
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Every finding includes comprehensive AI analysis with explanations, impact assessment, and production-ready fixes
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-12 max-w-6xl mx-auto items-start">
          {/* Left: Feature List */}
          <motion.div
            className="space-y-8"
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
          >
            <div className="space-y-4">
              <h3 className="text-2xl font-bold text-foreground">
                For Every Finding, You Get
              </h3>
              <p className="text-muted-foreground">
                Our AI engine analyzes each security issue and provides comprehensive remediation guidance
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {bulletPoints.map((point) => {
                const Icon = point.icon
                return (
                  <motion.div
                    key={point.label}
                    className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 hover:border-white/20 transition-all"
                    whileHover={{ x: 4 }}
                  >
                    <div className={cn('p-1.5 rounded-lg bg-white/5', point.color)}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <span className="text-sm text-foreground">{point.label}</span>
                  </motion.div>
                )
              })}
            </div>

            <div className="p-5 rounded-xl bg-gradient-to-br from-primary/10 to-indigo-600/10 border border-primary/30">
              <div className="flex items-start gap-3">
                <Sparkles className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-foreground">Context-Aware AI</p>
                  <p className="text-sm text-muted-foreground">
                    The AI understands your specific infrastructure context — whether it's Terraform, Kubernetes, Docker, or CI/CD — and provides tailored remediation.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Right: Chat UI Example */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
          >
            <div className="rounded-2xl border border-white/10 bg-black/40 backdrop-blur-sm overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10 bg-white/5">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/70" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
                  <div className="w-3 h-3 rounded-full bg-green-500/70" />
                </div>
                <span className="text-xs text-muted-foreground ml-2">AI Security Assistant</span>
              </div>

              <div className="p-4 space-y-4">
                {/* User message */}
                <div className="flex items-start gap-3 justify-end">
                  <div className="max-w-[80%] p-3 rounded-2xl rounded-br-sm bg-primary/20 border border-primary/30">
                    <div className="flex items-center gap-2 mb-1">
                      <User className="h-3.5 w-3.5 text-primary" />
                      <span className="text-xs font-medium text-primary">Developer</span>
                    </div>
                    <p className="text-sm text-foreground">
                      Why is this Terraform resource insecure?
                    </p>
                  </div>
                </div>

                {/* AI message */}
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-xl bg-gradient-to-br from-primary to-indigo-600 flex-shrink-0">
                    <Bot className="h-4 w-4 text-white" />
                  </div>
                  <div className="max-w-[80%] space-y-3">
                    <div className="p-3 rounded-2xl rounded-bl-sm bg-white/5 border border-white/10">
                      <div className="flex items-center gap-2 mb-2">
                        <Sparkles className="h-3.5 w-3.5 text-yellow-400" />
                        <span className="text-xs font-medium text-yellow-400">AI Analysis</span>
                      </div>
                      <p className="text-sm text-foreground mb-3">
                        This resource allows public access and lacks encryption. The S3 bucket has <code className="px-1 py-0.5 rounded bg-red-500/20 text-red-400 text-xs font-mono">acl = "public-read"</code> which exposes data to the internet.
                      </p>

                      <div className="space-y-2">
                        <div className="flex items-start gap-2 text-xs">
                          <AlertTriangle className="h-3.5 w-3.5 text-red-400 mt-0.5 flex-shrink-0" />
                          <span className="text-red-400"><strong>Risk:</strong> Data breach — anyone can read, list, or download your objects</span>
                        </div>
                        <div className="flex items-start gap-2 text-xs">
                          <Target className="h-3.5 w-3.5 text-orange-400 mt-0.5 flex-shrink-0" />
                          <span className="text-orange-400"><strong>Impact:</strong> Potential data exposure costing $4.45M avg. per breach</span>
                        </div>
                      </div>

                      <div className="mt-3 p-2.5 rounded-lg bg-black/40 border border-white/10">
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <Code className="h-3 w-3 text-green-400" />
                          <span className="text-xs font-medium text-green-400">Recommended Fix</span>
                        </div>
                        <pre className="text-xs font-mono text-foreground">
                          <code>{`resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}`}</code>
                        </pre>
                      </div>

                      <div className="flex items-center gap-2 mt-2 text-xs text-primary">
                        <CheckCircle className="h-3 w-3" />
                        <span>Fix verified against AWS best practices</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
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