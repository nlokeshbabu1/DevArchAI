import apiClient from '../client'

export type IntegrationProvider = 'github' | 'gitlab' | 'aws' | 'azure' | 'bitbucket' | 'kubernetes' | 'eks'

export type IntegrationStatus = 'connected' | 'not_connected' | 'connecting' | 'pending_verification' | 'connection_error'

export interface IntegrationStatusResponse {
  github: boolean
  gitlab: boolean
  aws: boolean
  azure: boolean
  bitbucket: boolean
  kubernetes: boolean
  eks: boolean
}

export interface IntegrationInfo {
  provider: IntegrationProvider
  connected: boolean
  status: IntegrationStatus
  label: string
  description: string
  features: string[]
  icon: string
  connectType: 'oauth' | 'modal' | 'none'
  connectUrl?: string
  modalType?: 'aws' | 'azure' | 'kubernetes' | 'eks'
}

export interface AuthContext {
  authProvider: 'github' | 'gitlab' | 'email'
}

const AUTH_PROVIDER_MAP: Record<string, IntegrationProvider> = {
  github: 'github',
  gitlab: 'gitlab',
}

const PROVIDER_META: Record<IntegrationProvider, { label: string; description: string; features: string[]; icon: string; connectType: 'oauth' | 'modal' | 'none'; connectUrl?: string; modalType?: 'aws' | 'azure' | 'kubernetes' | 'eks' }> = {
  github: {
    label: 'GitHub',
    description: 'Connect GitHub repositories for automated scanning',
    features: ['Repository import', 'PR comments', 'Status checks', 'Auto-scan on push'],
    icon: 'github',
    connectType: 'oauth',
    connectUrl: '/api/v1/integrations/github/url',
    modalType: undefined,
  },
  gitlab: {
    label: 'GitLab',
    description: 'CI/CD pipeline integration and MR scanning',
    features: ['Repository import', 'CI/CD integration', 'MR comments', 'Pipeline status'],
    icon: 'gitlab',
    connectType: 'oauth',
    connectUrl: '/api/v1/integrations/gitlab/url',
    modalType: undefined,
  },
  aws: {
    label: 'AWS',
    description: 'Scan AWS infrastructure and CloudFormation templates',
    features: ['Resource scanning', 'Compliance checks', 'Cost optimization'],
    icon: 'cloud',
    connectType: 'modal',
    modalType: 'aws',
  },
  azure: {
    label: 'Azure',
    description: 'Connect Azure subscriptions for infrastructure analysis',
    features: ['Resource scanning', 'Policy compliance', 'Security insights'],
    icon: 'server',
    connectType: 'modal',
    modalType: 'azure',
  },
  bitbucket: {
    label: 'Bitbucket',
    description: 'Integrate with Bitbucket repositories',
    features: ['PR scanning', 'Commit checks', 'Pipeline integration'],
    icon: 'link',
    connectType: 'oauth',
    connectUrl: '/api/v1/integrations/bitbucket/url',
    modalType: undefined,
  },
  kubernetes: {
    label: 'Kubernetes',
    description: 'Connect Kubernetes clusters for security scanning',
    features: ['Cluster scanning', 'RBAC analysis', 'Manifest validation'],
    icon: 'kubernetes',
    connectType: 'modal',
    modalType: 'kubernetes',
  },
  eks: {
    label: 'EKS',
    description: 'Discover and connect Amazon EKS clusters',
    features: ['Cluster discovery', 'AWS-powered', 'Managed scanning'],
    icon: 'aws',
    connectType: 'modal',
    modalType: 'eks',
  },
}

function buildDefaultStatus(authProvider: 'github' | 'gitlab' | 'email'): IntegrationInfo[] {
  const providers: IntegrationProvider[] = ['github', 'gitlab', 'aws', 'azure', 'bitbucket', 'kubernetes', 'eks']

  return providers.map((provider) => {
    const meta = PROVIDER_META[provider]
    const isAuthMatched = authProvider !== 'email' && AUTH_PROVIDER_MAP[authProvider] === provider
    const connected = isAuthMatched

    return {
      provider,
      connected,
      status: connected ? 'connected' : 'not_connected',
      label: meta.label,
      description: meta.description,
      features: meta.features,
      icon: meta.icon,
      connectType: meta.connectType,
      connectUrl: meta.connectUrl,
      modalType: meta.modalType,
    }
  })
}

export const integrationsApi = {
  getStatus: async (auth: AuthContext): Promise<IntegrationInfo[]> => {
    try {
      const response = await apiClient.get<IntegrationStatusResponse>('/integrations/status')
      const data = response.data
      const providers: IntegrationProvider[] = ['github', 'gitlab', 'aws', 'azure', 'bitbucket', 'kubernetes', 'eks']
      const { authProvider } = auth

      return providers.map((provider) => {
        const meta = PROVIDER_META[provider]
        const backendConnected = data[provider] ?? false
        const isAuthMatched = authProvider !== 'email' && AUTH_PROVIDER_MAP[authProvider] === provider

        // Auth provider's matching integration is always connected
        // Other integrations require backend verification
        const connected = isAuthMatched || backendConnected

        return {
          provider,
          connected,
          status: connected ? 'connected' : 'not_connected',
          label: meta.label,
          description: meta.description,
          features: meta.features,
          icon: meta.icon,
          connectType: meta.connectType,
          connectUrl: meta.connectUrl,
          modalType: meta.modalType,
        }
      })
    } catch {
      return buildDefaultStatus(auth.authProvider)
    }
  },

  /**
   * Get an OAuth authorization URL that attaches the provider to the current user.
   */
  getOAuthUrl: async (provider: 'github' | 'gitlab'): Promise<{ oauth_url: string | null; state?: string; error?: string }> => {
    const response = await apiClient.get<{ oauth_url: string | null; state?: string; error?: string }>(
      `/integrations/${provider}/url`,
    )
    return response.data
  },

  /**
   * Exchange an OAuth code to attach the provider to the current user.
   */
  exchangeOAuthCode: async (
    provider: 'github' | 'gitlab',
    code: string,
    state?: string,
  ): Promise<{ connected: boolean; provider: string; account?: string; has_github?: boolean; has_gitlab?: boolean }> => {
    const response = await apiClient.post(`/integrations/${provider}/callback`, { code, state })
    return response.data
  },

  /**
   * Disconnect an OAuth provider from the current user.
   */
  disconnectOAuth: async (provider: 'github' | 'gitlab'): Promise<{ connected: boolean; provider: string }> => {
    const response = await apiClient.post(`/integrations/${provider}/disconnect`)
    return response.data
  },
}
