import { lazy, Suspense, useEffect } from 'react'
import { Routes, Route, Navigate, useParams } from 'react-router-dom'

import { CookieConsentBanner } from './components/CookieConsentBanner'
import { Layout } from './components/layout/DashboardLayout'
import { ToastHost } from './components/ui/ToastHost'
import { GithubCallback } from './pages/auth/GithubCallback'
import { GitlabCallback } from './pages/auth/GitlabCallback'
import { IntegrationCallback } from './pages/auth/IntegrationCallback'
import { Login } from './pages/auth/Login'
import { Register } from './pages/auth/Register'
import { Landing } from './pages/Landing'
import { useAuthStore, initAuthSync } from './stores/auth-store'

const Dashboard = lazy(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })))
const Report = lazy(() => import('./pages/Report').then(m => ({ default: m.Report })))
const ScansPage = lazy(() => import('./pages/scans/ScansPage').then(m => ({ default: m.ScansPage })))
const Findings = lazy(() => import('./pages/findings/FindingsPage').then(m => ({ default: m.Findings })))
const RepositoriesPage = lazy(() => import('./pages/repositories/RepositoriesPage').then(m => ({ default: m.RepositoriesPage })))
const RepositoryResultsPage = lazy(() => import('./pages/repositories/RepositoryResultsPage').then(m => ({ default: m.RepositoryResultsPage })))
const BillingPage = lazy(() => import('./pages/billing/BillingPage').then(m => ({ default: m.BillingPage })))
const BillingSuccess = lazy(() => import('./pages/billing/BillingSuccess').then(m => ({ default: m.BillingSuccess })))
const PricingPage = lazy(() => import('./pages/billing/PricingPage').then(m => ({ default: m.PricingPage })))
const ScanPage = lazy(() => import('./pages/ScanPage').then(m => ({ default: m.ScanPage })))
const ScanProgressPage = lazy(() => import('./pages/ScanProgressPage').then(m => ({ default: m.ScanProgressPage })))
const ScanHistoryPage = lazy(() => import('./pages/ScanHistoryPage').then(m => ({ default: m.ScanHistoryPage })))
const AISuggestionsPage = lazy(() => import('./pages/dashboard/AISuggestions').then(m => ({ default: m.AISuggestionsPage })))
const IntegrationsPage = lazy(() => import('./pages/dashboard/Integrations').then(m => ({ default: m.IntegrationsPage })))
const SettingsPage = lazy(() => import('./pages/settings/SettingsPage').then(m => ({ default: m.SettingsPage })))
const AwsPage = lazy(() => import('./pages/aws/AwsPage').then(m => ({ default: m.AwsPage })))
const KubernetesWorkspacePage = lazy(() => import('./pages/kubernetes/KubernetesWorkspacePage').then(m => ({ default: m.KubernetesWorkspacePage })))
const ClusterDetailPage = lazy(() => import('./pages/kubernetes/ClusterDetailPage').then(m => ({ default: m.ClusterDetailPage })))
const DocsHome = lazy(() => import('./pages/docs/DocsPage').then(m => ({ default: m.DocsHome })))
const DocPage = lazy(() => import('./pages/docs/DocsPage').then(m => ({ default: m.DocPage })))

// Protected route component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const isLoading = useAuthStore((state) => state.isLoading)

  // Restore the session on mount regardless of cookie-consent status.
  // The HttpOnly refresh cookie is a first-party, security-essential cookie
  // and must NOT be gated behind optional cookie consent, otherwise a page
  // refresh would log the user out.
  useEffect(() => {
    initAuthSync()
    useAuthStore.getState().checkAuth()
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

// Redirect component for old scan result routes: /scan/result/:id -> /scans/:id
function ScanResultRedirect() {
  const { id } = useParams<{ id: string }>()
  if (!id || id === ':id') {
    return <Navigate to="/scans" replace />
  }
  return <Navigate to={`/scans/${id}`} replace />
}

export default function App() {
  useEffect(() => {
    initAuthSync()
  }, [])

  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
      </div>
    }>
    <ToastHost />
    <CookieConsentBanner />
    <Routes>
      {/* Public routes - no Layout */}
      <Route path="/" element={<Landing />} />
      <Route path="/scan" element={<ScanPage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/auth/github/callback" element={<GithubCallback />} />
      <Route path="/auth/gitlab/callback" element={<GitlabCallback />} />
      <Route path="/integrations/:provider/callback" element={<IntegrationCallback />} />
      <Route path="/pricing" element={<PricingPage />} />

      {/* Documentation - public */}
      <Route path="/docs" element={<DocsHome />} />
      <Route path="/docs/:slug" element={<DocPage />} />

      {/* Redirect old routes */}
      <Route path="/analyze" element={<Navigate to="/scan" replace />} />
      <Route path="/scan/result/:id" element={<ScanResultRedirect />} />

      {/* Protected routes with Layout */}
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <Layout>
            <Dashboard />
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

      {/* Scan progress page — accessible for both auth and guest users */}
      <Route path="/scans/:id" element={
        <Layout>
          <ScanProgressPage />
        </Layout>
      } />

      <Route path="/history" element={
        <ProtectedRoute>
          <Layout>
            <ScanHistoryPage />
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

      <Route path="/repositories/:repositoryId/results" element={
        <ProtectedRoute>
          <Layout>
            <RepositoryResultsPage />
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

      <Route path="/billing/success" element={
        <ProtectedRoute>
          <Layout>
            <BillingSuccess />
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/settings" element={
        <ProtectedRoute>
          <Layout>
            <SettingsPage />
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/ai-suggestions" element={
        <ProtectedRoute>
          <Layout>
            <AISuggestionsPage />
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/integrations" element={
        <ProtectedRoute>
          <Layout>
            <IntegrationsPage />
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/aws" element={
        <ProtectedRoute>
          <Layout>
            <AwsPage />
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/kubernetes" element={
        <ProtectedRoute>
          <Layout>
            <KubernetesWorkspacePage />
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/kubernetes/:connectionId" element={
        <ProtectedRoute>
          <Layout>
            <ClusterDetailPage />
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/reports/:id" element={
        <ProtectedRoute>
          <Layout>
            <Report />
          </Layout>
        </ProtectedRoute>
      } />

      {/* Catch all - redirect to dashboard */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
    </Suspense>
  )
}
