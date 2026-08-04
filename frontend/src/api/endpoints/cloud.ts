import { api } from '../../lib/api'

export interface CloudConnectPayload {
  provider: 'aws' | 'azure' | 'gcp' | 'oracle'
  account_id: string
  role_arn: string
  external_id: string
  regions: string[]
  connection_name?: string
}

export interface CloudConnection {
  id: string
  provider: string
  account_id: string
  role_arn: string
  connection_name: string
  status: string
  regions: string[]
  last_scanned_at: string | null
  scan_status: string
  resource_count: number
  finding_count: number
  security_score: number | null
  estimated_monthly_cost: number | null
  created_at: string
  updated_at: string
}

export interface CloudScanSession {
  id: string
  connection_id: string
  status: string
  progress: number
  current_stage: string
  stages_completed: string[]
  stages_total: number
  resources_scanned: number
  findings_count: number
  error: string | null
  started_at: string | null
  finished_at: string | null
  duration_seconds: number | null
  created_at: string | null
}

export interface CloudResourceSummary {
  total: number
  by_service: Record<string, number>
  by_status: Record<string, number>
  by_region: Record<string, number>
  total_monthly_cost: number
}

export interface CloudFindingSummary {
  total: number
  by_severity: Record<string, number>
  by_category: Record<string, number>
  by_service: Record<string, number>
}

export interface CloudCostSummary {
  total: number
  total_monthly_savings: number
  by_service: Record<string, number>
  by_priority: Record<string, number>
}

export interface CloudComplianceResult {
  id: string
  framework: string
  total_controls: number
  passed: number
  failed: number
  warnings: number
  not_applicable: number
  score: number
  last_checked: string | null
  details: Record<string, unknown>
  provider: string
  created_at: string | null
}

export interface CloudOverview {
  connection: CloudConnection
  resource_summary: CloudResourceSummary
  finding_summary: CloudFindingSummary
  cost_summary: CloudCostSummary
  compliance_results: CloudComplianceResult[]
  ai_recommendation_summary: CloudAIRecommendationSummary
  security_score: number
  estimated_monthly_cost: number
}

export interface CloudResource {
  id: string
  service: string
  resource_id: string
  resource_name: string
  resource_type: string
  region: string
  status: string
  configuration: Record<string, unknown> | null
  tags: Record<string, string> | null
  cost_monthly: number | null
}

export interface CloudFinding {
  id: string
  category: string
  severity: string
  title: string
  description: string
  rule_id: string | null
  resource_type: string | null
  resource_id: string | null
  region: string
  service: string
  compliance_frameworks: string[] | null
  remediation: string | null
  evidence: Record<string, unknown> | null
  status: string
  created_at: string | null
}

export interface CloudCostRecommendation {
  id: string
  title: string
  description: string
  monthly_savings: number
  current_cost: number
  priority: string
  category: string
  service: string
  resource_type: string | null
  resource_id: string | null
  region: string
  recommendation_type: string
  estimated_impact: string
}

export interface CloudAIRecommendation {
  recommendation_id: string
  connection_id: string
  scan_id: string | null
  provider: string
  service: string
  resource_id: string
  resource_name: string
  category: string
  severity: string
  title: string
  summary: string
  technical_explanation: string
  business_impact: string
  estimated_monthly_savings: number
  estimated_risk_reduction: number
  aws_cli_fix: string | null
  terraform_fix: string | null
  cloudformation_fix: string | null
  console_steps: string[] | null
  official_documentation_url: string | null
  recommendation_source: string
  status: string
  created_at: string | null
}

export interface CloudAIRecommendationSummary {
  total: number
  by_severity: Record<string, number>
  by_category: Record<string, number>
  by_status: Record<string, number>
  total_monthly_savings: number
  avg_risk_reduction: number
  critical_count: number
}

export interface CloudWSMessage {
  type: string
  data: Record<string, unknown>
}

// ── Jira Integration ────────────────────────────────────────

export interface CreateJiraTicketPayload {
  jira_url: string
  email: string
  api_token: string
  project_key: string
  summary: string
  description: string
  issue_type?: string
}

export interface JiraTicketResponse {
  success: boolean
  ticket_url: string | null
  ticket_key: string | null
  error: string | null
}

// ── Scan Comparison ─────────────────────────────────────────

export interface ScanComparisonDelta {
  added: number
  removed: number
  changed: number
}

export interface ScanComparisonSection {
  resources: ScanComparisonDelta
  findings: ScanComparisonDelta
  cost_recommendations: ScanComparisonDelta
  compliance: ScanComparisonDelta
  ai_recommendations: ScanComparisonDelta
}

export interface ScanComparisonResponse {
  connection_id: string
  old_scan_id: string | null
  new_scan_id: string | null
  old_scan: CloudScanSession | null
  new_scan: CloudScanSession | null
  deltas: ScanComparisonSection
}

// ── Wizard interfaces ──────────────────────────────────────

export interface WizardInitPayload {
  account_id: string
  connection_name?: string
}

export interface WizardInitResponse {
  wizard_id: string
  account_id: string
  connection_name: string
  external_id: string
  stack_name: string
  role_name: string
  cloudformation_url: string
  template_url: string
  status: string
}

export interface WizardStatusResponse {
  wizard_id: string
  account_id: string
  connection_name: string
  status: string
  role_arn: string | null
  regions: string[]
  error_message: string | null
  verified_account_id: string | null
  verified_permissions: string[]
}

export interface WizardVerifyResponse {
  success: boolean
  account_id: string | null
  role_arn: string | null
  permissions: {
    available: string[]
    unavailable: string[]
    total: number
  }
  regions: string[]
  error: string | null
}

export interface WizardCompletePayload {
  wizard_id: string
  regions?: string[]
}

export const cloudApi = {
  connect: async (payload: CloudConnectPayload): Promise<{ connection: CloudConnection; message: string }> => {
    const res = await api.post('/cloud/connect', payload)
    return res.data
  },

  connections: async (): Promise<CloudConnection[]> => {
    const res = await api.get('/cloud/connections')
    return res.data
  },

  deleteConnection: async (connectionId: string): Promise<{ message: string }> => {
    const res = await api.delete(`/cloud/connections/${connectionId}`)
    return res.data
  },

  triggerScan: async (connectionId: string): Promise<{ status: string }> => {
    const res = await api.post(`/cloud/connections/${connectionId}/scan`)
    return res.data
  },

  overview: async (connectionId: string): Promise<CloudOverview> => {
    const res = await api.get(`/cloud/connections/${connectionId}/overview`)
    return res.data
  },

  resources: async (
    connectionId: string,
    params?: { service?: string; region?: string },
  ): Promise<{ resources: CloudResource[]; total: number }> => {
    const res = await api.get(`/cloud/connections/${connectionId}/resources`, { params })
    return res.data
  },

  findings: async (
    connectionId: string,
    params?: { severity?: string; category?: string; service?: string },
  ): Promise<{ findings: CloudFinding[]; total: number }> => {
    const res = await api.get(`/cloud/connections/${connectionId}/findings`, { params })
    return res.data
  },

  costs: async (
    connectionId: string,
    params?: { priority?: string },
  ): Promise<{ recommendations: CloudCostRecommendation[]; total: number; total_monthly_savings: number }> => {
    const res = await api.get(`/cloud/connections/${connectionId}/costs`, { params })
    return res.data
  },

  compliance: async (
    connectionId: string,
  ): Promise<{ results: CloudComplianceResult[]; total_frameworks: number; average_score: number }> => {
    const res = await api.get(`/cloud/connections/${connectionId}/compliance`)
    return res.data
  },

  // ── AI Recommendations ──────────────────────────────────────

  recommendations: async (
    connectionId: string,
    params?: { severity?: string; category?: string; status?: string; search?: string },
  ): Promise<{ recommendations: CloudAIRecommendation[]; total: number }> => {
    const res = await api.get(`/cloud/connections/${connectionId}/recommendations`, { params })
    return res.data
  },

  recommendationsSummary: async (connectionId: string): Promise<CloudAIRecommendationSummary> => {
    const res = await api.get(`/cloud/connections/${connectionId}/recommendations/summary`)
    return res.data
  },

  updateRecommendationStatus: async (
    connectionId: string,
    recommendationId: string,
    status: string,
  ): Promise<{ status: string }> => {
    const res = await api.patch(`/cloud/connections/${connectionId}/recommendations/${recommendationId}/status`, null, {
      params: { status },
    })
    return res.data
  },

  // ── Jira ──

  createJiraTicket: async (
    connectionId: string,
    recommendationId: string,
    payload: CreateJiraTicketPayload,
  ): Promise<JiraTicketResponse> => {
    const res = await api.post(`/cloud/connections/${connectionId}/recommendations/${recommendationId}/jira`, payload)
    return res.data
  },

  // ── Export PDF ──

  exportRecommendationsPdf: async (connectionId: string): Promise<Blob> => {
    const res = await api.post(`/cloud/connections/${connectionId}/recommendations/export-pdf`, null, {
      responseType: 'blob',
    })
    return res.data
  },

  // ── Scan Comparison ──

  compareScans: async (
    connectionId: string,
    params?: { old_scan_id?: string; new_scan_id?: string },
  ): Promise<ScanComparisonResponse> => {
    const res = await api.get(`/cloud/connections/${connectionId}/compare`, { params })
    return res.data
  },

  // ── Wizard methods ────────────────────────────────────────

  initWizard: async (payload: WizardInitPayload): Promise<WizardInitResponse> => {
    const res = await api.post('/cloud/aws/wizard/init', payload)
    return res.data
  },

  wizardStatus: async (wizardId: string): Promise<WizardStatusResponse> => {
    const res = await api.get(`/cloud/aws/wizard/${wizardId}/status`)
    return res.data
  },

  verifyWizard: async (wizardId: string): Promise<WizardVerifyResponse> => {
    const res = await api.post(`/cloud/aws/wizard/${wizardId}/verify`)
    return res.data
  },

  completeWizard: async (
    wizardId: string,
    payload?: WizardCompletePayload,
  ): Promise<{ connection: CloudConnection; message: string }> => {
    const res = await api.post(`/cloud/aws/wizard/${wizardId}/complete`, {
      wizard_id: wizardId,
      regions: payload?.regions,
    })
    return res.data
  },
}
