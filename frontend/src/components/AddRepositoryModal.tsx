/**
 * AddRepositoryModal - Modal for adding new repositories
 */

import { motion, AnimatePresence } from 'framer-motion'
import { X, GitBranch, Loader2, Link as LinkIcon, AlertCircle } from 'lucide-react'
import { useState } from 'react'

import { cn } from '../lib/utils'

import { Input } from './ui'
import { Button, Card } from './ui-animated'

interface AddRepositoryModalProps {
  isOpen: boolean
  onClose: () => void
  onAdd: (url: string) => Promise<void>
  isLoading: boolean
}

export function AddRepositoryModal({ isOpen, onClose, onAdd, isLoading }: AddRepositoryModalProps) {
  const [repoUrl, setRepoUrl] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!repoUrl.trim()) {
      setError('Please enter a repository URL')
      return
    }

    // Validate URL format
    const gitUrlRegex = /^https:\/\/(github\.com|gitlab\.com|bitbucket\.org)\/[a-zA-Z0-9._-]+\/[a-zA-Z0-9._-]+(\/)?(\.git)?$/
    if (!gitUrlRegex.test(repoUrl.trim())) {
      setError('Please enter a valid repository URL (e.g., https://github.com/user/repo or https://gitlab.com/user/project)')
      return
    }

    try {
      await onAdd(repoUrl.trim())
      setRepoUrl('')
      onClose()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add repository. Please check the URL and try again.')
    }
  }

  const handleQuickAdd = (url: string) => {
    setRepoUrl(url)
    setError('')
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none"
          >
            <Card className="w-full max-w-lg p-6 pointer-events-auto" hover={false}>
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl font-bold text-foreground">Add Repository</h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    Add a repository to track and scan
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-white/5 rounded-lg transition-colors"
                  disabled={isLoading}
                >
                  <X className="h-5 w-5 text-muted-foreground" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Repository URL Input */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Repository URL
                  </label>
                  <div className="relative">
                    <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                      <Input
                        type="url"
                        placeholder="https://github.com/user/repo or https://gitlab.com/user/project"
                      value={repoUrl}
                      onChange={(e) => {
                        setRepoUrl(e.target.value)
                        setError('')
                      }}
                      className="pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                      disabled={isLoading}
                      autoFocus
                    />
                  </div>
                  {error && (
                    <div className="mt-2 flex items-center gap-2 text-sm text-red-400">
                      <AlertCircle className="h-4 w-4" />
                      <span>{error}</span>
                    </div>
                  )}
                </div>

                {/* Quick Add Suggestions */}
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">Quick add:</p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => handleQuickAdd('https://github.com/facebook/react')}
                      className="px-3 py-1.5 text-xs bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-colors"
                    >
                      <GitBranch className="h-3 w-3 inline mr-1" />
                      React
                    </button>
                    <button
                      type="button"
                      onClick={() => handleQuickAdd('https://github.com/microsoft/vscode')}
                      className="px-3 py-1.5 text-xs bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-colors"
                    >
                      <GitBranch className="h-3 w-3 inline mr-1" />
                      VS Code
                    </button>
                    <button
                      type="button"
                      onClick={() => handleQuickAdd('https://gitlab.com/gitlab-org/gitlab')}
                      className="px-3 py-1.5 text-xs bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-colors"
                    >
                      <GitBranch className="h-3 w-3 inline mr-1" />
                      GitLab
                    </button>
                  </div>
                </div>

                {/* Info Box */}
                <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                  <p className="text-xs text-blue-400">
                    <strong>Note:</strong> The repository will be analyzed for security, reliability,
                    scalability, and cost optimization issues.
                  </p>
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-4">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={onClose}
                    className="flex-1"
                    disabled={isLoading}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    className="flex-1"
                    disabled={isLoading || !repoUrl.trim()}
                    icon={isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitBranch className="h-4 w-4" />}
                  >
                    {isLoading ? 'Adding...' : 'Add Repository'}
                  </Button>
                </div>
              </form>
            </Card>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
