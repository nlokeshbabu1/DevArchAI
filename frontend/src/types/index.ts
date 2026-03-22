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
  findings_count: number
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
}

export interface Finding {
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
