import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Shield, Loader2, CheckCircle, XCircle } from 'lucide-react'
import { Card, Button } from '../../components/ui'
import { useAuthStore } from '../../stores/auth-store'
import { gitlabAuthApi } from '../../api/endpoints/gitlab-auth'

export function GitlabCallback() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const { login, setUser } = useAuthStore()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [error, setError] = useState('')
  const processedRef = useRef(false)

  useEffect(() => {
    if (processedRef.current) return
    processedRef.current = true

    const errorParam = searchParams.get('error')
    const code = searchParams.get('code')
    const state = searchParams.get('state')

    if (errorParam) {
      setStatus('error')
      setError(`GitLab authentication failed: ${errorParam}`)
      return
    }

    if (!code) {
      setStatus('error')
      setError('No authorization code received from GitLab')
      return
    }

    gitlabAuthApi.exchangeCodeForToken(code, state || undefined)
      .then((response) => {
        login(response.access_token)
        if (response.user) {
          setUser({
            id: response.user.id,
            email: response.user.email,
            username: response.user.username,
            avatar_url: response.user.avatar_url,
            provider: 'gitlab',
            is_active: response.user.is_active ?? true,
            is_verified: response.user.is_verified ?? true,
            role: response.user.role ?? 'user',
            current_org_id: response.user.current_org_id,
            has_github: response.user.has_github ?? false,
            has_gitlab: response.user.has_gitlab ?? false,
          })
        }
        queryClient.clear()
        setStatus('success')
        setTimeout(() => navigate('/dashboard'), 1000)
      })
      .catch((err: unknown) => {
        setStatus('error')
        const detail = err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
        setError(detail || 'Failed to complete GitLab authentication. Please try again.')
      })
  }, [login, navigate, queryClient, searchParams, setUser])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md p-8" hover={false}>
        <div className="text-center">
          <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 mb-6">
            <Shield className="h-12 w-12 text-white" />
          </div>

          {status === 'loading' && (
            <>
              <Loader2 className="h-12 w-12 text-primary animate-spin mx-auto mb-4" aria-hidden />
              <h1 className="text-2xl font-bold mb-2 text-foreground">Completing GitLab Login</h1>
              <p className="text-muted-foreground">Please wait while we authenticate you...</p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle className="h-12 w-12 text-green-400 mx-auto mb-4" aria-hidden />
              <h1 className="text-2xl font-bold mb-2 text-foreground">Login Successful!</h1>
              <p className="text-muted-foreground">Redirecting you to the dashboard...</p>
            </>
          )}

          {status === 'error' && (
            <>
              <XCircle className="h-12 w-12 text-red-400 mx-auto mb-4" aria-hidden />
              <h1 className="text-2xl font-bold mb-2 text-foreground">Login Failed</h1>
              <p className="text-muted-foreground mb-6" role="alert">{error}</p>
              <div className="flex gap-3">
                <Button variant="secondary" className="flex-1" onClick={() => navigate('/login')}>
                  Back to Login
                </Button>
                <Button variant="primary" className="flex-1" onClick={() => window.location.reload()}>
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
