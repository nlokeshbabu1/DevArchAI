/**
 * DiffViewer - Production-grade code diff viewer
 * Shows before/after code changes with syntax highlighting
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import { ChevronDown, ChevronUp, Code, FileDiff } from 'lucide-react'
import { Card } from './ui-animated'
import { cn } from '../lib/utils'

interface DiffViewerProps {
  beforeCode?: string
  afterCode?: string
  unifiedDiff?: string
  filename?: string
}

export function DiffViewer({ 
  beforeCode, 
  afterCode, 
  unifiedDiff,
  filename = 'file'
}: DiffViewerProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const [viewMode, setViewMode] = useState<'split' | 'unified'>('split')

  // Don't render if no diff data
  if (!beforeCode || !afterCode) {
    return null
  }

  // Parse unified diff for line-by-line rendering
  const parseDiff = (diff: string) => {
    const lines = diff.split('\n')
    const added: string[] = []
    const removed: string[] = []

    lines.forEach(line => {
      if (line.startsWith('+') && !line.startsWith('+++')) {
        added.push(line.substring(1))
      } else if (line.startsWith('-') && !line.startsWith('---')) {
        removed.push(line.substring(1))
      }
    })

    return { added, removed }
  }

  const diffData = unifiedDiff ? parseDiff(unifiedDiff) : null

  return (
    <Card className="p-6" hover={false}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/30">
            <FileDiff className="h-5 w-5 text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">
              Code Changes (Diff)
            </h3>
            <p className="text-xs text-muted-foreground">
              {filename}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex rounded-lg border border-white/10 overflow-hidden">
            <button
              onClick={() => setViewMode('split')}
              className={cn(
                'px-3 py-1.5 text-xs font-medium transition-colors',
                viewMode === 'split'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              Split
            </button>
            <button
              onClick={() => setViewMode('unified')}
              className={cn(
                'px-3 py-1.5 text-xs font-medium transition-colors',
                viewMode === 'unified'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              Unified
            </button>
          </div>

          {/* Expand/Collapse */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 rounded-lg hover:bg-white/5 transition-colors"
          >
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        </div>
      </div>

      {/* Diff Stats */}
      {diffData && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4 mb-4 text-xs"
        >
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-red-500/20 border border-red-500/50" />
            <span className="text-red-400 font-medium">
              -{diffData.removed.length} lines removed
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-green-500/20 border border-green-500/50" />
            <span className="text-green-400 font-medium">
              +{diffData.added.length} lines added
            </span>
          </div>
        </motion.div>
      )}

      {/* Code Diff Viewer */}
      {isExpanded && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="rounded-xl border border-white/10 overflow-hidden"
        >
          {viewMode === 'split' ? (
            <div className="grid grid-cols-2 gap-0">
              {/* Before Code */}
              <div className="border-r border-white/10">
                <div className="px-4 py-2 bg-red-500/10 border-b border-white/10">
                  <div className="flex items-center gap-2 text-xs font-medium text-red-400">
                    <FileDiff className="h-3 w-3" />
                    Before
                  </div>
                </div>
                <pre className="p-4 bg-black/50 overflow-x-auto max-h-[600px] text-sm">
                  <code className="text-red-300 font-mono whitespace-pre">
                    {beforeCode}
                  </code>
                </pre>
              </div>

              {/* After Code */}
              <div>
                <div className="px-4 py-2 bg-green-500/10 border-b border-white/10">
                  <div className="flex items-center gap-2 text-xs font-medium text-green-400">
                    <Code className="h-3 w-3" />
                    After
                  </div>
                </div>
                <pre className="p-4 bg-black/50 overflow-x-auto max-h-[600px] text-sm">
                  <code className="text-green-300 font-mono whitespace-pre">
                    {afterCode}
                  </code>
                </pre>
              </div>
            </div>
          ) : (
            <div>
              <div className="px-4 py-2 bg-blue-500/10 border-b border-white/10">
                <div className="flex items-center gap-2 text-xs font-medium text-blue-400">
                  <FileDiff className="h-3 w-3" />
                  Unified Diff
                </div>
              </div>
              <pre className="p-4 bg-black/50 overflow-x-auto max-h-[600px] text-sm font-mono">
                {unifiedDiff && (
                  <div>
                    {unifiedDiff.split('\n').map((line, index) => {
                      let lineClass = 'text-gray-400'
                      if (line.startsWith('+') && !line.startsWith('+++')) {
                        lineClass = 'text-green-400 bg-green-500/10'
                      } else if (line.startsWith('-') && !line.startsWith('---')) {
                        lineClass = 'text-red-400 bg-red-500/10'
                      } else if (line.startsWith('@@')) {
                        lineClass = 'text-blue-400 font-semibold'
                      }
                      
                      return (
                        <div key={index} className={cn('px-2', lineClass)}>
                          {line || '\u00A0'}
                        </div>
                      )
                    })}
                  </div>
                )}
              </pre>
            </div>
          )}
        </motion.div>
      )}
    </Card>
  )
}
