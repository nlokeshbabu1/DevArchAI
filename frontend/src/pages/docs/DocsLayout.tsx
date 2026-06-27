import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../lib/utils'
import {
  Shield, Menu, X, Search, ChevronRight, ChevronDown,
  BookOpen, ExternalLink, Github, Gitlab, Cloud, Server,
  AlertTriangle, Brain, FileText, HelpCircle, Bug, Zap,
  Container, FileCode, FolderGit2, Rocket, ArrowLeft, ArrowRight,
} from 'lucide-react'
import {
  DOC_SECTIONS,
  searchDocs,
  type DocPage,
  type SearchResult,
  getAllPages,
  getPrevNext,
} from './docs-data'

const ICON_MAP: Record<string, React.ElementType> = {
  Rocket, FolderGit2, Cloud, Server, Github, Gitlab,
  Container, FileCode, Zap, Brain, AlertTriangle, FileText,
  BookOpen, HelpCircle, Bug,
}

interface DocsLayoutProps {
  children: React.ReactNode
  page: DocPage | null
}

export function DocsLayout({ children, page }: DocsLayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [expandedSections, setExpandedSections] = useState<string[]>(() => {
    if (page) return [page.section]
    return DOC_SECTIONS.map((s) => s.label)
  })
  const searchRef = useRef<HTMLInputElement>(null)
  const searchContainerRef = useRef<HTMLDivElement>(null)
  const [activeHeading, setActiveHeading] = useState('')

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false)
    setSearchOpen(false)
  }, [location.pathname])

  // Focus search when opened
  useEffect(() => {
    if (searchOpen && searchRef.current) searchRef.current.focus()
  }, [searchOpen])

  // Close search on escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSearchOpen(false)
        setSearchQuery('')
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setSearchOpen((o) => !o)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // Close search on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setSearchOpen(false)
        setSearchQuery('')
      }
    }
    if (searchOpen) {
      document.addEventListener('mousedown', handler)
      return () => document.removeEventListener('mousedown', handler)
    }
  }, [searchOpen])

  // Search handler
  const handleSearch = (query: string) => {
    setSearchQuery(query)
    if (query.trim().length < 2) {
      setSearchResults([])
      return
    }
    // Deduplicate
    const raw = searchDocs(query)
    const seen = new Set<string>()
    setSearchResults(raw.filter((r) => {
      const key = `${r.slug}-${r.match}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    }))
  }

  // Track scroll position for active TOC heading
  useEffect(() => {
    const handleScroll = () => {
      if (!page) return
      const headings = page.headings.map((h) => document.getElementById(h.id)).filter(Boolean)
      let current = ''
      for (const el of headings) {
        if (!el) continue
        const rect = el.getBoundingClientRect()
        if (rect.top <= 120) current = el.id
      }
      setActiveHeading(current)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [page])

  const allPages = useMemo(() => getAllPages(), [])
  const prevNext = page ? getPrevNext(page.slug) : { prev: null, next: null }

  const toggleSection = (label: string) => {
    setExpandedSections((prev) =>
      prev.includes(label) ? prev.filter((s) => s !== label) : [...prev, label]
    )
  }

  const isActive = (slug: string) => location.pathname === `/docs/${slug}`

  return (
    <div className="min-h-screen bg-background">
      {/* ─── Global Search Overlay ─── */}
      <AnimatePresence>
        {searchOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />
        )}
      </AnimatePresence>

      {/* ─── Search Modal ─── */}
      <AnimatePresence>
        {searchOpen && (
          <motion.div
            ref={searchContainerRef}
            initial={{ opacity: 0, y: -20, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.96 }}
            className="fixed top-[15%] left-1/2 -translate-x-1/2 z-50 w-full max-w-2xl mx-4"
          >
            <div className="bg-card border border-white/10 rounded-2xl shadow-2xl shadow-black/40 overflow-hidden">
              <div className="flex items-center gap-3 px-5 py-4 border-b border-white/10">
                <Search className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                <input
                  ref={searchRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Search documentation... (e.g. 'connect aws', 'terraform', 'oauth')"
                  className="flex-1 bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none text-sm"
                />
                <kbd className="hidden sm:inline-flex px-2 py-0.5 text-[10px] font-mono text-muted-foreground bg-white/5 rounded border border-white/10">
                  ESC
                </kbd>
              </div>
              {searchResults.length > 0 && (
                <div className="max-h-80 overflow-y-auto p-2 space-y-0.5">
                  {searchResults.slice(0, 20).map((r, i) => (
                    <button
                      key={`${r.slug}-${r.match}-${i}`}
                      onClick={() => { navigate(`/docs/${r.slug}`); setSearchOpen(false); setSearchQuery('') }}
                      className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/5 transition-colors text-left"
                    >
                      <div className="p-1.5 rounded-lg bg-primary/10">
                        <BookOpen className="h-4 w-4 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">{r.title}</p>
                        <p className="text-xs text-muted-foreground truncate">{r.match}</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
              {searchQuery.length >= 2 && searchResults.length === 0 && (
                <div className="p-8 text-center">
                  <p className="text-sm text-muted-foreground">No results for &quot;{searchQuery}&quot;</p>
                  <p className="text-xs text-muted-foreground/60 mt-1">Try different keywords</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Top Navigation Bar ─── */}
      <header className="sticky top-0 z-40 bg-background/80 backdrop-blur-xl border-b border-white/10">
        <div className="flex items-center justify-between h-14 px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen((o) => !o)}
              className="lg:hidden p-2 rounded-lg hover:bg-white/5 transition-colors"
              aria-label="Toggle sidebar"
            >
              {sidebarOpen ? <X className="h-5 w-5 text-muted-foreground" /> : <Menu className="h-5 w-5 text-muted-foreground" />}
            </button>
            <Link to="/docs" className="flex items-center gap-2.5">
              <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-indigo-600">
                <Shield className="h-4 w-4 text-white" />
              </div>
              <span className="text-sm font-bold gradient-text">DevArchAI</span>
              <span className="hidden sm:inline text-xs text-muted-foreground/60 font-mono bg-white/5 px-2 py-0.5 rounded border border-white/10">Docs</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSearchOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground bg-white/5 rounded-lg border border-white/10 hover:bg-white/10 transition-colors"
            >
              <Search className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Search docs...</span>
              <span className="hidden sm:inline text-[10px] text-muted-foreground/60">⌘K</span>
            </button>
            <Link
              to="/"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5"
            >
              Back to site
            </Link>
          </div>
        </div>
      </header>

      {/* ─── Body ─── */}
      <div className="flex">
        {/* Mobile backdrop */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-30 lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
          )}
        </AnimatePresence>

        {/* ─── Left Sidebar ─── */}
        <motion.aside
          className={cn(
            'fixed lg:sticky top-14 left-0 z-30 h-[calc(100vh-3.5rem)] w-72 bg-card/90 backdrop-blur-xl border-r border-white/10 overflow-y-auto',
            'lg:translate-x-0 transition-transform duration-300',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
          )}
        >
          <nav className="p-4 space-y-1">
            {DOC_SECTIONS.map((section) => {
              const isExpanded = expandedSections.includes(section.label)
              return (
                <div key={section.label}>
                  <button
                    onClick={() => toggleSection(section.label)}
                    className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors rounded-lg"
                  >
                    {section.label}
                    {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                  </button>
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                      >
                        {section.pages.map((p) => {
                          const active = isActive(p.slug)
                          const Icon = ICON_MAP[p.icon] || BookOpen
                          return (
                            <Link
                              key={p.slug}
                              to={`/docs/${p.slug}`}
                              className={cn(
                                'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150',
                                active
                                  ? 'bg-primary/15 text-primary border border-primary/30'
                                  : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
                              )}
                            >
                              <Icon className={cn('h-4 w-4 flex-shrink-0', active ? 'text-primary' : '')} />
                              <span className="truncate">{p.title}</span>
                            </Link>
                          )
                        })}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )
            })}
          </nav>

          {/* External links */}
          <div className="p-4 border-t border-white/10 mt-2 space-y-1">
            <a
              href="https://github.com/your-org/devarchai"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
            >
              <Github className="h-4 w-4" />
              GitHub
              <ExternalLink className="h-3 w-3 ml-auto" />
            </a>
            <Link
              to="/"
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
            >
              <Shield className="h-4 w-4" />
              DevArchAI Home
            </Link>
          </div>
        </motion.aside>

        {/* ─── Main Content ─── */}
        <main className="flex-1 min-w-0 px-4 lg:px-8 py-8 lg:py-12">
          <div className="max-w-3xl mx-auto">
            {page && (
              <div className="mb-8">
                <Link
                  to="/docs"
                  className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mb-4"
                >
                  <ArrowLeft className="h-3 w-3" /> Documentation
                </Link>
                <h1 className="text-3xl lg:text-4xl font-bold text-foreground tracking-tight">{page.title}</h1>
                <p className="text-base text-muted-foreground mt-2">{page.subtitle}</p>
              </div>
            )}
            <div className="prose prose-invert max-w-none">
              {children}
            </div>

            {/* Prev / Next */}
            <nav className="mt-16 pt-8 border-t border-white/10 flex items-center justify-between">
              {prevNext.prev ? (
                <Link
                  to={`/docs/${prevNext.prev.slug}`}
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors group"
                >
                  <ArrowLeft className="h-4 w-4 group-hover:-translate-x-1 transition-transform" />
                  <div className="text-left">
                    <div className="text-[10px] text-muted-foreground/60 uppercase tracking-wider">Previous</div>
                    <div className="font-medium">{prevNext.prev.title}</div>
                  </div>
                </Link>
              ) : <div />}
              {prevNext.next ? (
                <Link
                  to={`/docs/${prevNext.next.slug}`}
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors group text-right"
                >
                  <div>
                    <div className="text-[10px] text-muted-foreground/60 uppercase tracking-wider">Next</div>
                    <div className="font-medium">{prevNext.next.title}</div>
                  </div>
                  <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                </Link>
              ) : <div />}
            </nav>
          </div>
        </main>

        {/* ─── Right TOC ─── */}
        {page && page.headings.length > 0 && (
          <aside className="hidden xl:block w-56 flex-shrink-0 sticky top-14 h-[calc(100vh-3.5rem)] overflow-y-auto py-8 pr-4">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-3 px-3">
              On this page
            </div>
            <nav className="space-y-0.5">
              {page.headings.map((h) => (
                <a
                  key={h.id}
                  href={`#${h.id}`}
                  onClick={(e) => {
                    e.preventDefault()
                    const el = document.getElementById(h.id)
                    if (el) {
                      window.scrollTo({ top: el.offsetTop - 100, behavior: 'smooth' })
                    }
                  }}
                  className={cn(
                    'block text-xs px-3 py-1.5 rounded-lg transition-colors',
                    h.level === 3 ? 'pl-6' : '',
                    activeHeading === h.id
                      ? 'text-primary bg-primary/10'
                      : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
                  )}
                >
                  {h.label}
                </a>
              ))}
            </nav>
          </aside>
        )}
      </div>
    </div>
  )
}
