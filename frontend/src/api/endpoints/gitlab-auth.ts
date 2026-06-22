import apiClient from '../client'

export interface GitlabCallbackRequest {
  code: string
  state?: string
}

export interface GitlabTokenResponse {
  access_token: string
  refresh_token?: string
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
    has_github?: boolean
    has_gitlab?: boolean
  }
}

export interface GitlabOAuthUrlResponse {
  oauth_url: string | null
  error?: string
  message?: string
}

export const gitlabAuthApi = {
  getAuthorizationUrl: async (): Promise<string | null> => {
    try {
      const response = await apiClient.get<GitlabOAuthUrlResponse>('/auth/gitlab/url')
      return response.data.oauth_url || null
    } catch {
      throw new Error('GitLab OAuth is not configured')
    }
  },

  exchangeCodeForToken: async (code: string, state?: string): Promise<GitlabTokenResponse> => {
    const response = await apiClient.post<GitlabTokenResponse>('/auth/gitlab/callback', { code, state })
    return response.data
  },
}
