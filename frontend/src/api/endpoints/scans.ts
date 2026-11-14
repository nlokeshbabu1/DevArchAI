/**
 * Scans API endpoints
 */

import type { StageMetadata } from '../../types';

import apiClient from './client';

export interface Scan {
  id: string;
  status: string;
  scan_status?: string;
  ai_status?: 'pending' | 'queued' | 'processing' | 'completed' | 'failed';
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

export interface UnifiedScanStartResponse {
  scan_id: string;
  session_token?: string;
  status: string;
  message?: string;
  repository_id?: string;
  repository_url?: string;
  branch?: string;
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
   * Start unified scan (guest or authenticated)
   */
  startUnifiedScan: async (data: ScanCreate): Promise<UnifiedScanStartResponse> => {
    const response = await apiClient.post<UnifiedScanStartResponse>('/scan/start', data);
    return response.data;
  },

  /**
   * Get scan stage metadata (labels, icons, order)
   */
  getStages: async (): Promise<StageMetadata[]> => {
    const response = await apiClient.get<{ stages: StageMetadata[] }>('/scan/stages');
    return response.data.stages;
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
   * Get scan results (scan details + findings + technology breakdown)
   * Uses unified results endpoint for canonical technology_details and per-finding technology.
   */
  getScanResults: async (scanId: string): Promise<any> => {
    const timestamp = Date.now();
    const response = await apiClient.get(`/scan/results/${scanId}?t=${timestamp}`, {
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
      },
    });
    return response.data;
  },

  /**
   * Aggregate AI recommendation job status for a scan.
   */
  getAiStatus: async (scanId: string): Promise<{
    scan_id: string
    ai_status: string
    total_jobs: number
    by_status: Record<string, number>
  }> => {
    const response = await apiClient.get(`/scans/${scanId}/ai/status`);
    return response.data;
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
    const response = await apiClient.delete(`/scans/${scanId}`);
    return response.data;
  },

  /**
   * Get authoritative scan state (for reconnect sync and progress tracking)
   */
  getScanState: async (scanId: string): Promise<{
    scan_id: string
    status: string
    current_stage: string | null
    progress: number
    is_terminal: boolean
    error_message?: string
    detected_stack: string[]
    started_at?: string
    completed_at?: string
    overall_score?: number
    created_at: string
  }> => {
    const response = await apiClient.get(`/scan/state/${scanId}`);
    return response.data;
  },

  /**
   * Get scan findings
   */
  getScanFindings: async (scanId: string): Promise<any[]> => {
    const response = await apiClient.get(`/scans/${scanId}/findings`);
    return response.data;
  },
};
