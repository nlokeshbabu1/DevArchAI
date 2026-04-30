/**
 * GitHub OAuth Authentication
 */

import apiClient from '../client'

export interface GithubCallbackRequest {
  code: string
}

export interface GithubTokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: {
    id: string
    email: string
    username: string
    avatar_url?: string
    is_active?: boolean
    is_verified?: boolean
    role?: string
    current_org_id?: string
  }
}

export interface GithubOAuthUrlResponse {
  oauth_url: string | null
  error?: string
  message?: string
}

export const githubAuthApi = {
  /**
   * Get GitHub OAuth authorization URL from backend
   */
  getAuthorizationUrl: async (): Promise<string | null> => {
    try {
      const response = await apiClient.get<GithubOAuthUrlResponse>('/auth/github/url')
      return response.data.oauth_url || null
    } catch (error: any) {
      // Fallback: try to build URL from env (for development)
      const clientId = import.meta.env.VITE_GITHUB_CLIENT_ID
      if (clientId) {
        const redirectUri = encodeURIComponent(`${window.location.origin}/auth/github/callback`)
        const scope = encodeURIComponent(import.meta.env.VITE_GITHUB_OAUTH_SCOPE || 'user:email read:user')
        return `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=${scope}`
      }
      throw error
    }
  },

  /**
   * Exchange GitHub authorization code for JWT token
   */
  exchangeCodeForToken: async (code: string): Promise<GithubTokenResponse> => {
    try {
      const response = await apiClient.post<GithubTokenResponse>('/auth/github/callback', { code })
      return response.data
    } catch (error: any) {
      throw error
    }
  },

  /**
   * Get GitHub user info from token
   */
  getUserInfo: async (): Promise<any> => {
    const response = await apiClient.get('/auth/github/user')
    return response.data
  },
}
