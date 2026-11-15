import { motion, AnimatePresence } from 'framer-motion'
import {
  Shield, LayoutDashboard, FolderGit2, FileSearch, AlertTriangle,
  Brain, CreditCard, Settings, Menu, X, Search,
  Zap, Cloud, ChevronDown, BookOpen, Plug, Container,
} from 'lucide-react'
import { startTransition, useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { useNavigate, useLocation, Link, useSearchParams } from 'react-router-dom'

import { useProductConfig } from '../../hooks/useProductConfig'
import { cn } from '../../lib/utils'
import { useAuthStore, initAuthSync } from '../../stores/auth-store'
import { Button } from '../ui'
import { StatusBadge } from '../ui/StatusBadge'

import { UserAccountMenu, userInitials } from './UserAccountMenu'

interface LayoutProps {
  children: React.ReactNode
}

type NavItem = {
  name: string
  href?: string
  icon: typeof LayoutDashboard
  status?: 'coming_soon' | 'beta' | 'enterprise'
}

const navigationGroups: { label: string; items: NavItem[] }[] = [
  {
    label: 'Security',
    items: [
      { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { name: 'Repositories', href: '/repositories', icon: FolderGit2 },
      { name: 'Scans', href: '/scans', icon: FileSearch },
      { name: 'Security Issues', href: '/findings', icon: AlertTriangle },
      { name: 'AI Recommendations', href: '/ai-suggestions', icon: Brain },
    ],
  },
  {
    label: 'Cloud',
    items: [
      { name: 'AWS', href: '/aws', icon: Cloud },
      { name: 'Kubernetes', href: '/kubernetes', icon: Container },
      { name: 'Azure', icon: Cloud, status: 'coming_soon' },
      { name: 'GCP', icon: Cloud, status: 'coming_soon' },
    ],
  },
  {
    label: 'Platform',
    items: [
      { name: 'Integrations', href: '/integrations', icon: Plug },
      { name: 'Documentation', href: '/docs', icon: BookOpen },
      { name: 'Billing', href: '/billing', icon: CreditCard },
      { name: 'Settings', href: '/settings', icon: Settings },
    ],
  },
]

const navigation = navigationGroups.flatMap((g) => g.items.filter((i) => i.href))

export function Layout({ children }: LayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const productConfig = useProductConfig()
  const navigationGroupsFiltered = useMemo(
    () =>
      navigationGroups.map((group) => ({
        ...group,
        items: group.items.filter(
          (item) => item.href !== '/billing' || productConfig.checkout_enabled
        ),
      })),
    [productConfig.checkout_enabled]
  )
  const [, setSearchParams] = useSearchParams()
  const { user, serverLogout, logoutInProgress, isLoading: authLoading } = useAuthStore()

  useEffect(() => {
    initAuthSync()
    useAuthStore.getState().checkAuth()
  }, [])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [headerMenuOpen, setHeaderMenuOpen] = useState(false)
  const headerMenuRef = useRef<HTMLDivElement>(null)
  const sidebarUserMenuRef = useRef<HTMLDivElement>(null)
  const [dashboardSearch, setDashboardSearch] = useState('')
  const isDashboardRoute = location.pathname === '/dashboard'

  useEffect(() => {
    const nextSearchValue = isDashboardRoute
      ? new URLSearchParams(location.search).get('search') ?? ''
      : ''
    setDashboardSearch((currentValue) => (
      currentValue === nextSearchValue ? currentValue : nextSearchValue
    ))
  }, [isDashboardRoute, location.search])

  const updateDashboardSearch = (value: string) => {
    setDashboardSearch(value)

    if (!isDashboardRoute) {
      return
    }

    const nextParams = new URLSearchParams(location.search)
    const normalizedValue = value.trim()

    if (normalizedValue) {
      nextParams.set('search', normalizedValue)
    } else {
      nextParams.delete('search')
    }

    startTransition(() => {
      setSearchParams(nextParams, { replace: true })
    })
  }

  const handleLogout = useCallback(async () => {
    setUserMenuOpen(false)
    setHeaderMenuOpen(false)
    await serverLogout()
  }, [serverLogout])

  const closeAccountMenus = useCallback(() => {
    setUserMenuOpen(false)
    setHeaderMenuOpen(false)
  }, [])

  const navigateFromMenu = useCallback(
    (path: string) => {
      navigate(path)
      closeAccountMenus()
      setSidebarOpen(false)
    },
    [closeAccountMenus, navigate],
  )

  useEffect(() => {
    if (!userMenuOpen && !headerMenuOpen) {return}
    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node
      if (headerMenuRef.current?.contains(target)) {return}
      if (sidebarUserMenuRef.current?.contains(target)) {return}
      closeAccountMenus()
    }
    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [userMenuOpen, headerMenuOpen, closeAccountMenus])

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Mobile sidebar backdrop */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-72 bg-card/80 backdrop-blur-xl border-r border-white/10",
          "lg:static lg:translate-x-0",
          "transition-transform duration-300 ease-in-out",
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-white/10">
          <Link to="/dashboard" className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-bold text-primary">DevArchAI</span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-1.5 rounded-lg hover:bg-white/5 transition-colors"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5 text-muted-foreground" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-4 overflow-y-auto" aria-label="Main navigation">
          {navigationGroupsFiltered.map((group) => (
            <div key={group.label}>
              <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-white/30">
                {group.label}
              </p>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const Icon = item.icon
                  const isDisabled = !item.href
                  const isActive = !isDisabled && (
                    location.pathname === item.href
                    || (item.href !== '/dashboard' && location.pathname.startsWith(item.href + '/'))
                  )

                  if (isDisabled) {
                    return (
                      <div
                        key={item.name}
                        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-muted-foreground/50 cursor-not-allowed"
                        aria-disabled="true"
                      >
                        <Icon className="h-5 w-5 flex-shrink-0 opacity-50" />
                        <span className="flex-1 text-left">{item.name}</span>
                        {item.status && <StatusBadge status={item.status} />}
                      </div>
                    )
                  }

                  return (
                    <button
                      key={item.name}
                      type="button"
                      onClick={() => {
                        navigate(item.href!)
                        setSidebarOpen(false)
                      }}
                      aria-current={isActive ? 'page' : undefined}
                      className={cn(
                        'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                        isActive
                          ? 'bg-primary/15 text-primary border border-primary/30'
                          : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
                      )}
                    >
                      <Icon className={cn("h-5 w-5 flex-shrink-0", isActive ? 'text-primary' : '')} />
                      <span className="flex-1 text-left">{item.name}</span>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* User profile - sticky bottom */}
        <div className="p-3 border-t border-white/10">
          <div className="relative" ref={sidebarUserMenuRef}>
            <button
              type="button"
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-3 w-full p-2.5 rounded-lg hover:bg-white/5 transition-colors"
              aria-expanded={userMenuOpen}
              aria-haspopup="menu"
            >
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-primary to-indigo-600 flex-shrink-0 text-xs font-semibold text-white">
                {userInitials(user)}
              </div>
              <div className="flex-1 min-w-0 text-left">
                <p className="text-sm font-medium text-foreground truncate">
                  {user?.full_name || user?.username || 'Account'}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {user?.email || ''}
                </p>
              </div>
              <ChevronDown className={cn("h-4 w-4 text-muted-foreground flex-shrink-0 transition-transform", userMenuOpen && "rotate-180")} />
            </button>

            <AnimatePresence>
              {userMenuOpen && (
                <motion.div
                  className="absolute bottom-full left-0 right-0 mb-2 bg-card border border-white/10 rounded-lg shadow-xl overflow-hidden z-50"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                >
                  <UserAccountMenu
                    user={user}
                    productConfig={productConfig}
                    logoutInProgress={logoutInProgress}
                    authLoading={authLoading}
                    onSettings={() => navigateFromMenu('/settings')}
                    onIntegrations={() => navigateFromMenu('/integrations')}
                    onBilling={() => navigateFromMenu('/billing')}
                    onLogout={() => { void handleLogout() }}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top navigation bar */}
        <header className="flex items-center justify-between h-16 px-6 border-b border-white/10 bg-background/80 backdrop-blur-xl">
          <div className="flex items-center gap-4 flex-1">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg hover:bg-white/5 transition-colors"
              aria-label="Open navigation menu"
            >
              <Menu className="h-5 w-5 text-muted-foreground" />
            </button>
            <div className="relative hidden sm:block max-w-md flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="search"
                value={dashboardSearch}
                onChange={(event) => updateDashboardSearch(event.target.value)}
                placeholder={isDashboardRoute ? 'Search recent scans...' : 'Search...'}
                aria-label="Search dashboard"
                className="w-full pl-10 pr-10 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              />
              {dashboardSearch && (
                <button
                  type="button"
                  onClick={() => updateDashboardSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-muted-foreground transition-colors duration-200 hover:bg-white/5 hover:text-foreground"
                  aria-label="Clear search"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="primary"
              size="sm"
              className="hidden sm:inline-flex"
              onClick={() => navigate('/scan')}
            >
              <Zap className="h-3.5 w-3.5 mr-1.5" aria-hidden />
              New Scan
            </Button>
            {productConfig.beta_access_mode ? (
              <StatusBadge
                status="beta"
                label={productConfig.beta_label || 'Beta — Free Access'}
                dot
              />
            ) : (
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/15 border border-primary/30">
                <Zap className="h-3.5 w-3.5 text-primary" aria-hidden />
                <span className="text-xs font-medium text-primary">{user?.plan ? `${user.plan} plan` : 'DevArchAI'}</span>
              </div>
            )}
            <div className="relative" ref={headerMenuRef}>
              <button
                type="button"
                onClick={() => setHeaderMenuOpen((open) => !open)}
                className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-white/5 transition-colors"
                aria-expanded={headerMenuOpen}
                aria-haspopup="menu"
                aria-label="Account menu"
              >
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-primary to-indigo-600 text-xs font-semibold text-white">
                  {userInitials(user)}
                </div>
                <ChevronDown className={cn('h-4 w-4 text-muted-foreground hidden sm:block', headerMenuOpen && 'rotate-180')} />
              </button>
              <AnimatePresence>
                {headerMenuOpen && (
                  <motion.div
                    className="absolute right-0 top-full mt-2 w-72 bg-card border border-white/10 rounded-lg shadow-xl overflow-hidden z-50"
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                  >
                    <UserAccountMenu
                      user={user}
                      productConfig={productConfig}
                      logoutInProgress={logoutInProgress}
                      authLoading={authLoading}
                      onSettings={() => navigateFromMenu('/settings')}
                      onIntegrations={() => navigateFromMenu('/integrations')}
                      onBilling={() => navigateFromMenu('/billing')}
                      onLogout={() => { void handleLogout() }}
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="max-w-7xl mx-auto"
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  )
}
