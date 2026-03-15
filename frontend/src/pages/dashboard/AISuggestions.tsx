import { motion } from 'framer-motion'
import { Brain, Lightbulb, Code, CheckCircle, ArrowRight, Search, Filter } from 'lucide-react'
import { useState } from 'react'
import { CodeBlock } from '../../components/ui/code-block'
import { SeverityBadge } from '../../components/ui/severity-badge'
import { Button } from '../../components/ui'
import { AnimatedCard } from '../../components/ui/animated-card'

interface AISuggestion {
  id: string
  title: string
  description: string
  impact: string
  fixExample: string
  confidence: number
  category: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  filePath: string
}

// Mock data - replace with actual API call
const mockSuggestions: AISuggestion[] = [
  {
    id: '1',
    title: 'Add Remote Backend for Terraform',
    description: 'Terraform state is stored locally. Configure remote backend for team collaboration.',
    impact: 'Multiple engineers running terraform apply simultaneously can corrupt state, causing infrastructure drift.',
    fixExample: `terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}`,
    confidence: 95,
    category: 'Reliability',
    severity: 'high',
    filePath: 's3-cdn-modules/dev/backend.tf',
  },
  {
    id: '2',
    title: 'Enable S3 Bucket Encryption',
    description: 'S3 bucket does not have server-side encryption enabled.',
    impact: 'Data stored in the bucket is not encrypted at rest, potentially exposing sensitive information.',
    fixExample: `resource "aws_s3_bucket_server_side_encryption_configuration" "example" {
  bucket = aws_s3_bucket.example.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}`,
    confidence: 90,
    category: 'Security',
    severity: 'high',
    filePath: 's3-cdn-modules/modules/s3/s3-bucket.tf',
  },
  {
    id: '3',
    title: 'Add Resource Tags',
    description: 'Resources are missing standard tags for cost tracking and organization.',
    impact: 'Difficulty in tracking resource ownership and allocating costs across teams.',
    fixExample: `resource "aws_s3_bucket" "example" {
  bucket = "my-bucket"

  tags = {
    Environment = "production"
    Owner       = "devops-team"
    Project     = "my-project"
    CostCenter  = "engineering"
    ManagedBy   = "terraform"
  }
}`,
    confidence: 85,
    category: 'Cost',
    severity: 'medium',
    filePath: 's3-cdn-modules/modules/s3/s3-bucket.tf',
  },
]

export function AISuggestionsPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedSuggestion, setSelectedSuggestion] = useState<AISuggestion | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string>('all')

  const filteredSuggestions = mockSuggestions.filter(suggestion => {
    const matchesSearch = suggestion.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      suggestion.description.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCategory = categoryFilter === 'all' || suggestion.category === categoryFilter
    return matchesSearch && matchesCategory
  })

  const categories = ['all', ...new Set(mockSuggestions.map(s => s.category))]

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold text-foreground">AI Suggestions</h1>
          <p className="text-muted-foreground mt-1">
            AI-powered recommendations to improve your infrastructure
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-4 py-2 bg-card/60 backdrop-blur-xl border border-white/10 rounded-xl">
            <Brain className="h-5 w-5 text-primary" />
            <span className="text-sm font-medium text-foreground">{mockSuggestions.length} suggestions</span>
          </div>
        </div>
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="flex flex-col sm:flex-row gap-4"
      >
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search suggestions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-card/60 backdrop-blur-xl border border-white/10 rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-4 py-2 bg-card/60 backdrop-blur-xl border border-white/10 rounded-xl text-foreground focus:outline-none"
          >
            {categories.map(cat => (
              <option key={cat} value={cat}>
                {cat.charAt(0).toUpperCase() + cat.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </motion.div>

      {/* Suggestions Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {filteredSuggestions.map((suggestion, index) => (
          <AnimatedCard
            key={suggestion.id}
            delay={index * 0.1}
            onClick={() => setSelectedSuggestion(suggestion)}
            className="cursor-pointer"
          >
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className="p-2.5 bg-primary/15 rounded-xl border border-primary/30">
                    <Lightbulb className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-foreground">{suggestion.title}</h3>
                    <p className="text-sm text-muted-foreground mt-1">{suggestion.description}</p>
                  </div>
                </div>
                <SeverityBadge severity={suggestion.severity} size="sm" />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="text-xs text-muted-foreground">{suggestion.category}</span>
                  <span className="text-xs text-muted-foreground">{suggestion.confidence}% confidence</span>
                </div>
                <Button variant="ghost" size="sm">
                  View Details
                  <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </Button>
              </div>
            </div>
          </AnimatedCard>
        ))}
      </div>

      {filteredSuggestions.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center py-12"
        >
          <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-foreground mb-2">No suggestions found</h3>
          <p className="text-muted-foreground">Try adjusting your search or filters.</p>
        </motion.div>
      )}

      {/* Detail Modal */}
      {selectedSuggestion && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedSuggestion(null)}
        >
          <motion.div
            initial={{ scale: 0.9, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            className="bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30 rounded-2xl p-6 max-w-3xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="space-y-6">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className="p-2.5 bg-primary/15 rounded-xl border border-primary/30">
                    <Lightbulb className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-foreground">{selectedSuggestion.title}</h2>
                    <p className="text-muted-foreground mt-1">{selectedSuggestion.filePath}</p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedSuggestion(null)}
                  className="p-2 hover:bg-white/5 rounded-lg transition-colors"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="flex items-center gap-4">
                <SeverityBadge severity={selectedSuggestion.severity} />
                <span className="text-sm text-muted-foreground">{selectedSuggestion.category}</span>
                <span className="text-sm text-muted-foreground">{selectedSuggestion.confidence}% confidence</span>
              </div>

              <div className="p-4 bg-orange-500/10 border border-orange-500/30 rounded-xl">
                <div className="flex items-center gap-2 mb-2">
                  <svg className="h-4 w-4 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <span className="text-sm font-medium text-orange-400">Impact</span>
                </div>
                <p className="text-sm text-muted-foreground">{selectedSuggestion.impact}</p>
              </div>

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Code className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium text-foreground">Suggested Fix</span>
                </div>
                <CodeBlock
                  code={selectedSuggestion.fixExample}
                  language="terraform"
                  title="Example"
                  showLineNumbers
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-white/10">
                <Button variant="ghost" onClick={() => setSelectedSuggestion(null)}>
                  Close
                </Button>
                <Button variant="primary">
                  Apply Fix
                  <CheckCircle className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  )
}
