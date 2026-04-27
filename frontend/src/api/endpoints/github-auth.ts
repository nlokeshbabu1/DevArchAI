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
      // Use environment variable for API URL with fallback for development
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      
      // Use redirect URI from env if available, otherwise build from origin
      const redirectUri = import.meta.env.VITE_GITHUB_REDIRECT_URI || `${window.location.origin}/auth/github/callback`
      
      const response = await fetch(`${apiUrl}/api/v1/auth/github/url?redirect_uri=${encodeURIComponent(redirectUri)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data.oauth_url || null
    } catch (error: any) {
      // Fallback: try to build URL from env (for development)
      const clientId = import.meta.env.VITE_GITHUB_CLIENT_ID
      if (clientId) {
        const redirectUri = import.meta.env.VITE_GITHUB_REDIRECT_URI || `${window.location.origin}/auth/github/callback`
        const encodedRedirectUri = encodeURIComponent(redirectUri)
        const scope = encodeURIComponent(import.meta.env.VITE_GITHUB_OAUTH_SCOPE || 'user:email read:user')
        return `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${encodedRedirectUri}&scope=${scope}`
      }
      throw error
    }
  },

  /**
   * Exchange GitHub authorization code for JWT token
   */
  exchangeCodeForToken: async (code: string): Promise<GithubTokenResponse> => {
    try {
      // Use environment variable for API URL with fallback for development
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/auth/github/callback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
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
