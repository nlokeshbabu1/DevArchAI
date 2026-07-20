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
  // Scanner metadata fields (from backend normalization)
  scanner_name?: string
  scanner_rule_id?: string
  package?: string
  installed_version?: string
  fixed_version?: string
  cve?: string
  cwe?: string
  references?: string[]
  evidence?: string
  resource_name?: string
  // Legacy fields (fallback only)
  fix_example?: string
  ai_explanation?: string
  impact_analysis?: string
}

export interface ScannerExecution {
  scanner_name: string
  scanner_id: string
  version: string | null
  status: 'DISCOVERED' | 'INITIALIZING' | 'RUNNING' | 'COMPLETED' | 'COMPLETED_WITH_FINDINGS' | 'COMPLETED_NO_FINDINGS' | 'SKIPPED_NOT_APPLICABLE' | 'UNAVAILABLE' | 'DISABLED' | 'FAILED'
  applicable: boolean
  enabled: boolean
  execution_start: string | null
  execution_end: string | null
  duration_ms: number | null
  files_scanned: number | null
  rules_executed: number | null
  findings_count: number
  skipped_reason: string | null
  error_message: string | null
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

export type ScanStage =
  | 'connecting'
  | 'cloning'
  | 'technology_detection'
  | 'scanner_selection'
  | 'scanning'
  | 'normalization'
  | 'deduplication'
  | 'ai_generation'
  | 'report_generation'

export interface StageMetadata {
  id: ScanStage
  label: string
  icon: string
  order: number
}

export interface ScanState {
  scan_id: string
  status: string
  current_stage: ScanStage | null
  progress: number
  is_terminal: boolean
  error_message?: string
  detected_stack: string[]
  started_at?: string
  completed_at?: string
  overall_score?: number
  created_at: string
}

export type ScanLifecycleState =
  | 'idle'
  | 'creating'
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'reconnecting'

// --- Enterprise Pipeline Types ---

export interface ScannerStatus {
  scanner_id: string
  scanner_name: string
  status: 'pending' | 'running' | 'completed' | 'completed_with_findings' | 'completed_no_findings' | 'skipped' | 'unavailable' | 'failed'
  rules_count?: number
  findings_count: number
  started_at?: string
  completed_at?: string
  duration_ms?: number
  error?: string
}

export interface LiveFinding {
  rule_id: string
  rule_name: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  file_path?: string
  line_number?: number
  description: string
  timestamp: string
}

export interface AIGenerationProgress {
  phase: string
  message: string
  progress: number
  findings_processed: number
  findings_total: number
  timestamp: string
}

export interface StageTransition {
  stage: ScanStage
  stage_label: string
  progress: number
  status: 'running' | 'completed' | 'failed'
  timestamp: string
}

export interface SeverityCounts {
  critical: number
  high: number
  medium: number
  low: number
  info: number
}

export type ScanEventType =
  | 'connecting'
  | 'cloning'
  | 'cloned'
  | 'indexed'
  | 'dockerfile_found'
  | 'terraform_found'
  | 'helm_found'
  | 'k8s_found'
  | 'github_actions_found'
  | 'tech_detection_complete'
  | 'running_docker_rules'
  | 'running_terraform_rules'
  | 'running_k8s_rules'
  | 'running_secret_detection'
  | 'finding_discovered'
  | 'ai_suggestion_generation'
  | 'creating_pull_request'
  | 'uploading_report'
  | 'scan_completed'
  | 'scan_failed'
  | 'progress_update'
  | 'scanner_start'
  | 'scanner_complete'
  | 'stack_detected'
  | 'log_message'
  | 'ai_progress'
  | 'stage_transition'
  | 'connection_ack'
  | 'unknown'

export interface ScanEvent {
  id: number
  type: ScanEventType
  timestamp: string
  progress: number
  stage: string
  message: string
  metadata: Record<string, any>
}

export interface ScanProgressSnapshot {
  scanId: string
  status: string
  currentStage: ScanStage | null
  progress: number
  currentStep?: string
  detectedStack: string[]
  isTerminal: boolean
  errorMessage?: string
  startedAt?: string
  completedAt?: string
  scanners: Record<string, ScannerStatus>
  liveFindings: LiveFinding[]
  aiProgress: AIGenerationProgress | null
  stageTransitions: StageTransition[]
  filesScanned: number
  totalFiles: number
  severityCounts: SeverityCounts
  logs: string[]
  events: ScanEvent[]
}

export interface RepoMetadata {
  owner: string
  repo: string
  branch: string
  visibility: string
  defaultBranch: string
  description?: string
  stars?: number
  language?: string
}
