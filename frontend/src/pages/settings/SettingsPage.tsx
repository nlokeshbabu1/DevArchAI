import { useState } from 'react'
import { motion } from 'framer-motion'
import { User, Mail, Building, Key, Bell, Shield, CreditCard, LogOut, Save, Loader2, CheckCircle } from 'lucide-react'
import { Button, Card } from '../../components/ui'
import { useAuthStore } from '../../stores/auth-store'
import { useNavigate } from 'react-router-dom'

export function SettingsPage() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState({
    fullName: user?.full_name || '',
    email: user?.email || '',
    organization: '',
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
    emailNotifications: true,
    securityAlerts: true,
    weeklyReports: false,
  })

  const handleSave = async () => {
    setIsLoading(true)
    // TODO: Implement API call to update profile
    await new Promise(resolve => setTimeout(resolve, 1000))
    setIsLoading(false)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const inputClass = "w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
  const labelClass = "block text-sm font-medium text-foreground mb-2"

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Manage your account settings and preferences
        </p>
      </motion.div>

      {/* Profile Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <Card className="p-6" hover={false}>
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2.5 bg-primary/15 rounded-xl border border-primary/30">
              <User className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-foreground">Profile Information</h2>
              <p className="text-sm text-muted-foreground">Update your personal information</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className={labelClass}>Full Name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  value={formData.fullName}
                  onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                  className={`${inputClass} pl-10`}
                  placeholder="John Doe"
                />
              </div>
            </div>

            <div>
              <label className={labelClass}>Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className={`${inputClass} pl-10`}
                  placeholder="john@example.com"
                />
              </div>
            </div>

            <div>
              <label className={labelClass}>Organization</label>
              <div className="relative">
                <Building className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  value={formData.organization}
                  onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                  className={`${inputClass} pl-10`}
                  placeholder="Acme Inc."
                />
              </div>
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Change Password Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <Card className="p-6" hover={false}>
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2.5 bg-primary/15 rounded-xl border border-primary/30">
              <Key className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-foreground">Change Password</h2>
              <p className="text-sm text-muted-foreground">Update your password securely</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className={labelClass}>Current Password</label>
              <input
                type="password"
                value={formData.currentPassword}
                onChange={(e) => setFormData({ ...formData, currentPassword: e.target.value })}
                className={inputClass}
                placeholder="••••••••"
              />
            </div>

            <div>
              <label className={labelClass}>New Password</label>
              <input
                type="password"
                value={formData.newPassword}
                onChange={(e) => setFormData({ ...formData, newPassword: e.target.value })}
                className={inputClass}
                placeholder="••••••••"
              />
            </div>

            <div>
              <label className={labelClass}>Confirm New Password</label>
              <input
                type="password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                className={inputClass}
                placeholder="••••••••"
              />
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Notifications Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <Card className="p-6" hover={false}>
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2.5 bg-primary/15 rounded-xl border border-primary/30">
              <Bell className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-foreground">Notifications</h2>
              <p className="text-sm text-muted-foreground">Manage your notification preferences</p>
            </div>
          </div>

          <div className="space-y-4">
            <label className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10 cursor-pointer hover:bg-white/10 transition-colors">
              <div className="flex items-center gap-3">
                <Bell className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium text-foreground">Email Notifications</p>
                  <p className="text-sm text-muted-foreground">Receive emails about scan results</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={formData.emailNotifications}
                onChange={(e) => setFormData({ ...formData, emailNotifications: e.target.checked })}
                className="w-5 h-5 rounded border-white/20 bg-white/5 text-primary focus:ring-primary focus:ring-2"
              />
            </label>

            <label className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10 cursor-pointer hover:bg-white/10 transition-colors">
              <div className="flex items-center gap-3">
                <Shield className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium text-foreground">Security Alerts</p>
                  <p className="text-sm text-muted-foreground">Get notified about critical findings</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={formData.securityAlerts}
                onChange={(e) => setFormData({ ...formData, securityAlerts: e.target.checked })}
                className="w-5 h-5 rounded border-white/20 bg-white/5 text-primary focus:ring-primary focus:ring-2"
              />
            </label>

            <label className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10 cursor-pointer hover:bg-white/10 transition-colors">
              <div className="flex items-center gap-3">
                <CreditCard className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium text-foreground">Weekly Reports</p>
                  <p className="text-sm text-muted-foreground">Receive weekly summary reports</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={formData.weeklyReports}
                onChange={(e) => setFormData({ ...formData, weeklyReports: e.target.checked })}
                className="w-5 h-5 rounded border-white/20 bg-white/5 text-primary focus:ring-primary focus:ring-2"
              />
            </label>
          </div>
        </Card>
      </motion.div>

      {/* Account Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="flex flex-col sm:flex-row gap-4"
      >
        <Button
          variant="primary"
          size="lg"
          onClick={handleSave}
          disabled={isLoading}
          className="flex-1"
          glow
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="h-4 w-4 mr-2" />
              Save Changes
            </>
          )}
        </Button>

        <Button
          variant="secondary"
          size="lg"
          onClick={() => navigate('/billing')}
          className="flex-1"
        >
          <CreditCard className="h-4 w-4 mr-2" />
          Manage Billing
        </Button>

        <Button
          variant="destructive"
          size="lg"
          onClick={handleLogout}
          className="flex-1"
        >
          <LogOut className="h-4 w-4 mr-2" />
          Logout
        </Button>
      </motion.div>
    </div>
  )
}
