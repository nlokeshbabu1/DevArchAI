import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { Github, Gitlab, Loader2, AlertCircle, GitBranch, ChevronDown, CheckCircle2, Globe } from 'lucide-react'

import { Card } from '../components/ui-animated'
import { api } from '../lib/api'
import { cn } from '../lib/utils'
import { scansApi } from '../api/endpoints/scans'
import { saveScanSessionToken } from '../lib/scan-session'

type RepoProvider = 'github' | 'gitlab' | 'unknown'
interface RepoInfo { owner: string; repo: string; provider: RepoProvider }

function parseRepoUrl(url: string): RepoInfo | null {
  try {
    const trimmed = url.trim().replace(/\/+$/, '')

    const ghMatch = trimmed.match(/(?:https?:\/\/)?github\.com\/([^/\s]+)\/([^/\s]+)/i)
    if (ghMatch) return { owner: ghMatch[1], repo: ghMatch[2].replace(/\.git$/, ''), provider: 'github' }

    const glMatch = trimmed.match(/(?:https?:\/\/)?gitlab\.com\/([^/\s]+(?:\/[^/\s]+)*)\/([^/\s]+)/i)
    if (glMatch) return { owner: glMatch[1], repo: glMatch[2].replace(/\.git$/, ''), provider: 'gitlab' }
  } catch { /* ignore */ }
  return null
}

function ProviderIcon({ provider, className }: { provider: RepoProvider; className?: string }) {
  if (provider === 'gitlab') return <Gitlab className={className} />
  return <Github className={className} />
}

export function ScanPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const prefersReducedMotion = useReducedMotion()

  const initialUrl = searchParams.get('url') || ''
  const initialBranch = searchParams.get('branch') || 'main'
  const autoStart = searchParams.get('auto') === 'true'
  const [repoUrl, setRepoUrl] = useState(initialUrl)
  const [selectedBranch, setSelectedBranch] = useState<string>(initialBranch)
  const [showBranchDropdown, setShowBranchDropdown] = useState(false)
  const autoSubmittedRef = useRef(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const [touched, setTouched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const parsed = useMemo(() => parseRepoUrl(repoUrl), [repoUrl])
  const urlValid = useMemo(() => {
    if (!repoUrl.trim()) return null
    return !!parsed
  }, [parsed, repoUrl])

  const { data: branchesData, isLoading: isLoadingBranches, error: branchesError, isFetching } = useQuery({
    queryKey: ['branches', repoUrl],
    queryFn: async () => {
      const trimmedUrl = repoUrl.trim()
      if (!trimmedUrl || !parsed) return { branches: [], default_branch: 'main' }
      const endpoint = parsed.provider === 'gitlab' ? '/gitlab/branches' : '/github/branches'
      try {
        const response = await api.get(endpoint, { params: { repo_url: trimmedUrl } })
        return response.data
      } catch (err: any) {
        return { branches: [], default_branch: 'main', error: err.response?.data?.detail || 'Failed to fetch branches' }
      }
    },
    enabled: !!parsed && !!repoUrl.trim(),
    staleTime: 2 * 60 * 1000,
    retry: false,
  })

  useEffect(() => {
    if (!branchesData?.default_branch) return
    if (initialUrl) return
    setSelectedBranch(branchesData.default_branch)
  }, [branchesData, initialUrl])

  const branches: { name: string; protected: boolean; commit_sha: string }[] = branchesData?.branches || []
  const isFetchingBranches = isLoadingBranches || isFetching
  const hasBranchesError = !!branchesData?.error || (branchesError && branches.length === 0)

  useEffect(() => {
    if (autoStart && repoUrl && !autoSubmittedRef.current && !loading) {
      autoSubmittedRef.current = true
      const timer = setTimeout(() => {
        const form = document.querySelector('form')
        if (form) form.requestSubmit()
      }, 800)
      return () => clearTimeout(timer)
    }
  }, [autoStart, repoUrl, loading])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) setShowBranchDropdown(false)
    }
    if (showBranchDropdown) document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showBranchDropdown])

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') setShowBranchDropdown(false)
  }, [])

  useEffect(() => {
    if (showBranchDropdown) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [showBranchDropdown, handleKeyDown])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setTouched(true)
    const trimmedUrl = repoUrl.trim()
    if (!trimmedUrl) { setError('Please enter a repository URL'); return }
    if (!parsed) { setError('Please enter a valid GitHub or GitLab repository URL'); return }
    setLoading(true)
    setError(null)
    try {
      const response = await scansApi.startUnifiedScan({ repository_url: trimmedUrl, branch: selectedBranch || 'main' })
      if (!response.scan_id) throw new Error('No scan_id returned from server')
      if (response.session_token) {
        saveScanSessionToken(response.scan_id, response.session_token)
      }
      navigate(`/scans/${response.scan_id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to analyze repository')
      setLoading(false)
    }
  }

  const animProps = prefersReducedMotion ? {} : {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#07070d]">
        <div className="text-center space-y-4">
          <motion.div
            animate={prefersReducedMotion ? {} : { rotate: 360 }}
            transition={prefersReducedMotion ? {} : { repeat: Infinity, duration: 1, ease: 'linear' }}
            className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-400 rounded-full mx-auto"
          />
          <p className="text-white/60 text-sm">Starting scan...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#07070d]">
        <Card className="p-8 max-w-md" hover={false}>
          <div className="text-center space-y-4">
            <AlertCircle className="h-12 w-12 text-red-400 mx-auto" />
            <h2 className="text-xl font-bold text-white">Scan Failed</h2>
            <p className="text-white/60 text-sm">{error}</p>
            <div className="flex gap-3">
              <button onClick={() => { setError(null); setLoading(false) }}
                className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 text-white border border-white/10 hover:bg-white/10 transition-colors text-sm font-medium">
                Try Again
              </button>
              <button onClick={() => navigate('/dashboard')}
                className="flex-1 px-4 py-2.5 rounded-xl text-white/60 hover:text-white hover:bg-white/5 transition-colors text-sm font-medium">
                Go Home
              </button>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#07070d] py-12">
      <div className="max-w-2xl w-full mx-auto px-4 space-y-6">
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold text-white">Analyze Your DevOps Architecture</h1>
          <p className="text-white/50 text-[15px]">Enter a GitHub or GitLab repository URL to get a comprehensive security analysis</p>
        </div>

        <motion.div {...animProps}>
          <Card className="p-8" hover={false}>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="relative">
                <label className="block text-sm font-medium text-white/50 mb-3">Repository URL</label>
                <div className="relative group">
                  <Github className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-white/40 pointer-events-none z-10" />
                  <input
                    ref={inputRef}
                    type="text"
                    value={repoUrl}
                    onChange={(e) => { setRepoUrl(e.target.value); setError(null) }}
                    onBlur={() => setTouched(true)}
                    placeholder="https://github.com/org/repo or https://gitlab.com/org/repo"
                    autoComplete="off"
                    autoCorrect="off"
                    autoCapitalize="off"
                    spellCheck={false}
                    className={cn(
                      'scan-input pl-12 pr-12 rounded-xl',
                      'placeholder:text-white/30',
                      'focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/60',
                      touched && urlValid === true && 'border-emerald-500/50 focus:ring-emerald-500/30',
                      touched && urlValid === false && repoUrl.trim() && 'border-red-500/50 focus:ring-red-500/30',
                      (!touched || urlValid === null) && 'border-white/[0.08]',
                    )}
                  />
                  {touched && repoUrl.trim() && urlValid !== null && (
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none z-10">
                      {urlValid === true
                        ? <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                        : <AlertCircle className="h-5 w-5 text-red-400" />}
                    </div>
                  )}
                </div>
                <AnimatePresence>
                  {touched && urlValid === false && repoUrl.trim() && (
                    <motion.p
                      initial={prefersReducedMotion ? false : { opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      className="text-xs text-red-400 mt-2"
                      role="alert"
                    >
                      Please enter a valid GitHub or GitLab URL
                    </motion.p>
                  )}
                </AnimatePresence>
                {!touched && <p className="text-xs text-white/30 mt-2">Enter a public GitHub or GitLab repository URL to analyze</p>}
              </div>

              <AnimatePresence>
                {parsed && (
                  <motion.div
                    initial={prefersReducedMotion ? false : { opacity: 0, height: 0, y: -8 }}
                    animate={{ opacity: 1, height: 'auto', y: 0 }}
                    exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, height: 0, y: -8 }}
                    transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                    className="overflow-hidden"
                  >
                    <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] backdrop-blur-xl p-4 space-y-4 relative">
                      <div className="absolute left-0 top-3 bottom-3 w-[2px] rounded-full bg-indigo-500/40" />
                      <div className="flex items-center gap-3 pl-2">
                        <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
                          <ProviderIcon provider={parsed.provider} className="h-4 w-4 text-indigo-400" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-medium text-white truncate">{parsed.owner} / {parsed.repo}</div>
                          <div className="text-xs text-white/40 font-mono">{parsed.provider === 'gitlab' ? 'gitlab.com' : 'github.com'}/{parsed.owner}/{parsed.repo}</div>
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-2 pl-2">
                        <span className="flex items-center gap-1.5 text-xs text-white/40">
                          <Globe className="w-3.5 h-3.5" />Public
                        </span>
                        <span className="text-white/10">|</span>
                        <div className="relative" ref={dropdownRef}>
                          <button
                            type="button"
                            role="listbox"
                            aria-label="Select branch"
                            onClick={() => setShowBranchDropdown(!showBranchDropdown)}
                            disabled={isFetchingBranches}
                            className={cn(
                              'flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg',
                              'bg-white/[0.04] border border-white/[0.08] text-white/60',
                              'hover:bg-white/[0.06] hover:border-white/[0.12] transition-colors',
                              'disabled:opacity-50 disabled:cursor-not-allowed outline-none focus:ring-2 focus:ring-indigo-500/40',
                            )}
                          >
                            {isFetchingBranches
                              ? <><Loader2 className="h-3 w-3 animate-spin" /><span>Fetching branches...</span></>
                              : <><GitBranch className="h-3 w-3" /><span>{selectedBranch || 'main'}</span></>}
                            <ChevronDown className={cn('h-3 w-3 text-white/30 transition-transform duration-200', showBranchDropdown && 'rotate-180')} />
                          </button>

                          <AnimatePresence>
                            {showBranchDropdown && (
                              <motion.div
                                initial={prefersReducedMotion ? false : { opacity: 0, y: -4, scale: 0.98 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: -4, scale: 0.98 }}
                                transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
                                className="absolute z-50 left-0 mt-1 min-w-[260px] max-h-60 overflow-auto rounded-xl border border-white/[0.08] bg-[#0d0d15] shadow-2xl shadow-black/60"
                              >
                                {isFetchingBranches ? (
                                  <div className="px-4 py-3 text-sm text-white/40 flex items-center gap-2">
                                    <Loader2 className="h-4 w-4 animate-spin" />Fetching branches...
                                  </div>
                                ) : branches.length > 0 ? (
                                  branches.map((branch) => (
                                    <button
                                      key={branch.name}
                                      type="button"
                                      role="option"
                                      aria-selected={selectedBranch === branch.name}
                                      onClick={() => { setSelectedBranch(branch.name); setShowBranchDropdown(false) }}
                                      className={cn(
                                        'w-full px-4 py-2 text-left flex items-center gap-2 hover:bg-white/[0.05] transition-colors text-sm',
                                        selectedBranch === branch.name && 'bg-indigo-500/10 text-indigo-300'
                                      )}
                                    >
                                      <GitBranch className="h-3.5 w-3.5 text-white/30 shrink-0" />
                                      <span className="text-white/80 truncate">{branch.name}</span>
                                      {branch.protected && (
                                        <span className="ml-auto text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 shrink-0">Protected</span>
                                      )}
                                    </button>
                                  ))
                                ) : hasBranchesError ? (
                                  <div className="px-4 py-3">
                                    <div className="text-sm text-yellow-400 mb-1">Could not fetch branches</div>
                                    <div className="text-xs text-white/40 mb-3">Using default branch. This may happen with private repos or API rate limits.</div>
                                    <div className="flex gap-2">
                                      <button type="button" onClick={() => { setSelectedBranch('main'); setShowBranchDropdown(false) }}
                                        className="text-xs px-3 py-1 rounded-lg bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 transition-colors">Use main</button>
                                      <button type="button" onClick={() => setShowBranchDropdown(false)}
                                        className="text-xs px-3 py-1 rounded-lg bg-white/5 text-white/40 hover:bg-white/10 transition-colors">Dismiss</button>
                                    </div>
                                  </div>
                                ) : (
                                  <div className="px-4 py-3 text-sm text-white/40">No branches available</div>
                                )}
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </div>
                        {isFetchingBranches && <span className="text-[11px] text-white/30">Fetching branches...</span>}
                        {!isFetchingBranches && branches.length > 0 && <span className="text-[11px] text-white/30">{branches.length} available</span>}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <motion.button
                type="submit"
                disabled={!repoUrl.trim() || !parsed}
                whileHover={prefersReducedMotion || !repoUrl.trim() || !parsed ? undefined : { scale: 1.01 }}
                whileTap={prefersReducedMotion ? undefined : { scale: 0.99 }}
                className={cn(
                  'w-full h-[52px] rounded-xl font-medium text-[15px] flex items-center justify-center gap-2',
                  'bg-gradient-to-r from-indigo-600 to-indigo-500 text-white',
                  'transition-all duration-300 shadow-lg shadow-indigo-500/20',
                  'hover:shadow-[0_0_20px_rgba(99,102,241,0.3)] hover:shadow-indigo-500/25',
                  'focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:ring-offset-2 focus:ring-offset-[#07070d]',
                  'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-lg disabled:shadow-indigo-500/20',
                )}
              >
                <GitBranch className="h-4 w-4" />
                Analyze Repository
              </motion.button>
            </form>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}
