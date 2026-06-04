/**
 * Reports API endpoints
 */

import apiClient from './client';

export interface Report {
  id: string;
  scan_id: string;
  repository_name: string;
  repository_url: string;
  commit_hash?: string;
  branch?: string;
  overall_score: number;
  category_scores?: Record<string, number>;
  executive_summary?: string;
  risk_analysis?: string;
  prioritized_recommendations?: string[];
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  files_analyzed?: string[];
  is_public: boolean;
  organization_id: string;
  created_at?: string;
  updated_at?: string;
}

export interface ReportDownloadLink {
  report_id: string;
  scan_id: string;
  format: 'pdf' | 'excel';
  url: string;
  filename: string;
  expires_at: string;
  expires_in_seconds: number;
}

export const reportsApi = {
  /**
   * List reports for organization
   */
  listReports: async (orgId: string): Promise<Report[]> => {
    const response = await apiClient.get<Report[]>(`/reports?org_id=${orgId}`);
    return response.data;
  },

  /**
   * Get report by ID
   */
  getReport: async (reportId: string): Promise<Report> => {
    const response = await apiClient.get<Report>(`/reports/${reportId}`);
    return response.data;
  },

  /**
   * Download report
   */
  downloadReport: async (reportId: string, format: string = 'json'): Promise<Blob> => {
    const response = await apiClient.get(`/reports/${reportId}/download?format=${format}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Generate shareable link for report
   */
  shareReport: async (reportId: string): Promise<{ message: string; share_url?: string }> => {
    const response = await apiClient.post(`/reports/${reportId}/share`);
    return response.data;
  },
};
