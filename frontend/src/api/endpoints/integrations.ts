import apiClient from '../client'

export type IntegrationProvider = 'github' | 'gitlab' | 'aws' | 'azure' | 'bitbucket'

export type IntegrationStatus = 'connected' | 'not_connected' | 'connecting' | 'pending_verification' | 'connection_error'

export interface IntegrationStatusResponse {
  github: boolean
  gitlab: boolean
  aws: boolean
  azure: boolean
  bitbucket: boolean
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
  modalType?: 'aws' | 'azure'
}

export interface AuthContext {
  authProvider: 'github' | 'gitlab' | 'email'
}

const AUTH_PROVIDER_MAP: Record<string, IntegrationProvider> = {
  github: 'github',
  gitlab: 'gitlab',
}

const PROVIDER_META: Record<IntegrationProvider, { label: string; description: string; features: string[]; icon: string; connectType: 'oauth' | 'modal' | 'none'; connectUrl?: string; modalType?: 'aws' | 'azure' }> = {
  github: {
    label: 'GitHub',
    description: 'Connect GitHub repositories for automated scanning',
    features: ['Repository import', 'PR comments', 'Status checks', 'Auto-scan on push'],
    icon: 'github',
    connectType: 'oauth',
    connectUrl: '/api/auth/github',
  },
  gitlab: {
    label: 'GitLab',
    description: 'CI/CD pipeline integration and MR scanning',
    features: ['Repository import', 'CI/CD integration', 'MR comments', 'Pipeline status'],
    icon: 'gitlab',
    connectType: 'oauth',
    connectUrl: '/api/auth/gitlab',
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
    connectUrl: '/api/auth/bitbucket',
  },
}

function buildDefaultStatus(authProvider: 'github' | 'gitlab' | 'email'): IntegrationInfo[] {
  const providers: IntegrationProvider[] = ['github', 'gitlab', 'aws', 'azure', 'bitbucket']

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
      const providers: IntegrationProvider[] = ['github', 'gitlab', 'aws', 'azure', 'bitbucket']
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
}
