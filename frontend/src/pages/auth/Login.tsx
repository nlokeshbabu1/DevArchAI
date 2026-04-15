import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Shield, Mail, Lock, Eye, EyeOff, Github, Loader2, 
  CheckCircle, AlertCircle, ArrowRight, Sparkles,
  Zap, Globe, Users, Star
} from 'lucide-react'
import { Button, Input, Card } from '../../components/ui'
import { useAuthStore } from '../../stores/auth-store'
import { authApi } from '../../api/endpoints/auth'
import { githubAuthApi } from '../../api/endpoints/github-auth'

// Trust signals data
const trustSignals = [
  { icon: Shield, text: 'Enterprise-grade security', subtext: 'SOC 2 Type II certified' },
  { icon: Zap, text: 'Lightning-fast scans', subtext: 'Results in under 2 minutes' },
  { icon: Globe, text: 'Trusted by 10,000+ teams', subtext: 'Worldwide deployment' },
]

// Benefits data (replacing stats)
const benefits = [
  { icon: Shield, title: '500+ Security Rules', description: 'Comprehensive IaC scanning' },
  { icon: Sparkles, title: 'AI-Powered Fixes', description: 'Auto-generate PRs with fixes' },
  { icon: Users, title: 'Team Collaboration', description: 'Multi-tenant organization support' },
]

export function Login() {
  const navigate = useNavigate()
  const { login, setUser } = useAuthStore()
  
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({})
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false,
  })

  // Clear error when user starts typing
  useEffect(() => {
    if (error) setError('')
  }, [formData.email, formData.password])

  const validateForm = (): boolean => {
    const errors: { email?: string; password?: string } = {}

    if (!formData.email) {
      errors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Please enter a valid email address'
    }

    if (!formData.password) {
      errors.password = 'Password is required'
    } else if (formData.password.length < 8) {
      errors.password = 'Password must be at least 8 characters'
    }

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setFieldErrors({})

    // Validate form
    if (!validateForm()) {
      return
    }

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

      // Show success message
      setSuccess('Login successful! Redirecting...')

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
      const errorMessage = err.response?.data?.detail || 'Login failed. Please check your credentials.'
      setError(errorMessage)
      
      // Add field-specific errors for better UX
      if (errorMessage.toLowerCase().includes('email')) {
        setFieldErrors({ email: 'Email not found' })
      } else if (errorMessage.toLowerCase().includes('password')) {
        setFieldErrors({ password: 'Incorrect password' })
      }
    } finally {
      // Don't set isLoading to false immediately on success (redirecting)
      if (!success) {
        setTimeout(() => setIsLoading(false), 500)
      }
    }
  }

  const handleGithubLogin = async () => {
    setError('')
    setIsLoading(true)
    
    try {
      const authUrl = await githubAuthApi.getAuthorizationUrl()
      if (!authUrl) {
        setError('GitHub OAuth is not configured. Please use email/password to login.')
        setIsLoading(false)
        return
      }
      window.location.href = authUrl
    } catch (error) {
      setError('GitHub OAuth is not configured. Please use email/password to login.')
      console.error('GitHub OAuth error:', error)
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      handleSubmit(e)
    }
  }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* Left side - Branding & Benefits */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary/10 via-indigo-600/10 to-purple-600/10 items-center justify-center p-12 relative overflow-hidden">
        {/* Background pattern */}
        <div className="absolute inset-0 opacity-5">
          <div className="absolute inset-0" style={{
            backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
            backgroundSize: '40px 40px'
          }} />
        </div>

        <motion.div 
          className="max-w-lg relative z-10"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          {/* Logo & Title */}
          <div className="mb-12">
            <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-2xl shadow-primary/40 mb-6">
              <Shield className="h-14 w-14 text-white" />
            </div>
            <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-white via-white to-white/80 bg-clip-text text-transparent">
              DevArchAI
            </h1>
            <p className="text-xl text-white/70 leading-relaxed">
              AI-Powered DevOps Production Readiness Engine
            </p>
          </div>

          {/* Benefits */}
          <div className="space-y-6 mb-12">
            {benefits.map((benefit, index) => (
              <motion.div
                key={benefit.title}
                className="flex items-start gap-4 p-4 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 + index * 0.1 }}
              >
                <div className="p-2 rounded-lg bg-primary/20 flex-shrink-0">
                  <benefit.icon className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1">{benefit.title}</h3>
                  <p className="text-sm text-white/60">{benefit.description}</p>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Trust Signals */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-white/50 mb-4">
              <Star className="h-4 w-4 text-yellow-400" />
              <span>Trusted by leading engineering teams</span>
            </div>
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: 'Security Rules', value: '500+' },
                { label: 'AI Models', value: '4' },
                { label: 'Avg. Scan Time', value: '< 2min' },
              ].map((stat) => (
                <div key={stat.label} className="text-center p-3 rounded-lg bg-white/5">
                  <div className="text-2xl font-bold text-white mb-1">{stat.value}</div>
                  <div className="text-xs text-white/50">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Right side - Login Form */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 bg-background relative">
        {/* Mobile logo */}
        <div className="lg:hidden absolute top-6 left-6 flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30">
            <Shield className="h-6 w-6 text-white" />
          </div>
          <span className="text-xl font-bold gradient-text">DevArchAI</span>
        </div>

        <motion.div 
          className="w-full max-w-md"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Card className="p-8 shadow-2xl border-0" hover={false}>
            {/* Header */}
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold mb-2 text-foreground">Welcome back</h1>
              <p className="text-muted-foreground">Sign in to continue securing your infrastructure</p>
            </div>

            {/* Success Message */}
            <AnimatePresence>
              {success && (
                <motion.div
                  initial={{ opacity: 0, y: -10, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: 'auto' }}
                  exit={{ opacity: 0, y: -10, height: 0 }}
                  className="mb-6 p-4 rounded-lg bg-green-500/10 border border-green-500/30 flex items-center gap-3"
                >
                  <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0" />
                  <span className="text-sm text-green-400">{success}</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Error Message */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: 'auto' }}
                  exit={{ opacity: 0, y: -10, height: 0 }}
                  className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-start gap-3"
                  role="alert"
                  aria-live="polite"
                >
                  <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-red-400">{error}</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Login Form */}
            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              {/* Email Field */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-foreground mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground pointer-events-none" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@company.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    onKeyDown={handleKeyDown}
                    className={`pl-10 ${fieldErrors.email ? 'border-red-500 focus:ring-red-500' : ''}`}
                    aria-invalid={!!fieldErrors.email}
                    aria-describedby={fieldErrors.email ? 'email-error' : undefined}
                    autoComplete="email"
                    disabled={isLoading}
                    autoFocus
                  />
                </div>
                <AnimatePresence>
                  {fieldErrors.email && (
                    <motion.p
                      id="email-error"
                      initial={{ opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -5 }}
                      className="mt-2 text-sm text-red-400 flex items-center gap-1"
                      role="alert"
                    >
                      <AlertCircle className="h-3 w-3" />
                      {fieldErrors.email}
                    </motion.p>
                  )}
                </AnimatePresence>
              </div>

              {/* Password Field */}
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-foreground mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground pointer-events-none" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter your password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    onKeyDown={handleKeyDown}
                    className={`pl-10 pr-10 ${fieldErrors.password ? 'border-red-500 focus:ring-red-500' : ''}`}
                    aria-invalid={!!fieldErrors.password}
                    aria-describedby={fieldErrors.password ? 'password-error' : undefined}
                    autoComplete="current-password"
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors p-1"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    disabled={isLoading}
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
                <AnimatePresence>
                  {fieldErrors.password && (
                    <motion.p
                      id="password-error"
                      initial={{ opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -5 }}
                      className="mt-2 text-sm text-red-400 flex items-center gap-1"
                      role="alert"
                    >
                      <AlertCircle className="h-3 w-3" />
                      {fieldErrors.password}
                    </motion.p>
                  )}
                </AnimatePresence>
              </div>

              {/* Remember Me & Forgot Password */}
              <div className="flex items-center justify-between text-sm">
                <label className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={formData.rememberMe}
                    onChange={(e) => setFormData({ ...formData, rememberMe: e.target.checked })}
                    className="rounded border-white/20 bg-white/5 text-primary focus:ring-primary focus:ring-2 cursor-pointer"
                    disabled={isLoading}
                  />
                  <span className="text-muted-foreground group-hover:text-foreground transition-colors">
                    Remember me
                  </span>
                </label>
                <a 
                  href="#" 
                  className="text-primary hover:underline transition-colors font-medium"
                  tabIndex={isLoading ? -1 : 0}
                >
                  Forgot password?
                </a>
              </div>

              {/* Submit Button */}
              <Button 
                type="submit" 
                className="w-full h-12 text-base font-semibold" 
                disabled={isLoading || !formData.email || !formData.password}
                aria-busy={isLoading}
              >
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Signing in...</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <span>Sign in</span>
                    <ArrowRight className="h-5 w-5" />
                  </div>
                )}
              </Button>
            </form>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-card text-muted-foreground">Or continue with</span>
              </div>
            </div>

            {/* Social Login Buttons */}
            <div className="space-y-3">
              {/* GitHub - Recommended */}
              <div className="relative">
                <Button
                  variant="secondary"
                  onClick={handleGithubLogin}
                  className="w-full h-12"
                  disabled={isLoading}
                  aria-label="Login with GitHub (Recommended)"
                >
                  <Github className="h-5 w-5 mr-2" />
                  <span>Continue with GitHub</span>
                </Button>
                <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-primary text-white text-xs font-semibold rounded-full">
                  Recommended
                </div>
              </div>

              {/* Google */}
              <Button
                variant="secondary"
                onClick={() => {}}
                className="w-full h-12"
                disabled={isLoading}
                aria-label="Login with Google (Coming soon)"
              >
                <svg className="h-5 w-5 mr-2" viewBox="0 0 24 24">
                  <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                <span>Continue with Google</span>
                <span className="ml-2 text-xs text-muted-foreground">(Coming soon)</span>
              </Button>
            </div>

            {/* Security Note */}
            <div className="mt-6 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
              <div className="flex items-start gap-2">
                <Shield className="h-4 w-4 text-blue-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-blue-300/80">
                  <strong>Secure login:</strong> Your connection is encrypted. We never store your password in plain text.
                </p>
              </div>
            </div>

            {/* Sign Up Link */}
            <div className="mt-8 text-center text-sm">
              <span className="text-muted-foreground">Don't have an account? </span>
              <Link 
                to="/register" 
                className="text-primary hover:underline font-semibold transition-colors inline-flex items-center gap-1"
              >
                Create free account
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            {/* Terms & Privacy */}
            <div className="mt-6 pt-6 border-t border-white/10">
              <p className="text-xs text-center text-muted-foreground leading-relaxed">
                By signing in, you agree to our{' '}
                <a href="#" className="text-primary hover:underline font-medium">Terms of Service</a>
                {' '}and{' '}
                <a href="#" className="text-primary hover:underline font-medium">Privacy Policy</a>
              </p>
            </div>
          </Card>

          {/* Mobile Trust Signals */}
          <div className="lg:hidden mt-8 space-y-4">
            {trustSignals.map((signal) => (
              <div key={signal.text} className="flex items-center gap-3 text-sm text-muted-foreground">
                <signal.icon className="h-4 w-4 text-primary flex-shrink-0" />
                <div>
                  <div className="text-foreground font-medium">{signal.text}</div>
                  <div className="text-xs">{signal.subtext}</div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}
