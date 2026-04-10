import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Shield, Mail, Lock, Eye, EyeOff, Github, Loader2 } from 'lucide-react'
import { Button, Input, Card } from '../../components/ui'
import { useAuthStore } from '../../stores/auth-store'
import { authApi } from '../../api/endpoints/auth'
import { githubAuthApi } from '../../api/endpoints/github-auth'

export function Login() {
  const navigate = useNavigate()
  const { login, setUser } = useAuthStore()
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      // Login and get tokens
      const tokenResponse = await authApi.login(formData)

      // Store tokens
      localStorage.setItem('access_token', tokenResponse.access_token)
      if (formData.rememberMe) {
        localStorage.setItem('refresh_token', tokenResponse.refresh_token)
      }

      // Update auth store with token
      login(tokenResponse.access_token)

      // Fetch user info
      try {
        const userResponse = await authApi.getCurrentUser()
        setUser(userResponse)

        // Navigate to dashboard or intended destination AFTER user is set
        const redirectPath = sessionStorage.getItem('postLoginRedirect')
        const upgradeIntent = sessionStorage.getItem('upgradeIntent')

        if (upgradeIntent === 'true') {
          // User came from upgrade click, redirect to checkout API directly
          const plan = sessionStorage.getItem('upgradePlan') || 'plus'
          const targetRedirect = redirectPath || '/dashboard'
          
          // Clear session storage
          sessionStorage.removeItem('upgradeIntent')
          sessionStorage.removeItem('upgradePlan')
          sessionStorage.removeItem('postLoginRedirect')
          
          // Call checkout API to get payment URL
          try {
            const response = await fetch('/api/v1/billing/checkout', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${tokenResponse.access_token}`,
              },
              body: JSON.stringify({ plan, billing: 'monthly' }),
            })

            const data = await response.json()
            if (data.checkout_url) {
              // Redirect to payment gateway
              const separator = data.checkout_url.includes('?') ? '&' : '?'
              window.location.href = `${data.checkout_url}${separator}redirect=${encodeURIComponent(targetRedirect)}`
              return
            }
          } catch (checkoutError) {
            console.error('Checkout creation failed, falling back to pricing page:', checkoutError)
          }
          
          // Fallback: redirect to pricing page if checkout fails
          navigate(`/pricing?plan=${plan}&redirect=${encodeURIComponent(targetRedirect)}`)
        } else if (redirectPath) {
          // Return to intended destination
          sessionStorage.removeItem('postLoginRedirect')
          navigate(redirectPath)
        } else {
          // Default to dashboard
          navigate('/dashboard')
        }
      } catch (err) {
        // User info fetch failed but login succeeded
        console.warn('Failed to fetch user info', err)

        // Default to dashboard on error
        navigate('/dashboard')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleGithubLogin = async () => {
    try {
      const authUrl = await githubAuthApi.getAuthorizationUrl()
      if (!authUrl) {
        setError('GitHub OAuth is not configured. Please use email/password to login.')
        return
      }
      window.location.href = authUrl
    } catch (error) {
      setError('GitHub OAuth is not configured. Please use email/password to login.')
      console.error('GitHub OAuth error:', error)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary/20 to-indigo-600/20 items-center justify-center p-12">
        <div className="max-w-md text-center">
          <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 mb-6">
            <Shield className="h-16 w-16 text-white" />
          </div>
          <h1 className="text-4xl font-bold mb-4 gradient-text">DevArchAI</h1>
          <p className="text-lg text-muted-foreground mb-8">
            AI-Powered DevOps Production Readiness Engine
          </p>
          <div className="grid grid-cols-3 gap-6">
            {[
              { label: 'Rules', value: '500+' },
              { label: 'Categories', value: '5' },
              { label: 'Avg. Time', value: '< 2min' },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-2xl font-bold gradient-text">{stat.value}</div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right side - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background">
        <Card className="w-full max-w-md p-8" hover={false}>
          <div className="text-center mb-8">
            <div className="lg:hidden inline-flex p-3 rounded-xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 mb-4">
              <Shield className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold mb-2 text-foreground">Welcome back</h1>
            <p className="text-muted-foreground">Sign in to your account to continue</p>
          </div>

          {error && (
            <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                  <Input
                    type="email"
                    placeholder="you@example.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="pl-10"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="pl-10 pr-10"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.rememberMe}
                  onChange={(e) => setFormData({ ...formData, rememberMe: e.target.checked })}
                  className="rounded border-white/20 bg-white/5 text-primary focus:ring-primary"
                />
                <span className="text-muted-foreground">Remember me</span>
              </label>
              <a href="#" className="text-primary hover:underline transition-colors">
                Forgot password?
              </a>
            </div>

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Signing in...
                </div>
              ) : (
                'Sign in'
              )}
            </Button>
          </form>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/10" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-card text-muted-foreground">Or continue with</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Button
              variant="secondary"
              onClick={handleGithubLogin}
              className="w-full"
            >
              <Github className="h-4 w-4 mr-2" />
              GitHub
            </Button>
            <Button
              variant="secondary"
              onClick={() => {}}
              className="w-full"
            >
              <svg className="h-4 w-4 mr-2" viewBox="0 0 24 24">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              Google
            </Button>
          </div>

          <div className="mt-8 text-center text-sm text-muted-foreground">
            Don't have an account?{' '}
            <Link to="/register" className="text-primary hover:underline font-medium transition-colors">
              Sign up
            </Link>
          </div>

          <div className="mt-8 pt-6 border-t border-white/10">
            <p className="text-xs text-center text-muted-foreground">
              By signing in, you agree to our{' '}
              <a href="#" className="text-primary hover:underline">Terms of Service</a>
              {' '}and{' '}
              <a href="#" className="text-primary hover:underline">Privacy Policy</a>
            </p>
          </div>
        </Card>
      </div>
    </div>
  )
}
