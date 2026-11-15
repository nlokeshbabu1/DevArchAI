import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { getApiV1BaseUrl } from '../../lib/api-base-url'
import { useAuthStore } from '../../stores/auth-store'

export function CliAuthorize() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { isAuthenticated, token, checkAuth, sessionChecked } = useAuthStore()
  const [error, setError] = useState('')
  const [status, setStatus] = useState('Checking your session…')
  const approvalStarted = useRef(false)

  const sessionId = searchParams.get('session_id') || ''
  const state = searchParams.get('state') || ''

  useEffect(() => {
    void checkAuth()
  }, [checkAuth])

  useEffect(() => {
    if (!sessionId || !state) {
      setError('Missing CLI authorization parameters.')
      return
    }
    if (!sessionChecked) {
      setStatus('Checking your session…')
      return
    }
    if (!isAuthenticated) {
      sessionStorage.setItem('postLoginRedirect', `/cli/authorize?session_id=${sessionId}&state=${encodeURIComponent(state)}`)
      navigate('/login', { replace: true })
      return
    }
    if (!token || approvalStarted.current) {
      return
    }
    approvalStarted.current = true

    const approve = async () => {
      setStatus('Authorizing DevArchAI CLI…')
      try {
        const resp = await fetch(`${getApiV1BaseUrl()}/auth/cli/approve`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ session_id: sessionId, state }),
        })
        if (!resp.ok) {
          const body = await resp.json().catch(() => ({}))
          const message = body?.detail || 'Authorization failed.'
          setError(typeof message === 'string' ? message : 'Authorization failed.')
          return
        }
        const data = await resp.json()
        setStatus('Redirecting back to the CLI…')
        window.location.href = data.redirect_uri
      } catch {
        setError('Could not reach the DevArchAI API. Try again from the CLI.')
      }
    }

    void approve()
  }, [token, isAuthenticated, sessionChecked, navigate, sessionId, state])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground p-6">
      <div className="max-w-md w-full rounded-xl border border-white/10 bg-card/60 p-8 shadow-xl text-center space-y-4">
        <h1 className="text-xl font-semibold">DevArchAI CLI</h1>
        {error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : (
          <p className="text-sm text-muted-foreground">{status}</p>
        )}
      </div>
    </div>
  )
}