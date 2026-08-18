import { useParams, Navigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { DocsLayout } from './DocsLayout'
import { getPage, type DocPage } from './docs-data'
import { PAGE_CONTENT } from './DocsContent'

import {
  BookOpen, Cloud, Server, Github, Gitlab,
  Brain, AlertTriangle, FileText, Bug, Rocket,
  FolderGit2, ArrowRight,
} from 'lucide-react'

function DocPageRenderer({ page }: { page: DocPage }) {
  const Content = PAGE_CONTENT[page.slug]
  if (!Content) return <Navigate to="/docs" replace />
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Content />
    </motion.div>
  )
}

export function DocPage() {
  const { slug } = useParams<{ slug: string }>()
  const page = slug ? getPage(slug) : undefined

  if (!page) {
    return <Navigate to="/docs" replace />
  }

  return (
    <DocsLayout page={page}>
      <DocPageRenderer page={page} />
    </DocsLayout>
  )
}

const QUICK_START_CARDS = [
  { href: '/docs/getting-started', label: 'Getting Started', desc: 'Set up your account and run your first scan', icon: Rocket },
  { href: '/docs/github-integration', label: 'GitHub Integration', desc: 'Connect GitHub repositories', icon: Github },
  { href: '/docs/gitlab-integration', label: 'GitLab Integration', desc: 'Connect GitLab repositories', icon: Gitlab },
  { href: '/docs/aws-integration', label: 'AWS Integration', desc: 'Connect your AWS account', icon: Cloud },
  { href: '/docs/azure-integration', label: 'Azure Integration', desc: 'Connect your Azure subscription', icon: Server },
  { href: '/docs/repository-scanning', label: 'Repository Scanning', desc: 'How DevArchAI scans your code', icon: FolderGit2 },
  { href: '/docs/ai-recommendations', label: 'AI Recommendations', desc: 'AI-powered fix suggestions', icon: Brain },
  { href: '/docs/security-findings', label: 'Security Findings', desc: 'Severity levels and remediation', icon: AlertTriangle },
  { href: '/docs/pdf-reports', label: 'Reports', desc: 'Generate and export audit reports', icon: FileText },
  { href: '/docs/troubleshooting', label: 'Troubleshooting', desc: 'Common issues and solutions', icon: Bug },
]

export function DocsHome() {
  return (
    <DocsLayout page={null}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-12"
      >
        {/* Hero */}
        <div className="text-center py-8 lg:py-12">
          <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 mb-6">
            <BookOpen className="h-10 w-10 text-white" />
          </div>
          <h1 className="text-4xl lg:text-5xl font-bold text-foreground tracking-tight">
            Documentation Center
          </h1>
          <p className="text-lg text-muted-foreground mt-3 max-w-2xl mx-auto">
            Everything you need to get started with infrastructure security scanning, from setting up your account to integrating cloud providers.
          </p>
        </div>

        {/* Quick Start Cards */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {QUICK_START_CARDS.map((card) => {
            const Icon = card.icon
            return (
              <Link
                key={card.href}
                to={card.href}
                className="flex items-start gap-4 p-5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-primary/30 transition-all group"
              >
                <div className="p-2.5 rounded-lg bg-primary/10 border border-primary/20 flex-shrink-0">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">{card.label}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{card.desc}</p>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors flex-shrink-0 mt-1 ml-auto" />
              </Link>
            )
          })}
        </div>

        {/* CTA */}
        <div className="text-center py-8">
          <p className="text-sm text-muted-foreground">
            Still need help? Contact us at <strong className="text-foreground">support@devarchai.com</strong>
          </p>
        </div>
      </motion.div>
    </DocsLayout>
  )
}
