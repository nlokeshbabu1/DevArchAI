import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Mail, Lock, User, Eye, EyeOff, Check, CheckCircle, Github, Loader2,
  AlertCircle, ArrowRight, Globe
} from 'lucide-react'
import { useAuthStore } from '../../stores/auth-store'
import { authApi } from '../../api/endpoints/auth'
import { githubAuthApi } from '../../api/endpoints/github-auth'
import { gitlabAuthApi } from '../../api/endpoints/gitlab-auth'
import { AuthLayout } from './AuthLayout'

const EASE_OUT = [0.16, 1, 0.3, 1] as const

export function Register() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { login, setUser } = useAuthStore()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [shakeField, setShakeField] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
    organization_name: '',
    country: 'IN',
    agreeToTerms: false,
  })

  const getPasswordStrength = (password: string) => {
    let strength = 0
    if (password.length >= 8) strength++
    if (password.length >= 12) strength++
    if (/[a-z]/.test(password)) strength++
    if (/[A-Z]/.test(password)) strength++
    if (/[0-9]/.test(password)) strength++
    if (/[^a-zA-Z0-9]/.test(password)) strength++
    return strength
  }

  const passwordStrength = getPasswordStrength(formData.password)
  const strengthLabels = ['Weak', 'Fair', 'Good', 'Strong', 'Very Strong', 'Excellent']
  const strengthColors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-lime-500', 'bg-green-500', 'bg-emerald-500']

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      setShakeField('confirmPassword')
      setTimeout(() => setShakeField(null), 500)
      return
    }

    if (!formData.agreeToTerms) {
      setError('You must agree to the Terms of Service')
      return
    }

    setIsLoading(true)

    try {
      await authApi.register({
        email: formData.email,
        username: formData.username,
        password: formData.password,
        organization_name: formData.organization_name,
        country: formData.country,
      })

      const loginResponse = await authApi.login({
        email: formData.email,
        password: formData.password,
      })

      login(loginResponse.access_token)

      try {
        const userResponse = await authApi.getCurrentUser()
        setUser(userResponse)
      } catch {
        console.warn('Failed to fetch user info')
      }

      queryClient.clear()
      navigate('/dashboard')
    } catch (err: any) {
      const detail = err.response?.data?.detail
      if (typeof detail === 'string') {
        setError(detail)
      } else if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg).join(', '))
      } else {
        setError('Registration failed. Please try again.')
      }
      setShakeField('form')
      setTimeout(() => setShakeField(null), 500)
    } finally {
      setIsLoading(false)
    }
  }

  const handleGithubLogin = async () => {
    try {
      const authUrl = await githubAuthApi.getAuthorizationUrl()
      if (!authUrl) {
        setError('GitHub OAuth is not configured.')
        return
      }
      window.location.href = authUrl
    } catch {
      setError('GitHub OAuth is not configured.')
    }
  }

  const handleGitlabLogin = async () => {
    try {
      const authUrl = await gitlabAuthApi.getAuthorizationUrl()
      if (!authUrl) {
        setError('GitLab OAuth is not configured.')
        return
      }
      window.location.href = authUrl
    } catch {
      setError('GitLab OAuth is not configured.')
    }
  }

  return (
    <AuthLayout>
      <div className="space-y-5">
        {/* Header */}
        <div className="text-center lg:text-left">
          <h1 className="text-2xl sm:text-[1.75rem] font-bold text-white tracking-tight">Create an account</h1>
          <p className="text-sm text-slate-400 mt-1.5">Start scanning your DevOps infrastructure</p>
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

        {/* OAuth */}
        <div className="space-y-2.5">
          <button
            type="button"
            onClick={handleGithubLogin}
            disabled={isLoading}
            className="auth-oauth-btn group"
            aria-label="Sign up with GitHub"
          >
            <Github className="h-4 w-4 text-slate-400 group-hover:text-white transition-colors" />
            <span>Sign up with GitHub</span>
          </button>
          <button
            type="button"
            onClick={handleGitlabLogin}
            disabled={isLoading}
            className="auth-oauth-btn group"
            aria-label="Sign up with GitLab"
          >
            <svg className="h-4 w-4 text-slate-400 group-hover:text-orange-400 transition-colors" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 01-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 014.82 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0118.6 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.51L23 13.45a.84.84 0 01-.35.94z"/>
            </svg>
            <span>Sign up with GitLab</span>
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
        <form onSubmit={handleSubmit} className="space-y-3.5" noValidate>
          {/* Email */}
          <div className={shakeField === 'email' ? 'auth-shake' : ''}>
            <label htmlFor="reg-email" className="block text-[13px] font-medium text-slate-300 mb-1.5">
              Email address
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
              <input
                id="reg-email"
                type="email"
                placeholder="you@company.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="auth-input pl-10"
                required
              />
            </div>
          </div>

          {/* Username */}
          <div className={shakeField === 'username' ? 'auth-shake' : ''}>
            <label htmlFor="reg-username" className="block text-[13px] font-medium text-slate-300 mb-1.5">
              Username
            </label>
            <div className="relative">
              <User className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
              <input
                id="reg-username"
                type="text"
                placeholder="johndoe"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="auth-input pl-10"
                required
                minLength={3}
              />
            </div>
          </div>

          {/* Organization */}
          <div>
            <label htmlFor="reg-org" className="block text-[13px] font-medium text-slate-300 mb-1.5">
              Organization <span className="text-slate-500 font-normal">(optional)</span>
            </label>
            <div className="relative">
              <Globe className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
              <input
                id="reg-org"
                type="text"
                placeholder="Acme Inc"
                value={formData.organization_name}
                onChange={(e) => setFormData({ ...formData, organization_name: e.target.value })}
                className="auth-input pl-10"
              />
            </div>
          </div>

          {/* Country */}
          <div>
            <label htmlFor="reg-country" className="block text-[13px] font-medium text-slate-300 mb-1.5">
              Country
            </label>
            <div className="relative">
              <Globe className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
              <select
                id="reg-country"
                value={formData.country}
                onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                className="auth-input pl-10 appearance-none cursor-pointer"
              >
                <option value="IN">India</option>
                <option value="US">United States</option>
                <option value="GB">United Kingdom</option>
                <option value="CA">Canada</option>
                <option value="AU">Australia</option>
                <option value="DE">Germany</option>
                <option value="FR">France</option>
                <option value="SG">Singapore</option>
                <option value="JP">Japan</option>
                <option value="OTHER">Other</option>
              </select>
              <div className="absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none">
                <svg className="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </div>

          {/* Password */}
          <div className={shakeField === 'password' ? 'auth-shake' : ''}>
            <label htmlFor="reg-password" className="block text-[13px] font-medium text-slate-300 mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
              <input
                id="reg-password"
                type={showPassword ? 'text' : 'password'}
                placeholder="Min 8 characters"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="auth-input pl-10 pr-10"
                required
                minLength={8}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors p-1"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {/* Strength indicator */}
            {formData.password && (
              <div className="mt-2 space-y-1">
                <div className="flex gap-1">
                  {[0, 1, 2, 3, 4, 5].map((level) => (
                    <div
                      key={level}
                      className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
                        level < passwordStrength
                          ? strengthColors[passwordStrength - 1]
                          : 'bg-white/[0.06]'
                      }`}
                    />
                  ))}
                </div>
                <p className="text-[11px] text-slate-500">
                  {strengthLabels[passwordStrength - 1] || 'Too short'}
                </p>
              </div>
            )}
          </div>

          {/* Confirm Password */}
          <div className={shakeField === 'confirmPassword' ? 'auth-shake' : ''}>
            <label htmlFor="reg-confirm" className="block text-[13px] font-medium text-slate-300 mb-1.5">
              Confirm password
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
              <input
                id="reg-confirm"
                type={showConfirmPassword ? 'text' : 'password'}
                placeholder="Re-enter password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                className={`auth-input pl-10 pr-10 ${
                  formData.confirmPassword && formData.password !== formData.confirmPassword
                    ? 'auth-input-error'
                    : ''
                }`}
                required
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors p-1"
                aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                tabIndex={-1}
              >
                {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <AnimatePresence>
              {formData.confirmPassword && formData.password !== formData.confirmPassword && (
                <motion.p
                  initial={{ opacity: 0, y: -4, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: 'auto' }}
                  exit={{ opacity: 0, y: -4, height: 0 }}
                  className="text-[12px] text-red-400 mt-1.5 flex items-center gap-1"
                  role="alert"
                >
                  <AlertCircle className="h-3 w-3" />
                  Passwords do not match
                </motion.p>
              )}
            </AnimatePresence>
          </div>

          {/* Terms checkbox */}
          <label className="flex items-start gap-2.5 cursor-pointer group">
            <div className="relative mt-0.5">
              <input
                type="checkbox"
                checked={formData.agreeToTerms}
                onChange={(e) => setFormData({ ...formData, agreeToTerms: e.target.checked })}
                className="sr-only peer"
              />
              <div className="auth-checkbox" />
              <CheckCircle className="auth-checkbox-check" />
            </div>
            <span className="text-[13px] text-slate-400 group-hover:text-slate-300 transition-colors leading-snug">
              I agree to the{' '}
              <Link to="/docs/getting-started" className="text-primary hover:text-primary/80 transition-colors font-medium">acceptable use terms</Link>
              {' '}for DevArchAI security scanning.
            </span>
          </label>

          {/* Submit */}
          <button
            type="submit"
            className="auth-submit-btn"
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="h-4 w-4" />
            )}
            <span>{isLoading ? 'Creating account...' : 'Create account'}</span>
          </button>
        </form>

        {/* Sign in link */}
        <p className="text-center text-[13px] text-slate-400">
          Already have an account?{' '}
          <Link to="/login" className="text-primary hover:text-primary/80 font-semibold transition-colors">
            Sign in
          </Link>
        </p>
      </div>
    </AuthLayout>
  )
}
