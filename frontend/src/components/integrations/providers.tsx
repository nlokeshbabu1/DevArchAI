import type { IntegrationCategory, IntegrationMeta, ConnectionStatus } from './types'

const STATUS: Record<string, ConnectionStatus> = {
  NC: 'not_connected',
  CS: 'coming_soon',
}

export const buildCategories = (opts: {
  githubStatus: ConnectionStatus
  gitlabStatus: ConnectionStatus
  bitbucketStatus: ConnectionStatus
  awsStatus: ConnectionStatus
  kubernetesStatus: ConnectionStatus
  eksStatus: ConnectionStatus
  kubernetesAccount?: string
  eksAccount?: string
  awsAccountId?: string
  awsResourceCount?: number
  awsSecurityScore?: number
  awsLastScan?: string
  onConnect: (id: string) => void
  onManage: (id: string) => void
  onNotify: (id: string) => void
}): IntegrationCategory[] => {
  const { onConnect, onManage, onNotify } = opts

  const repos: IntegrationMeta[] = [
    {
      id: 'github',
      name: 'GitHub',
      description: 'Repository import, PR comments, status checks, auto-scan on push.',
      icon: 'github',
      category: 'repositories',
      status: opts.githubStatus,
      features: ['Repository import', 'PR comments', 'Status checks', 'Auto-scan on push'],
    },
    {
      id: 'gitlab',
      name: 'GitLab',
      description: 'CI/CD pipeline integration, MR scanning, pipeline status.',
      icon: 'gitlab',
      category: 'repositories',
      status: opts.gitlabStatus,
      features: ['Repository import', 'CI/CD integration', 'MR comments', 'Pipeline status'],
    },
    {
      id: 'bitbucket',
      name: 'Bitbucket',
      description: 'PR scanning, commit checks, pipeline integration.',
      icon: 'bitbucket',
      category: 'repositories',
      status: opts.bitbucketStatus,
      features: ['PR scanning', 'Commit checks', 'Pipeline integration'],
    },
  ]

  const cloud: IntegrationMeta[] = [
    {
      id: 'aws',
      name: 'AWS',
      description: 'Infrastructure security scanning across 15+ AWS services.',
      icon: 'aws',
      category: 'cloud',
      status: opts.awsStatus,
      connectedAccount: opts.awsAccountId,
      extraStats: opts.awsResourceCount ? {
        Resources: opts.awsResourceCount.toLocaleString(),
        'Security Score': opts.awsSecurityScore ? `${opts.awsSecurityScore}/100` : '—',
      } : undefined,
      lastScan: opts.awsLastScan,
    },
    {
      id: 'azure',
      name: 'Azure',
      description: 'Resource scanning, policy compliance, Defender for Cloud integration.',
      icon: 'azure',
      category: 'cloud',
      status: STATUS.CS,
    },
    {
      id: 'gcp',
      name: 'Google Cloud',
      description: 'Security Command Center, Cloud Asset Inventory scanning.',
      icon: 'gcp',
      category: 'cloud',
      status: STATUS.CS,
    },
  ]

  const containers: IntegrationMeta[] = [
    { id: 'kubernetes', name: 'Kubernetes', description: 'Cluster scanning, RBAC analysis, manifest validation.', icon: 'kubernetes', category: 'containers', status: opts.kubernetesStatus, connectedAccount: opts.kubernetesAccount },
    { id: 'eks', name: 'EKS', description: 'Managed Kubernetes security scanning.', icon: 'aws', category: 'containers', status: opts.eksStatus, connectedAccount: opts.eksAccount },
    { id: 'aks', name: 'AKS', description: 'Azure Kubernetes security analysis.', icon: 'azure', category: 'containers', status: STATUS.CS },
    { id: 'gke', name: 'GKE', description: 'Google Kubernetes security scanning.', icon: 'gcp', category: 'containers', status: STATUS.CS },
  ]

  const notifications: IntegrationMeta[] = [
    { id: 'slack', name: 'Slack', description: 'Alert delivery, scan notifications, team channels.', icon: 'slack', category: 'notifications', status: STATUS.NC },
    { id: 'teams', name: 'Microsoft Teams', description: 'Security alerts and compliance reports.', icon: 'teams', category: 'notifications', status: STATUS.CS },
    { id: 'discord', name: 'Discord', description: 'Webhook notifications for scan events.', icon: 'discord', category: 'notifications', status: STATUS.CS },
    { id: 'pagerduty', name: 'PagerDuty', description: 'Critical finding escalation and incident management.', icon: 'pagerduty', category: 'notifications', status: STATUS.CS },
  ]

  return [
    {
      id: 'repositories',
      title: 'Repositories',
      description: 'Connect your source code providers for automated scanning.',
      icon: null,
      providers: repos,
    },
    {
      id: 'cloud',
      title: 'Cloud Infrastructure',
      description: 'Connect cloud accounts for infrastructure security scanning.',
      icon: null,
      providers: cloud,
    },
    {
      id: 'containers',
      title: 'Container Platforms',
      description: 'Cluster and orchestration platform scanning.',
      icon: null,
      providers: containers,
    },
    {
      id: 'notifications',
      title: 'Notifications',
      description: 'Alert delivery and incident management.',
      icon: null,
      providers: notifications,
    },
  ]
}
