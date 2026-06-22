/**
 * Settings API endpoints
 */

import apiClient from '../client'

export interface ProfileData {
  id: string
  email: string
  username: string
  full_name?: string
  avatar_url?: string
  organization?: string
  role: string
  is_verified: boolean
  plan: string
  created_at?: string
  last_login_at?: string
  provider?: 'email' | 'github' | 'gitlab' | 'email+github' | 'email+gitlab'
  has_password?: boolean
}

export interface NotificationPrefs {
  email_notifications: boolean
  security_alerts: boolean
  weekly_reports: boolean
  product_updates: boolean
  scan_completion_alerts: boolean
  theme?: string
}

export interface SessionData {
  id: string
  device?: string
  ip_address?: string
  last_active?: string
  current: boolean
}

export interface ApiKeyData {
  id: string
  name?: string
  masked_key?: string
  created_at?: string
}

export interface CreateApiKeyResponse {
  id: string
  name?: string
  masked_key?: string
  full_key: string
  created_at?: string
}

export interface ApiMessageResponse {
  message: string
  success: boolean
}

export const settingsApi = {
  getProfile: async (): Promise<ProfileData> => {
    const response = await apiClient.get<ProfileData>('/settings/profile')
    return response.data
  },

  updateProfile: async (data: { full_name?: string; username?: string }): Promise<ProfileData> => {
    const response = await apiClient.put<ProfileData>('/settings/profile', data)
    return response.data
  },

  changePassword: async (data: { current_password: string; new_password: string }): Promise<ApiMessageResponse> => {
    const response = await apiClient.put<ApiMessageResponse>('/settings/password', data)
    return response.data
  },

  getPreferences: async (): Promise<NotificationPrefs> => {
    const response = await apiClient.get<NotificationPrefs>('/settings/preferences')
    return response.data
  },

  updatePreferences: async (data: NotificationPrefs): Promise<NotificationPrefs> => {
    const response = await apiClient.put<NotificationPrefs>('/settings/preferences', data)
    return response.data
  },

  getSessions: async (): Promise<SessionData[]> => {
    const response = await apiClient.get<SessionData[]>('/settings/sessions')
    return response.data
  },

  revokeSession: async (sessionId: string): Promise<ApiMessageResponse> => {
    const response = await apiClient.delete<ApiMessageResponse>(`/settings/sessions/${sessionId}`)
    return response.data
  },

  getApiKeys: async (): Promise<ApiKeyData[]> => {
    const response = await apiClient.get<ApiKeyData[]>('/settings/api-keys')
    return response.data
  },

  createApiKey: async (name?: string): Promise<CreateApiKeyResponse> => {
    const response = await apiClient.post<CreateApiKeyResponse>('/settings/api-keys', name ? { name } : {})
    return response.data
  },

  revokeApiKey: async (keyId: string): Promise<ApiMessageResponse> => {
    const response = await apiClient.delete<ApiMessageResponse>(`/settings/api-keys/${keyId}`)
    return response.data
  },

  deleteAccount: async (password: string): Promise<ApiMessageResponse> => {
    const response = await apiClient.delete<ApiMessageResponse>('/settings/account', { data: { password } })
    return response.data
  },
}
