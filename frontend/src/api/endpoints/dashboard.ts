/**
 * Dashboard API endpoints
 */

import apiClient from './client';

export interface DashboardSummary {
  total_scans: number;
  total_findings: number;
  critical_findings: number;
  average_score: number;
  recent_scans: ScanSummary[];
}

export interface ScanSummary {
  id: string;
  repository_name: string;
  score: number;
  status: string;
  created_at: string;
}

export interface ScoreTrend {
  date: string;
    security: number;
  scalability: number;
  reliability: number;
  cost: number;
  observability: number;
  overall: number;
}

export const dashboardApi = {
  /**
   * Get dashboard summary
   */
  getSummary: async (orgId: string): Promise<DashboardSummary> => {
    const response = await apiClient.get<DashboardSummary>(`/api/v1/dashboard/summary?org_id=${orgId}`);
    return response.data;
  },

  /**
   * Get score trends
   */
  getTrends: async (orgId: string, period: string = '30d'): Promise<ScoreTrend[]> => {
    const response = await apiClient.get<ScoreTrend[]>(`/api/v1/dashboard/trends?org_id=${orgId}&period=${period}`);
    return response.data;
  },

  /**
   * Get key metrics
   */
  getMetrics: async (orgId: string): Promise<Record<string, number>> => {
    const response = await apiClient.get<Record<string, number>>(`/api/v1/dashboard/metrics?org_id=${orgId}`);
    return response.data;
  },

  /**
   * Get active alerts
   */
  getAlerts: async (orgId: string): Promise<any[]> => {
    const response = await apiClient.get<any[]>(`/api/v1/dashboard/alerts?org_id=${orgId}`);
    return response.data;
  },
};
