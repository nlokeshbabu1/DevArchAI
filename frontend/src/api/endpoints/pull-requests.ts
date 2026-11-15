/**
 * Pull Request API endpoints
 */

import apiClient from './client';

export interface CreatePRRequest {
  scan_id: string;
  finding_ids?: string[];
  branch_name?: string;
  pr_title?: string;
  pr_description?: string;
  is_draft?: boolean;
  /** Default true: all selected findings must patch successfully */
  atomic_mode?: boolean;
}

export interface RemediationOutcome {
  finding_id: string;
  rule_id?: string;
  file_path?: string;
  status: string;
  reason?: string;
  manual_guidance?: string;
  validation?: Array<{ name: string; status: string; message?: string }>;
}

export interface RemediationReport {
  base_commit_sha?: string;
  atomic_mode?: boolean;
  atomic_ok?: boolean;
  outcomes?: RemediationOutcome[];
  files_modified?: string[];
}

export interface CreatePRResponse {
  pr_id: string;
  scan_id: string;
  github_pr_number: number;
  github_pr_url: string;
  branch_name: string;
  title: string;
  status: 'open' | 'merged' | 'closed' | 'draft';
  findings_fixed: string[];
  score_before: number;
  score_after: number;
  created_at: string;
  remediation_report?: RemediationReport | null;
}

export interface PRInfo {
  id: string;
  github_pr_number: number;
  github_pr_url: string;
  branch_name: string;
  title: string;
  status: string;
  created_at: string;
  merged_at: string | null;
}

export const prApi = {
  /**
   * Create a GitHub Pull Request with AI-generated fixes
   */
  createPR: async (data: CreatePRRequest): Promise<CreatePRResponse> => {
    const response = await apiClient.post<CreatePRResponse>('/github/create-pr', data);
    return response.data;
  },

  /**
   * List all PRs for a scan
   */
  listPRs: async (scanId: string): Promise<{ prs: PRInfo[]; total: number }> => {
    const response = await apiClient.get<{ prs: PRInfo[]; total: number }>(`/github/prs/${scanId}`);
    return response.data;
  },
};
