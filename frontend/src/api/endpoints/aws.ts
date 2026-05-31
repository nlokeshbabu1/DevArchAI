import { api } from '../../lib/api'

export interface AwsAccount {
  id: string
  account_id: string
  account_alias?: string | null
  connection_type: string
  default_region: string
  is_active: boolean
  scan_status: string
  scan_progress: number
  last_error?: string | null
  last_scanned_at?: string | null
  created_at: string
}

export interface AwsOverview {
  account: AwsAccount
  inventory_summary: Record<string, number>
  severity_counts: Record<string, number>
  security_score: number
  cost_score: number
  estimated_monthly_savings: number
  posture_grade?: string
  last_sync?: string | null
  scan_duration_seconds?: number | null
  regions_scanned?: string[]
  aws_api_health?: string
  resource_coverage?: number
  queue_status?: string
  totals?: {
    resources: number
    findings: number
    recommendations: number
  }
  trend_data?: {
    security: Array<{ timestamp: string; critical: number; high: number; medium: number; low: number }>
    cost: Array<{ timestamp: string; estimated_monthly_savings: number; recommendations: number }>
    resources: Array<{ timestamp: string; total: number }>
  }
}

export interface AwsFinding {
  id: string
  category?: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  title: string
  description: string
  resource_type?: string | null
  resource_id?: string | null
  region?: string | null
  recommendation?: string | null
  metadata_json?: Record<string, unknown>
}

export interface AwsFindingExplanation {
  id: string
  title: string
  severity: string
  summary: string
  risk: string
  attack_scenario: string
  fix_steps: string[]
  cli_commands: string[]
  terraform_example: string
  best_practices: string[]
}

export interface AwsCostRecommendation {
  id: string
  title: string
  description: string
  recommendation_type: string
  resource_type?: string | null
  resource_id?: string | null
  region?: string | null
  estimated_monthly_savings: number
}

export interface AwsInventoryResponse {
  account: AwsAccount
  summary: Record<string, number>
  items: Array<{ id: string; resource_type: string; resource_id: string; name?: string | null; region?: string | null }>
}

export const awsApi = {
  connect: (payload: {
    access_key_id: string
    secret_access_key: string
    default_region: string
    account_alias?: string
  }) => api.post('/aws/connect', payload),
  accounts: async () => (await api.get<AwsAccount[]>('/aws/accounts')).data,
  scan: async (accountId: string) => (await api.post<AwsAccount>(`/aws/accounts/${accountId}/scan`)).data,
  disconnect: async (accountId: string) => (await api.delete(`/aws/accounts/${accountId}`)).data,
  overview: async (accountId?: string) => (await api.get<AwsOverview>('/aws/overview', { params: { account_id: accountId } })).data,
  inventory: async (accountId?: string) => (await api.get<AwsInventoryResponse>('/aws/inventory', { params: { account_id: accountId } })).data,
  security: async (accountId?: string) => (await api.get<{ score: number; items: AwsFinding[] }>('/aws/security', { params: { account_id: accountId } })).data,
  cost: async (accountId?: string) => (await api.get<{ score: number; estimated_monthly_savings: number; items: AwsCostRecommendation[] }>('/aws/cost', { params: { account_id: accountId } })).data,
  iamAnalysis: async (accountId?: string) => (await api.get<{ total: number; items: AwsFinding[] }>('/aws/iam-analysis', { params: { account_id: accountId } })).data,
  explainFinding: async (findingId: string) => (await api.get<AwsFindingExplanation>(`/aws/findings/${findingId}/explain`)).data,
}
