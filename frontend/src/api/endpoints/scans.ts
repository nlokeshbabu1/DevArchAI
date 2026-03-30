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
   * List scans for current user
   */
  listScans: async (statusFilter?: string, page: number = 1, page_size: number = 100): Promise<Scan[]> => {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('page_size', page_size.toString());
    if (statusFilter) {
      params.append('status_filter', statusFilter);
    }
    const response = await apiClient.get<Scan[]>(`/scans?${params.toString()}`);
    return response.data;
  },

  /**
   * Create new scan
   */
  createScan: async (data: ScanCreate): Promise<Scan> => {
    const response = await apiClient.post<Scan>('/scans', data);
    return response.data;
  },

  /**
   * Start unified scan (guest or authenticated)
   */
  startUnifiedScan: async (data: ScanCreate): Promise<{ scan_id: string; session_token?: string; status: string }> => {
    const response = await apiClient.post('/scan/start', data);
    return response.data;
  },

  /**
   * Get scan by ID
   */
  getScan: async (scanId: string): Promise<Scan> => {
    const response = await apiClient.get<Scan>(`/scans/${scanId}`);
    return response.data;
  },

  /**
   * Get scan progress
   */
  getScanProgress: async (scanId: string): Promise<{ status: string; progress: number; current_step: string }> => {
    const response = await apiClient.get(`/scan/status/${scanId}`);
    return response.data;
  },

  /**
   * Get scan results (scan details + findings)
   * Uses /scans/{id} endpoint which is more reliable
   */
  getScanResults: async (scanId: string): Promise<any> => {
    // Add cache-busting to prevent stale data
    const timestamp = Date.now();
    // Get scan details
    const scanResponse = await apiClient.get(`/scans/${scanId}?t=${timestamp}`, {
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
      }
    });
    // Get findings
    const findingsResponse = await apiClient.get(`/scans/${scanId}/findings?t=${timestamp}`, {
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
      }
    });

    return {
      ...scanResponse.data,
      findings: findingsResponse.data,
    };
  },

  /**
   * Cancel running scan
   */
  cancelScan: async (scanId: string): Promise<{ message: string }> => {
    const response = await apiClient.post(`/scans/${scanId}/cancel`);
    return response.data;
  },

  /**
   * Delete scan
   */
  deleteScan: async (scanId: string): Promise<{ message: string }> => {
    const response = await apiClient.delete(`/api/v1/scans/${scanId}`);
    return response.data;
  },

  /**
   * Get scan findings
   */
  getScanFindings: async (scanId: string): Promise<any[]> => {
    const response = await apiClient.get(`/api/v1/scans/${scanId}/findings`);
    return response.data;
  },
};
