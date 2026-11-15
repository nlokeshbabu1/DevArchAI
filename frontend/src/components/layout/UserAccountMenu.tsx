import { CreditCard, LogOut, Plug, Settings } from 'lucide-react'
import { memo } from 'react'

import type { ProductConfig } from '../../hooks/useProductConfig'
import { cn } from '../../lib/utils'
import { Button } from '../ui'
import { StatusBadge } from '../ui/StatusBadge'

export type AuthUserProfile = {
  email?: string
  username?: string
  full_name?: string
  avatar_url?: string
  plan?: string
  role?: string
}

export function userDisplayName(user: AuthUserProfile | null): string {
  if (!user) {return 'Account'}
  return user.full_name?.trim() || user.username || user.email?.split('@')[0] || 'Account'
}

export function userInitials(user: AuthUserProfile | null): string {
  const name = userDisplayName(user)
  const parts = name.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
}

type UserAccountMenuProps = {
  user: AuthUserProfile | null
  productConfig: ProductConfig
  logoutInProgress?: boolean
  authLoading?: boolean
  onSettings: () => void
  onBilling?: () => void
  onIntegrations?: () => void
  onLogout: () => void
  className?: string
}

export const UserAccountMenu = memo(function UserAccountMenu({
  user,
  productConfig,
  logoutInProgress,
  authLoading,
  onSettings,
  onBilling,
  onIntegrations,
  onLogout,
  className,
}: UserAccountMenuProps) {
  const displayName = userDisplayName(user)
  const email = user?.email || ''
  const initials = userInitials(user)

  return (
    <div className={cn('p-2 space-y-1', className)} role="menu">
      <div className="flex items-start gap-3 px-2 py-2 border-b border-white/10 mb-1">
        <div
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-indigo-600 text-sm font-semibold text-white"
          aria-hidden
        >
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className="h-full w-full rounded-full object-cover" />
          ) : (
            initials
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground truncate">{displayName}</p>
          {email ? (
            <p className="text-xs text-muted-foreground truncate">{email}</p>
          ) : (
            <p className="text-xs text-muted-foreground">Loading profile…</p>
          )}
          <div className="mt-2 flex flex-wrap gap-1.5">
            {productConfig.beta_access_mode ? (
              <StatusBadge
                status="beta"
                label={productConfig.beta_label || 'Beta'}
                dot
              />
            ) : user?.plan ? (
              <span className="inline-flex items-center rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                {user.plan} plan
              </span>
            ) : null}
            {user?.role ? (
              <span className="inline-flex items-center rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-medium text-muted-foreground capitalize">
                {user.role}
              </span>
            ) : null}
          </div>
        </div>
      </div>

      <Button variant="ghost" className="w-full justify-start gap-2" onClick={onSettings} role="menuitem">
        <Settings className="h-4 w-4" aria-hidden />
        Account settings
      </Button>
      {onIntegrations && (
        <Button variant="ghost" className="w-full justify-start gap-2" onClick={onIntegrations} role="menuitem">
          <Plug className="h-4 w-4" aria-hidden />
          Integrations
        </Button>
      )}
      {productConfig.checkout_enabled && onBilling && (
        <Button variant="ghost" className="w-full justify-start gap-2" onClick={onBilling} role="menuitem">
          <CreditCard className="h-4 w-4" aria-hidden />
          Billing & usage
        </Button>
      )}

      <div className="border-t border-white/10 pt-1 mt-1">
        <Button
          variant="ghost"
          className="w-full justify-start gap-2 text-red-400 hover:text-red-300 hover:bg-red-500/10"
          disabled={logoutInProgress || authLoading}
          onClick={onLogout}
          role="menuitem"
        >
          <LogOut className="h-4 w-4" aria-hidden />
          {logoutInProgress ? 'Signing out…' : 'Log out'}
        </Button>
      </div>
    </div>
  )
})

// motion optional - remove if not imported - I used motion.div by mistake, fix to div