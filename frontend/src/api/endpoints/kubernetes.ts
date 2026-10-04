/**
 * Kubernetes integration API endpoints.
 */

import apiClient from '../client'

export interface PermissionInfo {
  resource: string
  granted: boolean
  error?: string | null
}

export interface KubernetesInfo {
  id: string
  name: string
  provider: string
  kind: string
  context_name?: string | null
  cluster_name?: string | null
  cluster_endpoint?: string | null
  aws_account_id?: string | null
  aws_region?: string | null
  eks_cluster_name?: string | null
  kubernetes_version?: string | null
  health_status?: string | null
  status: string
  is_active: boolean
  node_count?: number | null
  pod_count?: number | null
  namespace_count?: number | null
  deployment_count?: number | null
  ingress_count?: number | null
  error_message?: string | null
  permissions?: PermissionInfo[] | null
  created_at?: string | null
  updated_at?: string | null
}

export interface EksCluster {
  name: string
  region: string
  status: string
  version: string
  endpoint?: string
  arn?: string
}

export interface ClusterOverviewResponse {
  connection: KubernetesInfo
  overview: Record<string, unknown>
  health_score?: Record<string, unknown>
  version_advisor?: Record<string, unknown>
  collected_at?: string
}

export interface ClusterAIJob {
  id: string
  connection_id: string
  status: string
  analysis_type: string
  result?: Record<string, unknown> | null
  error_message?: string | null
  started_at?: string | null
  completed_at?: string | null
  created_at?: string | null
}

export const kubernetesApi = {
  connect: async (payload: { name: string; kubeconfig: string; context_name?: string }): Promise<KubernetesInfo> => {
    const response = await apiClient.post<KubernetesInfo>('/kubernetes/connect', payload)
    return response.data
  },

  test: async (payload: { name: string; kubeconfig: string; context_name?: string }): Promise<{
    ok: boolean
    status?: string
    kubernetes_version?: string
    cluster_name?: string
    missing_permissions?: string[]
    message?: string
  }> => {
    const response = await apiClient.post('/kubernetes/test', payload)
    return response.data
  },

  list: async (): Promise<KubernetesInfo[]> => {
    const response = await apiClient.get<KubernetesInfo[]>('/kubernetes/connections')
    return response.data
  },

  get: async (connectionId: string): Promise<KubernetesInfo> => {
    const response = await apiClient.get<KubernetesInfo>(`/kubernetes/connections/${connectionId}`)
    return response.data
  },

  disconnect: async (connectionId: string): Promise<{ message: string }> => {
    const response = await apiClient.delete(`/kubernetes/connections/${connectionId}`)
    return response.data
  },

  validate: async (connectionId: string): Promise<KubernetesInfo> => {
    const response = await apiClient.post<KubernetesInfo>(`/kubernetes/connections/${connectionId}/validate`)
    return response.data
  },

  refresh: async (connectionId: string): Promise<Record<string, unknown>> => {
    const response = await apiClient.post(`/kubernetes/connections/${connectionId}/refresh`)
    return response.data
  },

  overview: async (connectionId: string): Promise<ClusterOverviewResponse & { ai_job?: ClusterAIJob | null; security_findings?: Record<string, unknown>[] }> => {
    const response = await apiClient.get<ClusterOverviewResponse>(`/kubernetes/connections/${connectionId}/overview`)
    return response.data
  },

  nodes: async (connectionId: string): Promise<{ nodes: Record<string, unknown>[]; collected_at?: string }> => {
    const response = await apiClient.get(`/kubernetes/connections/${connectionId}/nodes`)
    return response.data
  },

  pods: async (connectionId: string, namespace?: string): Promise<{ pods: Record<string, unknown>[]; collected_at?: string }> => {
    const response = await apiClient.get(`/kubernetes/connections/${connectionId}/pods`, { params: namespace ? { namespace } : {} })
    return response.data
  },

  podDetail: async (connectionId: string, namespace: string, podName: string): Promise<{ pod: Record<string, unknown>; events: Record<string, unknown>[] }> => {
    const response = await apiClient.get(`/kubernetes/connections/${connectionId}/pods/${namespace}/${podName}`)
    return response.data
  },

  events: async (connectionId: string): Promise<{ events: Record<string, unknown>[]; collected_at?: string }> => {
    const response = await apiClient.get(`/kubernetes/connections/${connectionId}/events`)
    return response.data
  },

  securityScan: async (connectionId: string): Promise<Record<string, unknown>> => {
    const response = await apiClient.post(`/kubernetes/connections/${connectionId}/security-scan`)
    return response.data
  },

  healthScore: async (connectionId: string): Promise<Record<string, unknown>> => {
    const response = await apiClient.get(`/kubernetes/connections/${connectionId}/health-score`)
    return response.data
  },

  versionAdvisor: async (connectionId: string, targetVersion?: string): Promise<Record<string, unknown>> => {
    const response = await apiClient.get(`/kubernetes/connections/${connectionId}/version-advisor`, {
      params: targetVersion ? { target_version: targetVersion } : {},
    })
    return response.data
  },

  startUpgradeAnalysis: async (connectionId: string, targetVersion?: string): Promise<ClusterAIJob> => {
    const response = await apiClient.post<ClusterAIJob>(
      `/kubernetes/connections/${connectionId}/upgrade-analysis`,
      targetVersion ? { target_version: targetVersion } : {},
    )
    return response.data
  },

  getUpgradeAnalysis: async (connectionId: string, jobId: string): Promise<ClusterAIJob> => {
    const response = await apiClient.get<ClusterAIJob>(
      `/kubernetes/connections/${connectionId}/upgrade-analysis/${jobId}`,
    )
    return response.data
  },

  getAiAnalysisLatest: async (connectionId: string): Promise<ClusterAIJob | null> => {
    const response = await apiClient.get<ClusterAIJob | null>(`/kubernetes/connections/${connectionId}/ai-analysis/latest`)
    return response.data
  },

  namespaces: async (connectionId: string) => {
    const response = await apiClient.get(`/kubernetes/connections/${connectionId}/namespaces`)
    return response.data
  },

  deployments: async (connectionId: string) => {
    const response = await apiClient.get(`/kubernetes/connections/${connectionId}/deployments`)
    return response.data
  },

  services: async (connectionId: string) => {
    const response = await apiClient.get(`/kubernetes/connections/${connectionId}/services`)
    return response.data
  },

  ingresses: async (connectionId: string) => {
    const response = await apiClient.get(`/kubernetes/connections/${connectionId}/ingresses`)
    return response.data
  },

  startAiAnalysis: async (
    connectionId: string,
    options?: { question?: string; analysis_type?: string },
  ): Promise<ClusterAIJob> => {
    const response = await apiClient.post<ClusterAIJob>(
      `/kubernetes/connections/${connectionId}/ai-analysis`,
      options || {},
    )
    return response.data
  },

  getAiAnalysis: async (connectionId: string, jobId: string): Promise<ClusterAIJob> => {
    const response = await apiClient.get<ClusterAIJob>(`/kubernetes/connections/${connectionId}/ai-analysis/${jobId}`)
    return response.data
  },

  eksAwsAvailable: async (): Promise<{ available: boolean; account_id?: string; connection_id?: string; message?: string }> => {
    const response = await apiClient.get('/kubernetes/eks/aws-available')
    return response.data
  },

  listEksClusters: async (region: string): Promise<EksCluster[]> => {
    const response = await apiClient.get<EksCluster[]>('/kubernetes/eks/clusters', { params: { region } })
    return response.data
  },

  connectEks: async (payload: { cluster_name: string; region: string; name?: string }): Promise<KubernetesInfo> => {
    const response = await apiClient.post<KubernetesInfo>('/kubernetes/eks/connect', payload)
    return response.data
  },
}
