import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Shield, Loader2, CheckCircle, XCircle } from 'lucide-react'
import { Card } from '../../components/ui'
import { integrationsApi } from '../../api/endpoints/integrations'
import { useAuthStore } from '../../stores/auth-store'
import { toast } from '../../hooks/useToast'

export function IntegrationCallback() {
  const navigate = useNavigate()
  const { provider } = useParams<{ provider: string }>()
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [error, setError] = useState('')
  const hasProcessedRef = useRef(false)

  const validProvider = provider === 'github' || provider === 'gitlab' ? provider : null

  useEffect(() => {
    if (hasProcessedRef.current) return
    hasProcessedRef.current = true

    const handleCallback = async () => {
      if (!validProvider) {
        setStatus('error')
        setError('Invalid callback provider')
        return
      }

      const code = searchParams.get('code')
      const errorParam = searchParams.get('error')

      if (errorParam) {
        setStatus('error')
        setError(`Authorization failed: ${errorParam}`)
        return
      }

      if (!code) {
        setStatus('error')
        setError('No authorization code received')
        return
      }

      try {
        // The page was fully reloaded by the OAuth redirect, so the in-memory
        // access token is gone. Restore the session from the refresh cookie
        // before exchanging the code.
        const refreshed = await useAuthStore.getState().refreshSession()
        if (!refreshed) {
          setStatus('error')
          setError('Session expired. Please sign in again.')
          setTimeout(() => navigate('/login', { replace: true }), 1500)
          return
        }

        const state = searchParams.get('state') || undefined
        await integrationsApi.exchangeOAuthCode(validProvider, code, state)
        setStatus('success')
        toast.success(`${validProvider === 'github' ? 'GitHub' : 'GitLab'} connected`)
        setTimeout(() => {
          navigate('/integrations', { replace: true })
        }, 1000)
      } catch (err: any) {
        console.error('Integration OAuth error:', err)
        setStatus('error')
        setError(err.response?.data?.detail || 'Failed to connect. Please try again.')
      }
    }

    handleCallback()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const providerName = validProvider === 'github' ? 'GitHub' : validProvider === 'gitlab' ? 'GitLab' : ''

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md p-8" hover={false}>
        <div className="text-center">
          <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 mb-6">
            <Shield className="h-12 w-12 text-white" />
          </div>

          {status === 'loading' && (
            <>
              <Loader2 className="h-12 w-12 text-primary animate-spin mx-auto mb-4" />
              <h1 className="text-2xl font-bold mb-2 text-foreground">Connecting {providerName}</h1>
              <p className="text-muted-foreground">Please wait while we link your account...</p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle className="h-12 w-12 text-green-400 mx-auto mb-4" />
              <h1 className="text-2xl font-bold mb-2 text-foreground">Connected!</h1>
              <p className="text-muted-foreground">Returning to integrations...</p>
            </>
          )}

          {status === 'error' && (
            <>
              <XCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
              <h1 className="text-2xl font-bold mb-2 text-foreground">Connection Failed</h1>
              <p className="text-muted-foreground mb-6">{error}</p>
              <button
                onClick={() => navigate('/integrations')}
                className="px-5 py-2.5 rounded-xl bg-primary text-white text-sm font-semibold hover:opacity-90 transition-opacity"
              >
                Back to Integrations
              </button>
            </>
          )}
        </div>
      </Card>
    </div>
  )
}
