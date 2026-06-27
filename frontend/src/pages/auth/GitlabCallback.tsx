import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Shield, Loader2, AlertCircle } from 'lucide-react'
import { useAuthStore } from '../../stores/auth-store'
import { gitlabAuthApi } from '../../api/endpoints/gitlab-auth'

export function GitlabCallback() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const { login, setUser } = useAuthStore()
  const processedRef = useRef(false)

  useEffect(() => {
    if (processedRef.current) return
    processedRef.current = true

    const code = searchParams.get('code')
    const state = searchParams.get('state')
    if (!code) {
      navigate('/login?error=No authorization code received')
      return
    }

    gitlabAuthApi.exchangeCodeForToken(code, state || undefined)
      .then((response) => {
        if (response.refresh_token) {
          localStorage.setItem('refresh_token', response.refresh_token)
        }
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
        navigate('/dashboard')
      })
      .catch((error) => {
        console.error('GitLab OAuth callback error:', error)
        navigate('/login?error=GitLab authentication failed')
      })
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-4">
        <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-2xl shadow-primary/40">
          <Shield className="h-12 w-12 text-white" />
        </div>
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="h-6 w-6 text-primary animate-spin" />
          <p className="text-lg text-muted-foreground">Completing GitLab authentication...</p>
        </div>
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground/60">
          <AlertCircle className="h-4 w-4" />
          <span>You will be redirected shortly</span>
        </div>
      </div>
    </div>
  )
}
