import { useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Mail, Lock, Eye, EyeOff, Github, Loader2,
  CheckCircle, AlertCircle, ArrowRight, Shield
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { authApi } from '../../api/endpoints/auth'
import { githubAuthApi } from '../../api/endpoints/github-auth'
import { gitlabAuthApi } from '../../api/endpoints/gitlab-auth'
import { fetchProductConfig } from '../../hooks/useProductConfig'
import { createCheckout, handleCheckoutResponse } from '../../lib/payment-gateway'
import { useAuthStore, initAuthSync } from '../../stores/auth-store'

import { AuthLayout } from './AuthLayout'

const EASE_OUT = [0.16, 1, 0.3, 1] as const

export function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const { login, setUser, isAuthenticated, isLoading: authBootstrapping, checkAuth } = useAuthStore()

  useEffect(() => {
    initAuthSync()
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true })
      return
    }
    checkAuth()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!authBootstrapping && isAuthenticated) {
      navigate('/dashboard', { replace: true })
    }
  }, [authBootstrapping, isAuthenticated, navigate])

  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [shakeField, setShakeField] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({})
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false,
  })

  useEffect(() => {
    if (error) {setError('')}
  }, [formData.email, formData.password])

  useEffect(() => {
    const oauthError = searchParams.get('error')
    if (oauthError) {
      setError(decodeURIComponent(oauthError.replace(/\+/g, ' ')))
    }
  }, [searchParams])

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
    if (errors.email || errors.password) {
      setShakeField(errors.email ? 'email' : 'password')
      setTimeout(() => setShakeField(null), 500)
    }
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setFieldErrors({})

    if (!validateForm()) {return}

    setIsLoading(true)

    try {
      const tokenResponse = await authApi.login(formData)

      login(tokenResponse.access_token)
      setSuccess('Login successful! Redirecting...')

      try {
        const userResponse = await authApi.getCurrentUser()
        setUser(userResponse)
        queryClient.clear()

        const redirectPath = sessionStorage.getItem('postLoginRedirect')
        const upgradeIntent = sessionStorage.getItem('upgradeIntent')

        if (upgradeIntent === 'true') {
          const plan = sessionStorage.getItem('upgradePlan') || 'plus'
          const targetRedirect = redirectPath || '/dashboard'
          sessionStorage.removeItem('upgradeIntent')
          sessionStorage.removeItem('upgradePlan')
          sessionStorage.removeItem('postLoginRedirect')

          const productConfig = await fetchProductConfig()
          if (!productConfig.checkout_enabled) {
            navigate(targetRedirect)
            return
          }

          try {
            const data = await createCheckout(
              { plan, billing: 'monthly' },
              tokenResponse.access_token
            )
            await handleCheckoutResponse(data)
            return
          } catch (checkoutError) {
            console.error('Checkout creation failed:', checkoutError)
          }
          navigate(`/pricing?plan=${plan}&redirect=${encodeURIComponent(targetRedirect)}`)
        } else if (redirectPath) {
          sessionStorage.removeItem('postLoginRedirect')
          navigate(redirectPath)
        } else {
          navigate('/dashboard')
        }
      } catch {
        queryClient.clear()
        navigate('/dashboard')
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Login failed. Please check your credentials.'
      setError(errorMessage)
      setShakeField('form')
      setTimeout(() => setShakeField(null), 500)
    } finally {
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
        setError('GitHub OAuth is not configured.')
        setIsLoading(false)
        return
      }
      window.location.href = authUrl
    } catch {
      setError('GitHub OAuth is not configured.')
      setIsLoading(false)
    }
  }

  const handleGitlabLogin = async () => {
    setError('')
    setIsLoading(true)
    try {
      const authUrl = await gitlabAuthApi.getAuthorizationUrl()
      if (!authUrl) {
        setError('GitLab OAuth is not configured.')
        setIsLoading(false)
        return
      }
      window.location.href = authUrl
    } catch {
      setError('GitLab OAuth is not configured.')
      setIsLoading(false)
    }
  }

  if (authBootstrapping) {
    return (
      <AuthLayout>
        <div className="flex flex-col items-center justify-center py-16 gap-4" role="status" aria-live="polite">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-slate-400">Restoring your session…</p>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="text-center lg:text-left">
          <h1 className="text-2xl sm:text-[1.75rem] font-bold text-white tracking-tight">Welcome back</h1>
          <p className="text-sm text-slate-400 mt-1.5">Sign in to continue securing your infrastructure</p>
        </div>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8, height: 0 }}
              animate={{ opacity: 1, y: 0, height: 'auto' }}
              exit={{ opacity: 0, y: -8, height: 0 }}
              className="p-3.5 rounded-xl bg-red-500/[0.08] border border-red-500/20 flex items-center gap-2.5"
              role="alert"
              aria-live="polite"
            >
              <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
              <span className="text-sm text-red-300">{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Success */}
        <AnimatePresence>
          {success && (
            <motion.div
              initial={{ opacity: 0, y: -8, height: 0 }}
              animate={{ opacity: 1, y: 0, height: 'auto' }}
              exit={{ opacity: 0, y: -8, height: 0 }}
              className="p-3.5 rounded-xl bg-green-500/[0.08] border border-green-500/20 flex items-center gap-2.5"
            >
              <CheckCircle className="h-4 w-4 text-green-400 flex-shrink-0" />
              <span className="text-sm text-green-300">{success}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* OAuth Buttons */}
        <div className="space-y-2.5">
          <button
            type="button"
            onClick={handleGithubLogin}
            disabled={isLoading}
            className="auth-oauth-btn group"
            aria-label="Login with GitHub"
          >
            <Github className="h-4 w-4 text-slate-400 group-hover:text-white transition-colors" />
            <span>Continue with GitHub</span>
          </button>
          <button
            type="button"
            onClick={handleGitlabLogin}
            disabled={isLoading}
            className="auth-oauth-btn group"
            aria-label="Login with GitLab"
          >
            <svg className="h-4 w-4 text-slate-400 group-hover:text-orange-400 transition-colors" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 01-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 014.82 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0118.6 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.51L23 13.45a.84.84 0 01-.35.94z"/>
            </svg>
            <span>Continue with GitLab</span>
          </button>
        </div>

        {/* Divider */}
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-white/[0.06]" />
          </div>
          <div className="relative flex justify-center">
            <span className="px-3 text-[11px] font-medium text-slate-500 uppercase tracking-wider bg-[#0B1020]">
              or continue with email
            </span>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {/* Email */}
          <div className={shakeField === 'email' ? 'auth-shake' : ''}>
            <label htmlFor="email" className="block text-[13px] font-medium text-slate-300 mb-1.5">
              Email address
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
              <input
                id="email"
                type="email"
                placeholder="you@company.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className={`auth-input pl-10 ${fieldErrors.email ? 'auth-input-error' : ''}`}
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
                  initial={{ opacity: 0, y: -4, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: 'auto' }}
                  exit={{ opacity: 0, y: -4, height: 0 }}
                  className="text-[12px] text-red-400 mt-1.5 flex items-center gap-1"
                  role="alert"
                >
                  <AlertCircle className="h-3 w-3" />
                  {fieldErrors.email}
                </motion.p>
              )}
            </AnimatePresence>
          </div>

          {/* Password */}
          <div className={shakeField === 'password' ? 'auth-shake' : ''}>
            <label htmlFor="password" className="block text-[13px] font-medium text-slate-300 mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="Enter your password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className={`auth-input pl-10 pr-10 ${fieldErrors.password ? 'auth-input-error' : ''}`}
                aria-invalid={!!fieldErrors.password}
                aria-describedby={fieldErrors.password ? 'password-error' : undefined}
                autoComplete="current-password"
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors p-1"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                disabled={isLoading}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <AnimatePresence>
              {fieldErrors.password && (
                <motion.p
                  id="password-error"
                  initial={{ opacity: 0, y: -4, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: 'auto' }}
                  exit={{ opacity: 0, y: -4, height: 0 }}
                  className="text-[12px] text-red-400 mt-1.5 flex items-center gap-1"
                  role="alert"
                >
                  <AlertCircle className="h-3 w-3" />
                  {fieldErrors.password}
                </motion.p>
              )}
            </AnimatePresence>
          </div>

          {/* Remember me & Forgot */}
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2.5 cursor-pointer group">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={formData.rememberMe}
                  onChange={(e) => setFormData({ ...formData, rememberMe: e.target.checked })}
                  className="sr-only peer"
                  disabled={isLoading}
                />
                <div className="auth-checkbox" />
                <CheckCircle className="auth-checkbox-check" />
              </div>
              <span className="text-[13px] text-slate-400 group-hover:text-slate-300 transition-colors">
                Remember me
              </span>
            </label>
          </div>

          {/* Submit */}
          <button
            type="submit"
            className="auth-submit-btn"
            disabled={isLoading || !formData.email || !formData.password}
            aria-busy={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="h-4 w-4" />
            )}
            <span>{isLoading ? 'Signing in...' : 'Sign in'}</span>
          </button>
        </form>

        {/* Sign up link */}
        <p className="text-center text-[13px] text-slate-400">
          Don&apos;t have an account?{' '}
          <Link to="/register" className="text-primary hover:text-primary/80 font-semibold transition-colors">
            Create free account
          </Link>
        </p>

        {/* Terms */}
        <p className="text-[11px] text-center text-slate-500 leading-relaxed">
          By signing in, you agree to DevArchAI&apos;s{' '}
          <Link to="/docs/getting-started" className="text-slate-400 hover:text-white transition-colors underline">
            acceptable use terms
          </Link>
          {' '}for security scanning services.
        </p>
      </div>
    </AuthLayout>
  )
}
