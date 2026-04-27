/**
 * GitHub Repository Selection Modal
 * 
 * Shown after GitHub login to let users select which repos to import.
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Github, Check, Loader2, Search } from 'lucide-react'
import { Button, Card } from '../components/ui-animated'
import { Badge } from '../components/ui'
import { cn } from '../lib/utils'
import apiClient from '../api/endpoints/client'

interface GitHubRepo {
  id: number
  full_name: string
  html_url: string
  description: string | null
  private: boolean
  default_branch: string
  language: string | null
  stargazers_count: number
  forks_count: number
  updated_at: string
}

interface GitHubRepoSelectionModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  repos: GitHubRepo[]
  isLoading: boolean
}

export function GitHubRepoSelectionModal({
  isOpen,
  onClose,
  onSuccess,
  repos,
  isLoading,
}: GitHubRepoSelectionModalProps) {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [searchTerm, setSearchTerm] = useState('')
  const [isImporting, setIsImporting] = useState(false)

  // Filter repos by search term
  const filteredRepos = repos.filter(repo => {
    const name = repo.full_name?.toLowerCase() || ''
    const desc = repo.description?.toLowerCase() || ''
    const search = searchTerm.toLowerCase()
    return name.includes(search) || desc.includes(search)
  })

  // Toggle repo selection
  const toggleRepo = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  // Select all filtered repos
  const selectAll = () => {
    const allIds = filteredRepos.map(r => r.id)
    setSelectedIds(new Set(allIds))
  }

  // Deselect all
  const deselectAll = () => {
    setSelectedIds(new Set())
  }

  // Import selected repos
  const handleImport = async () => {
    if (selectedIds.size === 0) return

    setIsImporting(true)
    try {
      await apiClient.post('/github/import-repos', Array.from(selectedIds))
      onSuccess()
      onClose()
    } catch (error) {
      console.error('Failed to import repos:', error)
      alert('Failed to import repositories. Please try again.')
    } finally {
      setIsImporting(false)
    }
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: 20 }}
          onClick={e => e.stopPropagation()}
          className="w-full max-w-3xl max-h-[80vh] flex flex-col bg-card border border-white/10 rounded-2xl shadow-2xl"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10">
                <Github className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-foreground">Select Repositories</h2>
                <p className="text-sm text-muted-foreground">
                  Choose which repositories to import
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            >
              <X className="h-5 w-5 text-muted-foreground" />
            </button>
          </div>

          {/* Search & Actions */}
          <div className="p-4 border-b border-white/10 space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search repositories..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                {selectedIds.size} of {filteredRepos.length} selected
              </span>
              <div className="flex gap-2">
                <button
                  onClick={selectAll}
                  className="text-primary hover:text-primary/80 text-xs font-medium"
                >
                  Select All
                </button>
                <span className="text-muted-foreground">|</span>
                <button
                  onClick={deselectAll}
                  className="text-muted-foreground hover:text-foreground text-xs font-medium"
                >
                  Deselect All
                </button>
              </div>
            </div>
          </div>

          {/* Repo List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {isLoading ? (
              <div className="text-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
                <p className="text-muted-foreground">Loading repositories...</p>
              </div>
            ) : filteredRepos.length === 0 ? (
              <div className="text-center py-12">
                <Github className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">No repositories found</p>
              </div>
            ) : (
              filteredRepos.map(repo => {
                const isSelected = selectedIds.has(repo.id)
                return (
                  <button
                    key={repo.id}
                    onClick={() => toggleRepo(repo.id)}
                    className={cn(
                      'w-full flex items-start gap-3 p-4 rounded-xl border transition-all text-left',
                      isSelected
                        ? 'bg-primary/10 border-primary/30'
                        : 'bg-white/5 border-white/10 hover:bg-white/10'
                    )}
                  >
                    <div className={cn(
                      'mt-1 p-1.5 rounded-md border transition-all',
                      isSelected
                        ? 'bg-primary border-primary text-primary-foreground'
                        : 'bg-white/5 border-white/20'
                    )}>
                      {isSelected ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <div className="h-4 w-4" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground truncate">
                          {repo.full_name}
                        </span>
                        {repo.private && (
                          <Badge variant="secondary" className="text-xs bg-yellow-500/10 text-yellow-400 border-yellow-500/30">
                            Private
                          </Badge>
                        )}
                      </div>
                      {repo.description && (
                        <p className="text-sm text-muted-foreground mt-1 line-clamp-1">
                          {repo.description}
                        </p>
                      )}
                      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                        {repo.language && <span>{repo.language}</span>}
                        <span>⭐ {repo.stargazers_count}</span>
                        <span>🍴 {repo.forks_count}</span>
                      </div>
                    </div>
                  </button>
                )
              })
            )}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-white/10 flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              {selectedIds.size === 0
                ? 'Select at least one repository'
                : `${selectedIds.size} repos selected`}
            </span>
            <div className="flex gap-3">
              <Button
                variant="ghost"
                onClick={onClose}
                disabled={isImporting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleImport}
                disabled={selectedIds.size === 0 || isImporting}
                icon={isImporting ? <Loader2 className="h-4 w-4 animate-spin" /> : undefined}
              >
                {isImporting ? 'Importing...' : `Import ${selectedIds.size > 0 ? `(${selectedIds.size})` : ''}`}
              </Button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
