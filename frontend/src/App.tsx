import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Landing } from './pages/Landing'
import { Home } from './pages/Home'
import { Dashboard } from './pages/Dashboard'
import { Report } from './pages/Report'
import { Login } from './pages/auth/Login'
import { Register } from './pages/auth/Register'
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
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
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

      {/* Protected routes with Layout */}
      <Route path="/dashboard" element={<ProtectedRoute><Layout><Dashboard /></Layout></ProtectedRoute>} />
      <Route path="/report/:id" element={<ProtectedRoute><Layout><Report /></Layout></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><Layout><Reports /></Layout></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Layout><Settings /></Layout></ProtectedRoute>} />
      <Route path="/analyze" element={<ProtectedRoute><Layout><Home /></Layout></ProtectedRoute>} />

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function Reports() {
  return (
    <div className="text-center py-24">
      <h1 className="text-2xl font-bold mb-2">Reports</h1>
      <p className="text-muted-foreground">View and manage all your analysis reports.</p>
    </div>
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
