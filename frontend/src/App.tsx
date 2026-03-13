import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/layout/DashboardLayout'
import { Landing } from './pages/Landing'
import { Home } from './pages/Home'
import { Dashboard } from './pages/Dashboard'
import { Report } from './pages/Report'
import { Login } from './pages/auth/Login'
import { Register } from './pages/auth/Register'
import { GithubCallback } from './pages/auth/GithubCallback'
import { ScansPage } from './pages/scans/ScansPage'
import { Findings } from './pages/findings/FindingsPage'
import { RepositoriesPage } from './pages/repositories/RepositoriesPage'
import { BillingPage } from './pages/billing/BillingPage'
import { AISuggestionsPage } from './pages/dashboard/AISuggestions'
import { IntegrationsPage } from './pages/dashboard/Integrations'
import { useAuthStore } from './stores/auth-store'
import { useEffect } from 'react'

// Protected route component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const isLoading = useAuthStore((state) => state.isLoading)

  // Check auth on mount
  useEffect(() => {
    useAuthStore.getState().checkAuth()
  }, [])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-8 h-8 bg-primary rounded-full animate-pulse" />
          </div>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

export default function App() {
  // Check auth on app mount
  useEffect(() => {
    useAuthStore.getState().checkAuth()
  }, [])

  return (
    <Routes>
      {/* Public routes - no Layout */}
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/auth/github/callback" element={<GithubCallback />} />

      {/* Protected routes with Layout */}
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <Layout>
            <Dashboard />
          </Layout>
        </ProtectedRoute>
      } />
      
      <Route path="/report/:id" element={
        <ProtectedRoute>
          <Layout>
            <Report />
          </Layout>
        </ProtectedRoute>
      } />
      
      <Route path="/analyze" element={
        <ProtectedRoute>
          <Layout>
            <Home />
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/scans" element={
        <ProtectedRoute>
          <Layout>
            <ScansPage />
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/findings" element={
        <ProtectedRoute>
          <Layout>
            <Findings />
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/repositories" element={
        <ProtectedRoute>
          <Layout>
            <RepositoriesPage />
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/billing" element={
        <ProtectedRoute>
          <Layout>
            <BillingPage />
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/settings" element={
        <ProtectedRoute>
          <Layout>
            <Settings />
          </Layout>
        </ProtectedRoute>
      } />

      {/* Catch all - redirect to dashboard */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

function Settings() {
  return (
    <div className="text-center py-24">
      <h1 className="text-2xl font-bold mb-2">Settings</h1>
      <p className="text-muted-foreground">Configure your analysis preferences and integrations.</p>
    </div>
  )
}
