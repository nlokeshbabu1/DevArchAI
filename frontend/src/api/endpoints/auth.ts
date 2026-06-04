/**
 * Authentication API endpoints
 */

import apiClient from '../client'

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  username: string
  password: string
  organization_name?: string
  country?: string  // ISO 3166-1 alpha-2 country code (default: "US")
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserResponse {
  id: string
  email: string
  username: string
  full_name?: string
  avatar_url?: string
  is_active: boolean
  is_verified: boolean
  role: string
  current_org_id?: string
  created_at?: string
  updated_at?: string
  last_login_at?: string
}

export interface SessionInfo {
  id: string
  device_name?: string
  browser?: string
  ip_address?: string
  location?: string
  created_at: string
  last_active_at: string
  expires_at?: string
  is_current: boolean
}

export const authApi = {
  /**
   * Register a new user
   */
  register: async (data: RegisterRequest): Promise<UserResponse> => {
    const response = await apiClient.post<UserResponse>('/auth/register', data)
    return response.data
  },

  /**
   * Login user
   */
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/login', data)
    return response.data
  },

  /**
   * Get current user info
   */
  getCurrentUser: async (): Promise<UserResponse> => {
    const response = await apiClient.get<UserResponse>('/auth/me')
    return response.data
  },

  /**
   * Update current user profile
   */
  updateProfile: async (data: Partial<UserResponse>): Promise<UserResponse> => {
    const response = await apiClient.put<UserResponse>('/auth/me', data)
    return response.data
  },

  /**
   * Create API key
   */
  createApiKey: async (): Promise<{ api_key: string; api_key_prefix: string; created_at: string }> => {
    const response = await apiClient.post('/auth/api-key')
    return response.data
  },

  /**
   * Revoke API key
   */
  revokeApiKey: async (): Promise<{ message: string }> => {
    const response = await apiClient.delete('/auth/api-key')
    return response.data
  },

  /**
   * Server-side logout (blacklists tokens, revokes session)
   */
  logout: async (): Promise<{ message: string }> => {
    const response = await apiClient.post('/auth/logout')
    return response.data
  },

  /**
   * List all active sessions
   */
  getSessions: async (): Promise<SessionInfo[]> => {
    const response = await apiClient.get<SessionInfo[]>('/auth/sessions')
    return response.data
  },

  /**
   * Revoke a specific session
   */
  revokeSession: async (sessionId: string): Promise<{ message: string }> => {
    const response = await apiClient.delete(`/auth/sessions/${sessionId}`)
    return response.data
  },

  /**
   * Revoke all other sessions
   */
  revokeAllSessions: async (): Promise<{ message: string; revoked_count: number }> => {
    const response = await apiClient.post('/auth/revoke-all')
    return response.data
  },
}
