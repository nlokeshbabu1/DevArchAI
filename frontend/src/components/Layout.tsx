import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { cn } from '../lib/utils'
import {
  LayoutDashboard,
  ScanSearch,
  FileText,
  Settings,
  Menu,
  X,
  Shield,
  ChevronLeft,
  ChevronRight,
  LogOut,
  User
} from 'lucide-react'
import { useAuthStore } from '../stores/auth-store'

interface LayoutProps {
  children: React.ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Analyze', href: '/analyze', icon: ScanSearch },
  { name: 'Reports', href: '/reports', icon: FileText },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { logout, user } = useAuthStore()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/')  // Redirect to main landing page
  }

  return (
    <div className="min-h-screen bg-background flex">
      {/* Mobile sidebar backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden backdrop-blur-sm"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={cn(
        'fixed lg:static inset-y-0 left-0 z-50',
        'bg-card/80 backdrop-blur-xl border-r border-white/10',
        'transition-all duration-300 ease-in-out',
        'flex flex-col',
        sidebarOpen ? 'w-64' : 'w-20',
        mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      )}>
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-white/10">
          <Link to="/dashboard" className="flex items-center gap-3 overflow-hidden">
            <div className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 border border-white/20">
              <Shield className="h-6 w-6 text-white" />
            </div>
            <span className={cn(
              'text-xl font-bold text-primary whitespace-nowrap transition-opacity duration-300',
              sidebarOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'
            )}>
              DevArchAI
            </span>
          </Link>
          <button
            onClick={() => setMobileOpen(false)}
            className="lg:hidden p-2 hover:bg-white/5 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-muted-foreground" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            const Icon = item.icon

            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  'flex items-center gap-3 px-3 py-3 rounded-xl',
                  'text-muted-foreground hover:text-foreground hover:bg-white/5',
                  'transition-all duration-200',
                  'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-card',
                  isActive && 'bg-primary/15 text-primary border border-primary/30 shadow-lg shadow-primary/20',
                  !sidebarOpen && 'justify-center'
                )}
              >
                <Icon className="h-5 w-5 flex-shrink-0" />
                <span className={cn(
                  'whitespace-nowrap transition-opacity duration-300',
                  sidebarOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'
                )}>
                  {item.name}
                </span>
                {isActive && sidebarOpen && (
                  <div className="ml-auto">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary shadow-lg shadow-primary/50" />
                  </div>
                )}
              </Link>
            )
          })}
        </nav>

        {/* Bottom section - User info & Logout / Login */}
        <div className="p-3 border-t border-white/10">
          {user ? (
            <div className={cn(
              'bg-gradient-to-br from-primary/15 to-indigo-600/15 rounded-xl p-3 border border-primary/30 backdrop-blur-sm',
              'transition-all duration-300',
              !sidebarOpen && 'p-2'
            )}>
              <div className={cn(
                'flex items-center gap-3',
                !sidebarOpen && 'justify-center'
              )}>
                <div className="p-2 bg-primary/20 rounded-lg flex-shrink-0">
                  <User className="h-5 w-5 text-primary" />
                </div>
                <div className={cn(
                  'overflow-hidden transition-all duration-300',
                  !sidebarOpen && 'w-0 opacity-0'
                )}>
                  <p className="text-sm font-medium text-foreground whitespace-nowrap truncate">
                    {user.username || user.email}
                  </p>
                  <p className="text-xs text-muted-foreground whitespace-nowrap capitalize">
                    {user.role || 'User'}
                  </p>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className={cn(
                  'w-full flex items-center justify-center gap-2 btn btn-secondary btn-sm mt-3',
                  !sidebarOpen && 'px-2'
                )}
              >
                <LogOut className="h-4 w-4" />
                <span className={cn(!sidebarOpen && 'sr-only')}>Logout</span>
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className={cn(
                'flex items-center gap-3 px-3 py-3 rounded-xl',
                'bg-gradient-to-br from-primary/15 to-indigo-600/15 border border-primary/30 backdrop-blur-sm',
                'text-muted-foreground hover:text-foreground hover:bg-white/5',
                'transition-all duration-200',
                !sidebarOpen && 'justify-center'
              )}
            >
              <div className="p-2 bg-primary/20 rounded-lg flex-shrink-0">
                <User className="h-5 w-5 text-primary" />
              </div>
              <span className={cn(
                'whitespace-nowrap transition-opacity duration-300',
                !sidebarOpen && 'opacity-0 w-0 overflow-hidden'
              )}>
                Login
              </span>
            </Link>
          )}
        </div>
      </aside>

      {/* Main content wrapper */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top navbar */}
        <header className="sticky top-0 z-30 h-16 bg-background/80 backdrop-blur-xl border-b border-white/10">
          <div className="flex items-center justify-between h-full px-4 lg:px-6">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setMobileOpen(true)}
                className="lg:hidden p-2 hover:bg-white/5 rounded-lg transition-colors"
              >
                <Menu className="h-5 w-5 text-muted-foreground" />
              </button>
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="hidden lg:flex p-2 hover:bg-white/5 rounded-lg transition-colors"
              >
                {sidebarOpen ? (
                  <ChevronLeft className="h-5 w-5 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-5 w-5 text-muted-foreground" />
                )}
              </button>
            </div>

            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-green-500/10 rounded-full border border-green-500/30">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-sm text-green-400">System Operational</span>
              </div>
              {user && (
                <div className="relative">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center gap-2 p-2 hover:bg-white/5 rounded-lg transition-colors"
                  >
                    <div className="w-8 h-8 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
                      <User className="h-4 w-4 text-primary" />
                    </div>
                  </button>
                  {showUserMenu && (
                    <div className="absolute right-0 mt-2 w-48 rounded-xl bg-card border border-white/10 shadow-lg shadow-black/50 z-50">
                      <div className="p-3 border-b border-white/10">
                        <p className="text-sm font-medium text-foreground">{user.username || user.email}</p>
                        <p className="text-xs text-muted-foreground">{user.email}</p>
                      </div>
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 rounded-lg transition-colors"
                      >
                        <LogOut className="h-4 w-4" />
                        Sign out
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page content - Centered with proper spacing */}
        <main className="flex-1 p-4 lg:p-6 overflow-auto">
          <div className="w-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
