/**
 * Kubernetes integration API endpoints.
 */

import apiClient from '../client'

export interface KubernetesInfo {
  id: string
  name: string
  provider: string
  kind: string
  context_name?: string | null
  cluster_endpoint?: string | null
  aws_account_id?: string | null
  aws_region?: string | null
  eks_cluster_name?: string | null
  status: string
  is_active: boolean
  created_at?: string | null
}

export interface EksCluster {
  name: string
  region: string
  status: string
  version: string
  endpoint?: string
  arn?: string
}

export const kubernetesApi = {
  connect: async (payload: { name: string; kubeconfig: string; context_name?: string }): Promise<KubernetesInfo> => {
    const response = await apiClient.post<KubernetesInfo>('/kubernetes/connect', payload)
    return response.data
  },

  test: async (payload: { name: string; kubeconfig: string; context_name?: string }): Promise<{ ok: boolean; message?: string }> => {
    const response = await apiClient.post('/kubernetes/test', payload)
    return response.data
  },

  list: async (): Promise<KubernetesInfo[]> => {
    const response = await apiClient.get<KubernetesInfo[]>('/kubernetes/connections')
    return response.data
  },

  disconnect: async (connectionId: string): Promise<{ message: string }> => {
    const response = await apiClient.delete(`/kubernetes/connections/${connectionId}`)
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
