import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Shield, Loader2, CheckCircle, XCircle } from 'lucide-react'
import { Card, Button } from '../../components/ui'
import { githubAuthApi } from '../../api/endpoints/github-auth'
import { useAuthStore } from '../../stores/auth-store'

export function GithubCallback() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login, setUser } = useAuthStore()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [error, setError] = useState('')
  
  // Use ref to prevent double processing in React StrictMode
  const hasProcessedRef = useRef(false)

  useEffect(() => {
    // Prevent double processing (React StrictMode)
    if (hasProcessedRef.current) return
    hasProcessedRef.current = true

    const handleCallback = async () => {
      const code = searchParams.get('code')
      const errorParam = searchParams.get('error')

      // Check for OAuth error
      if (errorParam) {
        setStatus('error')
        setError(`GitHub authentication failed: ${errorParam}`)
        return
      }

      if (!code) {
        setStatus('error')
        setError('No authorization code received from GitHub')
        return
      }

      try {
        // Exchange code for token
        const tokenResponse = await githubAuthApi.exchangeCodeForToken(code)

        // Store tokens
        localStorage.setItem('access_token', tokenResponse.access_token)
        if (tokenResponse.refresh_token) {
          localStorage.setItem('refresh_token', tokenResponse.refresh_token)
        }

        // Update auth store
        login(tokenResponse.access_token)
        setUser({
          ...tokenResponse.user,
          is_active: tokenResponse.user.is_active ?? true,
          is_verified: tokenResponse.user.is_verified ?? false,
          role: tokenResponse.user.role ?? 'user',
        })

        // Success!
        setStatus('success')

        // Redirect to dashboard after short delay
        setTimeout(() => {
          navigate('/dashboard')
        }, 1000)
      } catch (err: any) {
        console.error('GitHub OAuth error:', err)
        setStatus('error')
        setError(
          err.response?.data?.detail || 'Failed to complete GitHub authentication. Please try again.'
        )
      }
    }

    handleCallback()
  }, []) // Empty deps - only run once on mount

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md p-8" hover={false}>
        <div className="text-center">
          {/* Logo */}
          <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 mb-6">
            <Shield className="h-12 w-12 text-white" />
          </div>

          {/* Status */}
          {status === 'loading' && (
            <>
              <Loader2 className="h-12 w-12 text-primary animate-spin mx-auto mb-4" />
              <h1 className="text-2xl font-bold mb-2 text-foreground">Completing GitHub Login</h1>
              <p className="text-muted-foreground">Please wait while we authenticate you...</p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle className="h-12 w-12 text-green-400 mx-auto mb-4" />
              <h1 className="text-2xl font-bold mb-2 text-foreground">Login Successful!</h1>
              <p className="text-muted-foreground">Redirecting you to the dashboard...</p>
            </>
          )}

          {status === 'error' && (
            <>
              <XCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
              <h1 className="text-2xl font-bold mb-2 text-foreground">Login Failed</h1>
              <p className="text-muted-foreground mb-6">{error}</p>
              <div className="flex gap-3">
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => navigate('/login')}
                >
                  Back to Login
                </Button>
                <Button
                  variant="primary"
                  className="flex-1"
                  onClick={() => window.location.reload()}
                >
                  Try Again
                </Button>
              </div>
            </>
          )}
        </div>
      </Card>
    </div>
  )
}
