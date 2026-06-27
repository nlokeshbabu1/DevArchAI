export interface AnalysisReport {
  id: string
  repository_url: string
  repository_name: string
  overall_score: number
  category_scores: CategoryScore[]
  findings: Finding[]
  summary: Summary
  executive_summary?: string
  risk_analysis?: string
  prioritized_recommendations?: string[]
  files_analyzed: string[]
  analysis_duration_seconds: number
  created_at: string
}

export interface CategoryScore {
  category: string
  score: number
  findings_count?: number
  files_scanned?: number
  critical_count?: number
  high_count?: number
  medium_count?: number
  low_count?: number
}

export interface Finding {
  id?: string
  message?: string
  rule_id: string
  rule_name: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  recommendation: string
  file_path?: string
  line_number?: number
  // AI Fix Generator fields (production-grade) - MUST match backend API
  summary?: string
  risk?: string
  impact?: string
  fix_code?: string
  full_example?: string
  best_practices?: string[]
  confidence?: number  // Backend returns this
  confidence_score?: number  // Also accept for backwards compatibility
  documentation_url?: string
  // Code Diff fields
  before_code?: string
  after_code?: string
  unified_diff?: string
  original_code?: string
  // Security Impact fields
  risk_level?: 'critical' | 'high' | 'medium' | 'low'
  attack_scenario?: string
  business_impact?: string
  environment_impact?: string
  risk_reduction_score?: number  // 0-100, how much fixing this improves security
  predicted_score_after_fix?: number  // Estimated score after applying fix
  estimated_fix_time?: string  // e.g. "~30 min"
  // Legacy fields (fallback only)
  fix_example?: string
  ai_explanation?: string
  impact_analysis?: string
}

export interface Summary {
  critical: number
  high: number
  medium: number
  low: number
  info: number
}

export interface AnalysisJob {
  id: string
  repository_url: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  created_at: string
  completed_at?: string
  error_message?: string
  report_id?: string
}
