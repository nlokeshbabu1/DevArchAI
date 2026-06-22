/**
 * Repository Selection Modal
 *
 * Provider-agnostic modal for selecting repositories/projects to import.
 * Supports both GitHub and GitLab.
 */

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Github, Gitlab, Check, Loader2, Search } from 'lucide-react'
import { Button } from '../components/ui-animated'
import { Badge } from '../components/ui'
import { cn } from '../lib/utils'

interface RepoItem {
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

interface RepoSelectionModalProps {
  isOpen: boolean
  onClose: () => void
  onImport: (repoIds: number[]) => Promise<void>
  repos: RepoItem[]
  isLoading: boolean
  provider: 'github' | 'gitlab'
  connected: boolean
  statusMessage?: string
  hasError?: boolean
}

function getProviderConfig(provider: 'github' | 'gitlab') {
  return provider === 'github'
    ? {
        icon: Github,
        name: 'GitHub',
        placeholder: 'Search GitHub repositories...',
        emptyTitle: 'GitHub not connected',
        emptyDesc: 'Connect GitHub with OAuth to import repositories here.',
        allImported: 'All available GitHub repositories are already imported.',
      }
    : {
        icon: Gitlab,
        name: 'GitLab',
        placeholder: 'Search GitLab projects...',
        emptyTitle: 'GitLab not connected',
        emptyDesc: 'Connect GitLab with OAuth to import projects here.',
        allImported: 'All available GitLab projects are already imported.',
      }
}

export function RepoSelectionModal({
  isOpen,
  onClose,
  onImport,
  repos,
  isLoading,
  provider,
  connected = true,
  statusMessage,
  hasError = false,
}: RepoSelectionModalProps) {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [searchTerm, setSearchTerm] = useState('')
  const [isImporting, setIsImporting] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)

  const config = getProviderConfig(provider)
  const ProviderIcon = config.icon
  const label = provider === 'github' ? 'repository' : 'project'
  const labelPlural = provider === 'github' ? 'repositories' : 'projects'

  useEffect(() => {
    if (!isOpen) return
    setSelectedIds(new Set())
    setSearchTerm('')
    setImportError(null)
  }, [isOpen])

  const filteredRepos = repos.filter(repo => {
    const name = repo.full_name?.toLowerCase() || ''
    const desc = repo.description?.toLowerCase() || ''
    const search = searchTerm.toLowerCase()
    return name.includes(search) || desc.includes(search)
  })

  const toggleRepo = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectAll = () => setSelectedIds(new Set(filteredRepos.map(r => r.id)))
  const deselectAll = () => setSelectedIds(new Set())

  const handleImport = async () => {
    if (selectedIds.size === 0) return
    setIsImporting(true)
    setImportError(null)
    try {
      await onImport(Array.from(selectedIds))
      onClose()
    } catch (error: any) {
      console.error(`Failed to import ${labelPlural}:`, error)
      setImportError(error.response?.data?.detail || `Failed to import ${labelPlural}. Please try again.`)
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
        onClick={() => { if (!isImporting) onClose() }}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: 20 }}
          onClick={e => e.stopPropagation()}
          className="flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-white/10 bg-card shadow-2xl"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10">
                <ProviderIcon className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-foreground">Select {config.name} {labelPlural}</h2>
                <p className="text-sm text-muted-foreground">
                  Choose which {labelPlural} to import
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              disabled={isImporting}
              className="rounded-lg p-2 transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <X className="h-5 w-5 text-muted-foreground" />
            </button>
          </div>

          {/* Search & Actions */}
          <div className="space-y-3 border-b border-white/10 p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder={config.placeholder}
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-white/5 py-2 pl-10 pr-4 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="text-muted-foreground">
                {selectedIds.size} of {filteredRepos.length} selected
              </span>
              <div className="flex gap-2">
                <button onClick={selectAll} className="text-primary hover:text-primary/80 text-xs font-medium">
                  Select All
                </button>
                <span className="text-muted-foreground">|</span>
                <button onClick={deselectAll} className="text-muted-foreground hover:text-foreground text-xs font-medium">
                  Deselect All
                </button>
              </div>
            </div>
          </div>

          {/* Project List */}
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {isLoading ? (
              <div className="text-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
                <p className="text-muted-foreground">Loading {labelPlural}...</p>
              </div>
            ) : filteredRepos.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.03] px-6 py-12 text-center">
                <ProviderIcon className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
                <h3 className="text-lg font-semibold text-foreground">
                  {hasError
                    ? `Unable to load ${labelPlural}`
                    : !connected
                    ? config.emptyTitle
                    : searchTerm
                    ? `No ${labelPlural} match your search`
                    : `No ${labelPlural} available to import`}
                </h3>
                <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                  {statusMessage || (hasError
                    ? 'A temporary error prevented loading. Please try again.'
                    : !connected
                    ? config.emptyDesc
                    : searchTerm
                    ? 'Try a different name or clear the current search.'
                    : config.allImported)}
                </p>
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
                      {isSelected ? <Check className="h-4 w-4" /> : <div className="h-4 w-4" />}
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
                      <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
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
          <div className="border-t border-white/10 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <span className="text-sm text-muted-foreground">
                  {selectedIds.size === 0
                    ? `Select at least one ${label}`
                    : `${selectedIds.size} ${labelPlural} selected`}
                </span>
                {importError && <p className="text-sm text-red-400">{importError}</p>}
              </div>
              <div className="flex gap-3">
                <Button variant="ghost" onClick={onClose} disabled={isImporting}>
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
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
