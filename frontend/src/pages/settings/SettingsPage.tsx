import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  User, Mail, Building, Key, Bell, Shield, CreditCard, Trash2,
  Save, Loader2, CheckCircle, AlertCircle, X, Eye, EyeOff,
  Copy, Check, Plus, LogOut, Monitor, Globe, Clock, Zap,
  AlertTriangle, RefreshCw, ChevronRight, Camera, Smartphone,
  Github, Gitlab, Lock,
} from 'lucide-react'
import { Button, Card, Input } from '../../components/ui'
import { Skeleton } from '../../components/ui/Skeleton'
import { authApi, type SessionInfo } from '../../api/endpoints/auth'
import { settingsApi, type ProfileData, type NotificationPrefs, type SessionData, type ApiKeyData, type CreateApiKeyResponse } from '../../api/endpoints/settings'
import { useAuthStore } from '../../stores/auth-store'
import { useNavigate } from 'react-router-dom'
import { cn } from '../../lib/utils'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function safeEmail(email: string | null | undefined): string {
  if (!email) return 'Email unavailable'
  return email
}

/* ──────────────── Tab config ──────────────── */

type TabId = 'profile' | 'security' | 'sessions'
const TABS: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'profile',  label: 'Profile',  icon: User },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'sessions', label: 'Sessions', icon: Monitor },
]

/* ──────────────────── Toast ──────────────────── */

interface Toast { id: string; type: 'success' | 'error' | 'info'; message: string }
let toastId = 0
function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([])
  const addToast = useCallback((type: Toast['type'], message: string) => {
    const id = String(++toastId)
    setToasts(prev => [...prev, { id, type, message }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
  }, [])
  const removeToast = useCallback((id: string) => setToasts(prev => prev.filter(t => t.id !== id)), [])
  return { toasts, addToast, removeToast }
}

function ToastContainer({ toasts, removeToast }: { toasts: Toast[]; removeToast: (id: string) => void }) {
  if (!toasts.length) return null
  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      <AnimatePresence>
        {toasts.map(t => (
          <motion.div key={t.id} initial={{ opacity: 0, x: 100, scale: 0.9 }} animate={{ opacity: 1, x: 0, scale: 1 }} exit={{ opacity: 0, x: 100, scale: 0.9 }}
            className={cn('flex items-start gap-3 p-4 rounded-xl border backdrop-blur-xl shadow-2xl',
              t.type === 'success' && 'bg-green-500/15 border-green-500/40',
              t.type === 'error' && 'bg-red-500/15 border-red-500/40',
              t.type === 'info' && 'bg-blue-500/15 border-blue-500/40',
            )}>
            {t.type === 'success' && <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />}
            {t.type === 'error' && <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />}
            {t.type === 'info' && <AlertCircle className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />}
            <p className={cn('text-sm flex-1', t.type === 'success' && 'text-green-200', t.type === 'error' && 'text-red-200', t.type === 'info' && 'text-blue-200')}>{t.message}</p>
            <button onClick={() => removeToast(t.id)} className="text-white/40 hover:text-white/80 transition-colors"><X className="h-4 w-4" /></button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

/* ──────────────── Password Strength ──────────────── */

function getPasswordStrength(pw: string): { label: string; color: string; width: string; score: number } {
  if (!pw) return { label: '', color: '', width: '0%', score: 0 }
  let score = 0
  if (pw.length >= 8) score += 1
  if (pw.length >= 12) score += 1
  if (/[a-z]/.test(pw)) score += 1
  if (/[A-Z]/.test(pw)) score += 1
  if (/[0-9]/.test(pw)) score += 1
  if (/[^a-zA-Z0-9]/.test(pw)) score += 1
  if (score <= 2) return { label: 'Weak', color: 'bg-red-500', width: '20%', score }
  if (score <= 3) return { label: 'Fair', color: 'bg-orange-500', width: '40%', score }
  if (score <= 4) return { label: 'Good', color: 'bg-yellow-500', width: '65%', score }
  if (score <= 5) return { label: 'Strong', color: 'bg-green-500', width: '85%', score }
  return { label: 'Very Strong', color: 'bg-emerald-500', width: '100%', score }
}

function PasswordStrengthMeter({ password }: { password: string }) {
  const strength = getPasswordStrength(password)
  if (!password) return null
  return (
    <div className="mt-2 space-y-1">
      <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
        <motion.div initial={{ width: 0 }} animate={{ width: strength.width }} transition={{ duration: 0.3 }} className={cn('h-full rounded-full', strength.color)} />
      </div>
      <p className={cn('text-xs font-medium', strength.score <= 2 && 'text-red-400', strength.score === 3 && 'text-orange-400', strength.score === 4 && 'text-yellow-400', strength.score >= 5 && 'text-green-400')}>{strength.label}</p>
    </div>
  )
}

/* ──────────────── Section Header ──────────────── */

function SectionHeader({ icon: Icon, title, description }: { icon: React.ElementType; title: string; description: string }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      <div className="p-2.5 bg-primary/15 rounded-xl border border-primary/30"><Icon className="h-5 w-5 text-primary" /></div>
      <div><h2 className="text-xl font-semibold text-foreground">{title}</h2><p className="text-sm text-muted-foreground">{description}</p></div>
    </div>
  )
}

/* ──────────────── Toggle Switch ──────────────── */

function ToggleSwitch({ checked, onChange, label, description, icon: Icon }: { checked: boolean; onChange: (v: boolean) => void; label: string; description: string; icon: React.ElementType }) {
  return (
    <label className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10 cursor-pointer hover:bg-white/10 transition-colors group">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-white/5 border border-white/10 group-hover:bg-white/10 transition-colors"><Icon className="h-4 w-4 text-muted-foreground" /></div>
        <div><p className="font-medium text-foreground text-sm">{label}</p><p className="text-xs text-muted-foreground mt-0.5">{description}</p></div>
      </div>
      <button type="button" role="switch" aria-checked={checked} onClick={(e) => { e.preventDefault(); onChange(!checked) }}
        className={cn('relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 flex-shrink-0', checked ? 'bg-primary' : 'bg-white/10')}>
        <span className={cn('inline-block h-4 w-4 rounded-full bg-white shadow-lg transform transition-transform duration-200', checked ? 'translate-x-6' : 'translate-x-1')} />
      </button>
    </label>
  )
}

/* ──────────────── Danger Confirmation Modal ──────────────── */

function ConfirmModal({ open, onClose, onConfirm, title, description, confirmLabel, isLoading, children }: { open: boolean; onClose: () => void; onConfirm: () => void; title: string; description: string; confirmLabel: string; isLoading?: boolean; children?: React.ReactNode }) {
  if (!open) return null
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="bg-card border border-white/10 rounded-2xl p-6 max-w-md w-full shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 bg-red-500/15 rounded-xl border border-red-500/30"><AlertTriangle className="h-5 w-5 text-red-400" /></div>
          <div><h3 className="text-lg font-semibold text-foreground">{title}</h3><p className="text-sm text-muted-foreground">{description}</p></div>
        </div>
        {children && <div className="mb-4">{children}</div>}
        <div className="flex gap-3 justify-end">
          <Button variant="secondary" onClick={onClose} disabled={isLoading}>Cancel</Button>
          <Button variant="destructive" onClick={onConfirm} loading={isLoading}>{confirmLabel}</Button>
        </div>
      </motion.div>
    </motion.div>
  )
}

/* ══════════════════════════════════════════════════
   PROFILE TAB
   ══════════════════════════════════════════════════ */

function ProfileTab({ profile, fullName, username, setFullName, setUsername, saving, handleSaveProfile }:
  { profile: ProfileData | null; fullName: string; username: string; setFullName: (v: string) => void; setUsername: (v: string) => void; saving: string | null; handleSaveProfile: () => Promise<void> }) {

  const providerLabel = profile?.provider === 'github' ? 'GitHub Account'
    : profile?.provider === 'gitlab' ? 'GitLab Account'
    : profile?.provider === 'email+github' ? 'Email + GitHub'
    : profile?.provider === 'email+gitlab' ? 'Email + GitLab'
    : 'Email Account'
  const providerIcon = profile?.provider === 'github' || profile?.provider === 'email+github' ? Github
    : profile?.provider === 'gitlab' || profile?.provider === 'email+gitlab' ? Gitlab
    : Mail
  const providerColor = profile?.provider === 'github' ? 'bg-gray-600/15 text-gray-300 border-gray-500/30'
    : profile?.provider === 'gitlab' ? 'bg-orange-600/15 text-orange-300 border-orange-500/30'
    : profile?.provider === 'email+github' ? 'bg-indigo-600/15 text-indigo-300 border-indigo-500/30'
    : profile?.provider === 'email+gitlab' ? 'bg-orange-600/15 text-orange-300 border-orange-500/30'
    : 'bg-primary/15 text-primary border-primary/30'

  return (
    <Card className="p-6" hover={false}>
      <SectionHeader icon={User} title="Profile Information" description="Your personal details" />

      {/* Avatar + name + provider badge */}
      <div className="flex items-center gap-5 mb-6">
        <div className="relative group">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary to-indigo-600 flex items-center justify-center text-2xl font-bold text-white shadow-lg shadow-primary/30">
            {profile?.full_name?.charAt(0)?.toUpperCase() || profile?.username?.charAt(0)?.toUpperCase() || '?'}
          </div>
          <button className="absolute inset-0 flex items-center justify-center rounded-full bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity"><Camera className="h-5 w-5 text-white" /></button>
        </div>
        <div>
          <p className="text-foreground font-medium text-lg">{profile?.full_name || profile?.username}</p>
          <p className="text-sm text-muted-foreground">{safeEmail(profile?.email)}</p>
          <span className={cn('inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium mt-1.5 border', providerColor)}>
            {providerIcon === Github ? <Github className="h-3 w-3" /> : <Mail className="h-3 w-3" />}
            {providerLabel}
          </span>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-foreground mb-2">Full Name</label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input type="text" value={fullName} onChange={e => setFullName(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              placeholder="Your full name" />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-2">Username</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">@</span>
            <input type="text" value={username} onChange={e => setUsername(e.target.value)}
              className="w-full pl-8 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              placeholder="username" />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-2">Email</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input type="email" value={safeEmail(profile?.email)} disabled
              className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-muted-foreground cursor-not-allowed" />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-2">Organization</label>
          <div className="relative">
            <Building className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input type="text" value={profile?.organization || 'No organization'} disabled
              className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-muted-foreground cursor-not-allowed" />
          </div>
        </div>
      </div>

      {/* Authentication Method */}
      <div className="mt-6 p-4 bg-white/5 rounded-xl border border-white/10">
        <p className="text-sm font-medium text-foreground mb-2">Authentication Method</p>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          {profile?.provider === 'github' ? (
            <><Github className="h-4 w-4 text-gray-400" /> GitHub OAuth</>
          ) : profile?.provider === 'gitlab' ? (
            <><Gitlab className="h-4 w-4 text-gray-400" /> GitLab OAuth</>
          ) : profile?.provider === 'email+github' ? (
            <><><Mail className="h-4 w-4 text-primary" /> Email</> <span className="text-muted-foreground/40">+</span> <Github className="h-4 w-4 text-gray-400" /> GitHub</>
          ) : profile?.provider === 'email+gitlab' ? (
            <><><Mail className="h-4 w-4 text-primary" /> Email</> <span className="text-muted-foreground/40">+</span> <Gitlab className="h-4 w-4 text-gray-400" /> GitLab</>
          ) : (
            <><Mail className="h-4 w-4 text-primary" /> Email Login</>
          )}
          {!profile?.has_password && profile?.provider !== 'github' && profile?.provider !== 'gitlab' && profile?.provider !== 'email+github' && profile?.provider !== 'email+gitlab' && (
            <span className="text-xs text-yellow-400 ml-2">(No password set)</span>
          )}
        </div>
      </div>

      {/* Member since */}
      {profile?.created_at && (
        <p className="mt-4 text-xs text-muted-foreground">
          Member since {new Date(profile.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      )}

      <div className="mt-6 flex justify-end">
        <Button variant="primary" onClick={handleSaveProfile} loading={saving === 'profile'} disabled={saving === 'profile'}>
          <Save className="h-4 w-4" /> Save Profile
        </Button>
      </div>
    </Card>
  )
}

/* ══════════════════════════════════════════════════
   SECURITY TAB
   ══════════════════════════════════════════════════ */

function SecurityTab({ profile, currentPassword, newPassword, confirmPassword, showPassword, setCurrentPassword, setNewPassword, setConfirmPassword, setShowPassword, saving, handleChangePassword, apiKeys, newKeyData, handleCreateApiKey, handleRevokeKey, copyToClipboard, copiedKey, setNewKeyData, showDeleteModal, setShowDeleteModal, deletePassword, setDeletePassword, handleDeleteAccount }:
  { profile: ProfileData | null; currentPassword: string; newPassword: string; confirmPassword: string; showPassword: { current: boolean; new: boolean; confirm: boolean }; setCurrentPassword: (v: string) => void; setNewPassword: (v: string) => void; setConfirmPassword: (v: string) => void; setShowPassword: React.Dispatch<React.SetStateAction<{ current: boolean; new: boolean; confirm: boolean }>>; saving: string | null; handleChangePassword: () => Promise<void>; apiKeys: ApiKeyData[]; newKeyData: CreateApiKeyResponse | null; handleCreateApiKey: () => Promise<void>; handleRevokeKey: (id: string) => Promise<void>; copyToClipboard: (t: string) => Promise<void>; copiedKey: boolean; setNewKeyData: (v: CreateApiKeyResponse | null) => void; showDeleteModal: boolean; setShowDeleteModal: (v: boolean) => void; deletePassword: string; setDeletePassword: (v: string) => void; handleDeleteAccount: () => Promise<void> }) {

  const passwordsMatch = !confirmPassword || newPassword === confirmPassword
  const passwordStrength = getPasswordStrength(newPassword)

  const canChangePassword = profile?.has_password !== false

  return (
    <div className="space-y-6">
      {/* ───────── Password Change ───────── */}
      <Card className="p-6" hover={false}>
        <SectionHeader icon={Key} title="Password" description={canChangePassword ? "Change your password" : "Set a password for your account"} />

        <div className="space-y-4 max-w-md">
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Current Password</label>
            <div className="relative">
              <input type={showPassword.current ? 'text' : 'password'} value={currentPassword} onChange={e => setCurrentPassword(e.target.value)}
                className="w-full pr-10 pl-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                placeholder={canChangePassword ? "Enter current password" : "Enter password"} />
              <button type="button" onClick={() => setShowPassword(prev => ({ ...prev, current: !prev.current }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                {showPassword.current ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">New Password</label>
            <div className="relative">
              <input type={showPassword.new ? 'text' : 'password'} value={newPassword} onChange={e => setNewPassword(e.target.value)}
                className="w-full pr-10 pl-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                placeholder="Enter new password" />
              <button type="button" onClick={() => setShowPassword(prev => ({ ...prev, new: !prev.new }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                {showPassword.new ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <PasswordStrengthMeter password={newPassword} />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Confirm New Password</label>
            <div className="relative">
              <input type={showPassword.confirm ? 'text' : 'password'} value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)}
                className={cn('w-full pr-10 pl-4 py-2.5 bg-white/5 border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all',
                  confirmPassword && !passwordsMatch ? 'border-red-500/50' : 'border-white/10')}
                placeholder="Confirm new password" />
              <button type="button" onClick={() => setShowPassword(prev => ({ ...prev, confirm: !prev.confirm }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                {showPassword.confirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {confirmPassword && !passwordsMatch && <p className="mt-1.5 text-xs text-red-400">Passwords do not match</p>}
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <Button variant="primary" onClick={handleChangePassword}
            loading={saving === 'password'}
            disabled={saving === 'password' || !currentPassword || !newPassword || !confirmPassword || !passwordsMatch}>
            <Lock className="h-4 w-4" /> Change Password
          </Button>
        </div>
      </Card>

      {/* ───────── MFA ───────── */}
      <Card className="p-6" hover={false}>
        <SectionHeader icon={Smartphone} title="Multi-Factor Authentication" description="Add an extra layer of security" />
        <div className="p-4 bg-white/5 rounded-xl border border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20"><Smartphone className="h-4 w-4 text-primary" /></div>
            <div>
              <p className="text-sm font-medium text-foreground">Authenticator App</p>
              <p className="text-xs text-muted-foreground">Status: Not Configured</p>
            </div>
          </div>
          <span className="px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider bg-yellow-500/15 text-yellow-400 border border-yellow-500/30 rounded-full">
            Coming Soon
          </span>
        </div>
      </Card>

      {/* ───────── API Keys ───────── */}
      <Card className="p-6" hover={false}>
        <SectionHeader icon={Key} title="API Keys" description="Manage your API keys for programmatic access" />

        <AnimatePresence>
          {newKeyData && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
              className="mb-4 p-4 bg-green-500/10 rounded-xl border border-green-500/30">
              <div className="flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-green-300">API Key Created</p>
                  <p className="text-xs text-green-400/80 mt-1">Copy this key now. You won't be able to see it again.</p>
                  <div className="mt-2 flex items-center gap-2">
                    <code className="flex-1 px-3 py-2 bg-black/30 rounded-lg text-sm font-mono text-green-200 break-all">{newKeyData.full_key}</code>
                    <button onClick={() => copyToClipboard(newKeyData.full_key)} className="p-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors">
                      {copiedKey ? <Check className="h-4 w-4 text-green-400" /> : <Copy className="h-4 w-4 text-muted-foreground" />}
                    </button>
                  </div>
                </div>
                <button onClick={() => setNewKeyData(null)} className="text-white/40 hover:text-white/80"><X className="h-4 w-4" /></button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {apiKeys.length > 0 && (
          <div className="space-y-3 mb-4">
            {apiKeys.map(key => (
              <div key={key.id} className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-2 rounded-lg bg-primary/10 border border-primary/20"><Key className="h-4 w-4 text-primary" /></div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-foreground">{key.name || 'API Key'}</p>
                      <code className="text-xs text-muted-foreground font-mono">{key.masked_key || `sk-****${key.id.slice(-4)}`}</code>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">Created {key.created_at ? new Date(key.created_at).toLocaleDateString() : 'N/A'}</p>
                  </div>
                </div>
                <button onClick={() => handleRevokeKey(key.id)} disabled={saving === `revoke-${key.id}`}
                  className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50">
                  {saving === `revoke-${key.id}` ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                </button>
              </div>
            ))}
          </div>
        )}

        {apiKeys.length === 0 && !newKeyData && (
          <div className="mb-4 p-4 bg-white/5 rounded-xl border border-white/10 text-center">
            <Key className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">No API keys yet. Create one for programmatic access.</p>
          </div>
        )}

        <div className="flex justify-end">
          <Button variant="primary" onClick={handleCreateApiKey} loading={saving === 'apikey'} disabled={saving === 'apikey'}>
            <Plus className="h-4 w-4" /> Generate API Key
          </Button>
        </div>
      </Card>

      {/* ───────── Danger Zone ───────── */}
      <Card className="p-6 border-red-500/30" glass={false} hover={false}>
        <SectionHeader icon={AlertTriangle} title="Danger Zone" description="Irreversible account actions" />
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 bg-red-500/5 rounded-xl border border-red-500/20">
          <div>
            <p className="text-sm font-medium text-foreground">Delete Account</p>
            <p className="text-xs text-muted-foreground mt-0.5">Permanently delete your account and all associated data. This action cannot be undone.</p>
          </div>
          <Button variant="destructive" onClick={() => setShowDeleteModal(true)}><Trash2 className="h-4 w-4" /> Delete Account</Button>
        </div>
      </Card>
    </div>
  )
}

/* ══════════════════════════════════════════════════
   SESSIONS TAB
   ══════════════════════════════════════════════════ */

function SessionsTab({ sessions, prefs, saving, handleRevokeSession, handleRevokeAll, handleSavePrefs, setPrefs, handleNavigateBilling, profile }: {
  sessions: SessionInfo[]; prefs: NotificationPrefs; saving: string | null; handleRevokeSession: (id: string) => Promise<void>; handleRevokeAll: () => Promise<void>; handleSavePrefs: () => Promise<void>; setPrefs: (v: NotificationPrefs | ((prev: NotificationPrefs) => NotificationPrefs)) => void; handleNavigateBilling: () => void; profile: ProfileData | null }) {

  return (
    <div className="space-y-6">
      {/* ───────── Active Sessions ───────── */}
      <Card className="p-6" hover={false}>
        <SectionHeader icon={Monitor} title="Active Sessions" description="Manage your active login sessions" />

        {sessions.length > 0 && (
          <div className="mb-4 flex justify-end">
            <Button variant="secondary" size="sm" onClick={handleRevokeAll} loading={saving === 'revoke-all'} disabled={saving === 'revoke-all'}>
              <LogOut className="h-3.5 w-3.5" /> Logout All Devices
            </Button>
          </div>
        )}

        <div className="space-y-3">
          {sessions.length === 0 ? (
            <div className="p-4 bg-white/5 rounded-xl border border-white/10 text-center">
              <p className="text-sm text-muted-foreground">No active sessions found</p>
            </div>
          ) : (
            sessions.map(session => (
              <div key={session.id} className={cn('flex items-center justify-between p-4 rounded-xl border transition-colors',
                session.is_current ? 'bg-primary/5 border-primary/30' : 'bg-white/5 border-white/10')}>
                <div className="flex items-center gap-3 min-w-0">
                  <div className={cn('p-2 rounded-lg', session.is_current ? 'bg-primary/10 border border-primary/20' : 'bg-white/5 border border-white/10')}>
                    <Monitor className={cn('h-4 w-4', session.is_current ? 'text-primary' : 'text-muted-foreground')} />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-medium text-foreground">{session.browser || session.device_name || 'Unknown device'}</p>
                      {session.os && <span className="text-xs text-muted-foreground">· {session.os}</span>}
                      {session.is_current && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/20 text-primary font-medium">Current</span>}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5 flex-wrap">
                      {session.ip_address && <span className="flex items-center gap-1"><Globe className="h-3 w-3" />{session.ip_address}</span>}
                      {session.last_active_at && <span className="flex items-center gap-1"><Clock className="h-3 w-3" />Active {new Date(session.last_active_at).toLocaleDateString()}</span>}
                      {session.created_at && <span>Created {new Date(session.created_at).toLocaleDateString()}</span>}
                    </div>
                  </div>
                </div>
                {!session.is_current && (
                  <button onClick={() => handleRevokeSession(session.id)} disabled={saving === `session-${session.id}`}
                    className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50">
                    {saving === `session-${session.id}` ? <Loader2 className="h-4 w-4 animate-spin" /> : <LogOut className="h-4 w-4" />}
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </Card>

      {/* ───────── Notification Preferences ───────── */}
      <Card className="p-6" hover={false}>
        <SectionHeader icon={Bell} title="Notification Preferences" description="Control what notifications you receive" />

        <div className="space-y-3">
          <ToggleSwitch icon={Bell} label="Email Notifications" description="Receive email notifications about scan results"
            checked={prefs.email_notifications} onChange={v => setPrefs(prev => ({ ...prev, email_notifications: v }))} />
          <ToggleSwitch icon={AlertTriangle} label="Critical Findings Alerts" description="Get notified about critical security findings immediately"
            checked={prefs.security_alerts} onChange={v => setPrefs(prev => ({ ...prev, security_alerts: v }))} />
          <ToggleSwitch icon={Clock} label="Weekly Reports" description="Receive a weekly summary of all scans and findings"
            checked={prefs.weekly_reports} onChange={v => setPrefs(prev => ({ ...prev, weekly_reports: v }))} />
          <ToggleSwitch icon={RefreshCw} label="Product Updates" description="Get notified about new features and product updates"
            checked={prefs.product_updates} onChange={v => setPrefs(prev => ({ ...prev, product_updates: v }))} />
          <ToggleSwitch icon={CheckCircle} label="Scan Completion Alerts" description="Get notified when a scan completes"
            checked={prefs.scan_completion_alerts} onChange={v => setPrefs(prev => ({ ...prev, scan_completion_alerts: v }))} />
        </div>

        <div className="mt-6 flex justify-end">
          <Button variant="primary" onClick={handleSavePrefs} loading={saving === 'prefs'} disabled={saving === 'prefs'}>
            <Save className="h-4 w-4" /> Save Preferences
          </Button>
        </div>
      </Card>

      {/* ───────── Plan & Billing ───────── */}
      <Card className="p-6" hover={false}>
        <SectionHeader icon={CreditCard} title="Plan & Billing" description="Manage your subscription and billing" />
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 bg-white/5 rounded-xl border border-white/10">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-primary/15 rounded-xl border border-primary/30"><Zap className="h-5 w-5 text-primary" /></div>
            <div>
              <p className="text-sm font-medium text-foreground">Current Plan: <span className="text-primary capitalize">{profile?.plan || 'Free'}</span></p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {profile?.plan === 'free' ? '3 scans per month · 1 repository' :
                 profile?.plan === 'plus' ? '50 scans per month · 5 repositories' :
                 profile?.plan === 'pro' ? 'Unlimited scans · Unlimited repositories' :
                 'Enterprise-grade security'}
              </p>
            </div>
          </div>
          <Button variant="primary" onClick={handleNavigateBilling}>Manage Billing <ChevronRight className="h-4 w-4" /></Button>
        </div>
      </Card>
    </div>
  )
}

/* ══════════════════════════════════════════════════
   MAIN SETTINGS PAGE
   ══════════════════════════════════════════════════ */

export function SettingsPage() {
  const navigate = useNavigate()
  const { user, setUser } = useAuthStore()
  const { toasts, addToast, removeToast } = useToast()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)

  /* ── Tabs ── */
  const [activeTab, setActiveTab] = useState<TabId>('profile')

  /* ── Profile ── */
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [fullName, setFullName] = useState('')
  const [username, setUsername] = useState('')

  /* ── Security ── */
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState({ current: false, new: false, confirm: false })

  /* ── API Keys ── */
  const [apiKeys, setApiKeys] = useState<ApiKeyData[]>([])
  const [newKeyData, setNewKeyData] = useState<CreateApiKeyResponse | null>(null)
  const [copiedKey, setCopiedKey] = useState(false)

  /* ── Notifications ── */
  const [prefs, setPrefs] = useState<NotificationPrefs>({
    email_notifications: true,
    security_alerts: true,
    weekly_reports: false,
    product_updates: false,
    scan_completion_alerts: true,
  })

  /* ── Sessions ── */
  const [sessions, setSessions] = useState<SessionInfo[]>([])

  /* ── Danger Zone ── */
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')

  /* ── Load Data ── */
  useEffect(() => {
    async function loadAll() {
      setLoading(true)
      try {
        const [profileData, prefsData, sessionsData, keysData] = await Promise.all([
          settingsApi.getProfile(),
          settingsApi.getPreferences(),
          authApi.getSessions(),
          settingsApi.getApiKeys(),
        ])
        setProfile(profileData)
        setFullName(profileData.full_name || '')
        setUsername(profileData.username)
        setPrefs(prefsData)
        setSessions(sessionsData)
        setApiKeys(keysData)
      } catch (err: any) {
        addToast('error', err?.response?.data?.detail || 'Failed to load settings')
      } finally {
        setLoading(false)
      }
    }
    loadAll()
  }, [addToast])

  /* ── Save Profile ── */
  const handleSaveProfile = async () => {
    setSaving('profile')
    try {
      const updated = await settingsApi.updateProfile({ full_name: fullName, username })
      setProfile(updated)
      setFullName(updated.full_name || '')
      setUsername(updated.username)
      if (user) {
        setUser({ ...user, full_name: updated.full_name || '', username: updated.username })
      }
      addToast('success', 'Profile updated successfully')
    } catch (err: any) {
      addToast('error', err?.response?.data?.detail || 'Failed to update profile')
    } finally {
      setSaving(null)
    }
  }

  /* ── Change Password ── */
  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      addToast('error', 'New passwords do not match')
      return
    }
    if (!currentPassword) {
      addToast('error', 'Current password is required')
      return
    }
    if (newPassword.length < 8) {
      addToast('error', 'New password must be at least 8 characters')
      return
    }
    setSaving('password')
    try {
      await settingsApi.changePassword({ current_password: currentPassword, new_password: newPassword })
      addToast('success', 'Password changed successfully')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      addToast('error', err?.response?.data?.detail || 'Failed to change password')
    } finally {
      setSaving(null)
    }
  }

  /* ── API Keys ── */
  const handleCreateApiKey = async () => {
    setSaving('apikey')
    try {
      const result = await settingsApi.createApiKey()
      setNewKeyData(result)
      setApiKeys(prev => [{
        id: result.id,
        name: result.name,
        masked_key: result.masked_key,
        created_at: result.created_at,
      }, ...prev])
      addToast('success', 'API key created. Copy it now - you won\'t see it again.')
    } catch (err: any) {
      addToast('error', err?.response?.data?.detail || 'Failed to create API key')
    } finally {
      setSaving(null)
    }
  }

  const handleRevokeKey = async (keyId: string) => {
    setSaving(`revoke-${keyId}`)
    try {
      await settingsApi.revokeApiKey(keyId)
      setApiKeys(prev => prev.filter(k => k.id !== keyId))
      addToast('success', 'API key revoked')
    } catch (err: any) {
      addToast('error', err?.response?.data?.detail || 'Failed to revoke API key')
    } finally {
      setSaving(null)
    }
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedKey(true)
      setTimeout(() => setCopiedKey(false), 2000)
    } catch {
      addToast('error', 'Failed to copy to clipboard')
    }
  }

  /* ── Notifications ── */
  const handleSavePrefs = async () => {
    setSaving('prefs')
    try {
      await settingsApi.updatePreferences(prefs)
      addToast('success', 'Notification preferences updated')
    } catch (err: any) {
      addToast('error', err?.response?.data?.detail || 'Failed to update preferences')
    } finally {
      setSaving(null)
    }
  }

  /* ── Sessions ── */
  const handleRevokeSession = async (sessionId: string) => {
    setSaving(`session-${sessionId}`)
    try {
      await authApi.revokeSession(sessionId)
      setSessions(prev => prev.filter(s => s.id !== sessionId))
      addToast('success', 'Session revoked')
    } catch (err: any) {
      addToast('error', err?.response?.data?.detail || 'Failed to revoke session')
    } finally {
      setSaving(null)
    }
  }

  const handleRevokeAll = async () => {
    setSaving('revoke-all')
    try {
      const result = await authApi.revokeAllSessions()
      setSessions(prev => prev.filter(s => s.is_current))
      addToast('success', result.message || 'All other sessions revoked')
    } catch (err: any) {
      addToast('error', err?.response?.data?.detail || 'Failed to revoke sessions')
    } finally {
      setSaving(null)
    }
  }

  /* ── Delete Account ── */
  const handleDeleteAccount = async () => {
    if (!deletePassword) {
      addToast('error', 'Password is required to delete account')
      return
    }
    setSaving('delete')
    try {
      await settingsApi.deleteAccount(deletePassword)
      addToast('info', 'Account deleted')
      setTimeout(() => {
        const { logout } = useAuthStore.getState()
        logout()
        navigate('/')
      }, 1000)
    } catch (err: any) {
      addToast('error', err?.response?.data?.detail || 'Failed to delete account')
    } finally {
      setSaving(null)
      setShowDeleteModal(false)
      setDeletePassword('')
    }
  }

  /* ── Navigate to billing ── */
  const handleNavigateBilling = () => navigate('/billing')

  /* ── Render ── */
  if (loading) {
    return (
      <div className="space-y-6 max-w-4xl">
        <div className="space-y-1">
          <Skeleton className="h-9 w-48" />
          <Skeleton className="h-5 w-72" />
        </div>
        {[1, 2, 3].map(i => (
          <div key={i} className="rounded-2xl border border-white/10 bg-card/50 p-6 space-y-4">
            <div className="flex items-center gap-3">
              <Skeleton className="h-10 w-10 rounded-xl" />
              <div className="space-y-2">
                <Skeleton className="h-5 w-40" />
                <Skeleton className="h-4 w-56" />
              </div>
            </div>
            <div className="space-y-3 pt-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-2/3" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <>
      <ToastContainer toasts={toasts} removeToast={removeToast} />

      <div className="space-y-6 max-w-4xl pb-12">

        {/* ─── Header ─── */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold text-foreground">Settings</h1>
          <p className="text-muted-foreground mt-1">Manage your account settings and preferences</p>
        </motion.div>

        {/* ─── Tabs ─── */}
        <div className="flex gap-1 p-1 bg-white/5 rounded-xl border border-white/10 w-fit">
          {TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                activeTab === tab.id
                  ? 'bg-primary text-white shadow-lg shadow-primary/30'
                  : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
              )}>
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* ─── Tab Content ─── */}
        <AnimatePresence mode="wait">
          <motion.div key={activeTab} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.15 }}>
            {activeTab === 'profile' && (
              <ProfileTab profile={profile} fullName={fullName} username={username}
                setFullName={setFullName} setUsername={setUsername}
                saving={saving} handleSaveProfile={handleSaveProfile} />
            )}

            {activeTab === 'security' && (
              <SecurityTab profile={profile}
                currentPassword={currentPassword} newPassword={newPassword} confirmPassword={confirmPassword}
                showPassword={showPassword} setCurrentPassword={setCurrentPassword}
                setNewPassword={setNewPassword} setConfirmPassword={setConfirmPassword}
                setShowPassword={setShowPassword} saving={saving} handleChangePassword={handleChangePassword}
                apiKeys={apiKeys} newKeyData={newKeyData} handleCreateApiKey={handleCreateApiKey}
                handleRevokeKey={handleRevokeKey} copyToClipboard={copyToClipboard}
                copiedKey={copiedKey} setNewKeyData={setNewKeyData}
                showDeleteModal={showDeleteModal} setShowDeleteModal={setShowDeleteModal}
                deletePassword={deletePassword} setDeletePassword={setDeletePassword}
                handleDeleteAccount={handleDeleteAccount} />
            )}

            {activeTab === 'sessions' && (
              <SessionsTab sessions={sessions} prefs={prefs} saving={saving}
                handleRevokeSession={handleRevokeSession} handleRevokeAll={handleRevokeAll}
                handleSavePrefs={handleSavePrefs} setPrefs={setPrefs}
                handleNavigateBilling={handleNavigateBilling} profile={profile} />
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* ─── Delete Confirm Modal ─── */}
      <AnimatePresence>
        {showDeleteModal && (
          <ConfirmModal open={showDeleteModal} onClose={() => { setShowDeleteModal(false); setDeletePassword('') }}
            onConfirm={handleDeleteAccount} title="Delete Account"
            description="This will permanently delete your account, scans, findings, and all associated data. Enter your password to confirm."
            confirmLabel="Permanently Delete" isLoading={saving === 'delete'}>
            <div className="mt-4">
              <input type="password" value={deletePassword} onChange={e => setDeletePassword(e.target.value)}
                className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all"
                placeholder="Enter your password to confirm" autoFocus />
            </div>
          </ConfirmModal>
        )}
      </AnimatePresence>
    </>
  )
}
