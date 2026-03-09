/**
 * Scans API endpoints
 */

import apiClient from './client';

export interface Scan {
  id: string;
  status: string;
  progress: number;
  status_message?: string;
  error_message?: string;
  overall_score?: number;
  security_score?: number;
  scalability_score?: number;
  reliability_score?: number;
  cost_score?: number;
  observability_score?: number;
  branch: string;
  commit_hash?: string;
  repository_url: string;
  repository_id?: string;
  organization_id: string;
  started_at?: string;
  completed_at?: string;
  analysis_duration_seconds?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ScanCreate {
  repository_id?: string;
  repository_url: string;
  branch?: string;
  commit_hash?: string;
}

export const scansApi = {
  /**
   * List scans for organization
   */
  listScans: async (orgId: string, statusFilter?: string): Promise<Scan[]> => {
    const params = new URLSearchParams();
    if (statusFilter) {
      params.append('status_filter', statusFilter);
    }
    const response = await apiClient.get<Scan[]>(`/api/v1/scans?org_id=${orgId}&${params.toString()}`);
    return response.data;
  },

  /**
   * Create new scan
   */
  createScan: async (data: ScanCreate): Promise<{ message: string; status: string }> => {
    const response = await apiClient.post('/api/v1/scans', data);
    return response.data;
  },

  /**
   * Get scan by ID
   */
  getScan: async (scanId: string): Promise<Scan> => {
    const response = await apiClient.get<Scan>(`/api/v1/scans/${scanId}`);
    return response.data;
  },

  /**
   * Cancel running scan
   */
  cancelScan: async (scanId: string): Promise<{ message: string }> => {
    const response = await apiClient.post(`/api/v1/scans/${scanId}/cancel`);
    return response.data;
  },

  /**
   * Delete scan
   */
  deleteScan: async (scanId: string): Promise<{ message: string }> => {
    const response = await apiClient.delete(`/api/v1/scans/${scanId}`);
    return response.data;
  },
};
