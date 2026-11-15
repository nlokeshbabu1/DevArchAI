import apiClient from '../client'

export type IntegrationProvider = 'github' | 'gitlab' | 'aws' | 'azure' | 'bitbucket' | 'kubernetes' | 'eks'

export type IntegrationStatus = 'connected' | 'not_connected' | 'connecting' | 'pending_verification' | 'connection_error'

export interface IntegrationStatusResponse {
  github: boolean
  github_oauth?: boolean
  github_app_installed?: boolean
  github_repository_access?: boolean
  gitlab: boolean
  gitlab_oauth?: boolean
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
  connectionDetail?: string
}

export interface AuthContext {
  authProvider: 'github' | 'gitlab' | 'email'
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

function githubOAuthConnected(data: IntegrationStatusResponse): boolean {
  return data.github_oauth ?? false
}

function gitlabOAuthConnected(data: IntegrationStatusResponse): boolean {
  return data.gitlab_oauth ?? data.gitlab ?? false
}

function githubConnectionDetail(data: IntegrationStatusResponse): string | undefined {
  const oauth = githubOAuthConnected(data)
  const app = data.github_app_installed ?? false
  const repos = data.github_repository_access ?? false
  if (oauth) {
    return app ? 'OAuth linked · GitHub App installed' : 'OAuth identity linked'
  }
  if (app) {
    return 'GitHub App installed (OAuth not linked)'
  }
  if (repos) {
    return 'Repositories added manually (OAuth not linked)'
  }
  return undefined
}

function buildDefaultStatus(): IntegrationInfo[] {
  const providers: IntegrationProvider[] = ['github', 'gitlab', 'aws', 'azure', 'bitbucket', 'kubernetes', 'eks']

  return providers.map((provider) => {
    const meta = PROVIDER_META[provider]

    return {
      provider,
      connected: false,
      status: 'not_connected',
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
  getIntegrationStatus: async (): Promise<IntegrationStatusResponse> => {
    const response = await apiClient.get<IntegrationStatusResponse>('/integrations/status')
    return response.data
  },

  getStatus: async (_auth: AuthContext): Promise<IntegrationInfo[]> => {
    try {
      const data = await integrationsApi.getIntegrationStatus()
      const providers: IntegrationProvider[] = ['github', 'gitlab', 'aws', 'azure', 'bitbucket', 'kubernetes', 'eks']

      return providers.map((provider) => {
        const meta = PROVIDER_META[provider]
        let connected = data[provider] ?? false
        let status: IntegrationStatus = connected ? 'connected' : 'not_connected'
        let connectionDetail: string | undefined

        if (provider === 'github') {
          const oauth = githubOAuthConnected(data)
          const app = data.github_app_installed ?? false
          connected = oauth
          status = oauth ? 'connected' : app ? 'pending_verification' : 'not_connected'
          connectionDetail = githubConnectionDetail(data)
        } else if (provider === 'gitlab') {
          connected = gitlabOAuthConnected(data)
          status = connected ? 'connected' : 'not_connected'
          connectionDetail = connected ? 'OAuth identity linked' : undefined
        }

        return {
          provider,
          connected,
          status,
          label: meta.label,
          description: meta.description,
          features: meta.features,
          icon: meta.icon,
          connectType: meta.connectType,
          connectUrl: meta.connectUrl,
          modalType: meta.modalType,
          connectionDetail,
        }
      })
    } catch {
      return buildDefaultStatus()
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
