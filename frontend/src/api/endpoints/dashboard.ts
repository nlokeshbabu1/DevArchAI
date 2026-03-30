/**
 * Dashboard API endpoints
 */

import apiClient from './client';

export interface DashboardSummary {
  total_scans: number;
  total_repositories: number;
  total_findings: number;
  critical_findings: number;
  ai_suggestions: number;
  average_score: number;
}

export interface RecentScan {
  id: string;
  repository_url: string;
  repository_name: string;
  status: string;
  overall_score?: number;
  security_score?: number;
  created_at: string;
  completed_at?: string;
  analysis_duration_seconds?: number;
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

export interface DashboardMetrics {
  severity_counts: Record<string, number>;
  category_counts: Record<string, number>;
  status_counts: Record<string, number>;
  total_scans: number;
  total_findings: number;
  completion_rate: number;
}

export const dashboardApi = {
  /**
   * Get dashboard summary
   */
  getSummary: async (): Promise<DashboardSummary> => {
    const response = await apiClient.get<DashboardSummary>('/dashboard/summary');
    return response.data;
  },

  /**
   * Get recent scans
   */
  getRecentScans: async (limit: number = 5): Promise<RecentScan[]> => {
    const response = await apiClient.get<RecentScan[]>(`/dashboard/recent-scans?limit=${limit}`);
    return response.data;
  },

  /**
   * Get score trends
   */
  getTrends: async (period: string = '30d'): Promise<ScoreTrend[]> => {
    const response = await apiClient.get<ScoreTrend[]>(`/dashboard/trends?period=${period}`);
    return response.data;
  },

  /**
   * Get key metrics
   */
  getMetrics: async (): Promise<DashboardMetrics> => {
    const response = await apiClient.get<DashboardMetrics>('/dashboard/metrics');
    return response.data;
  },

  /**
   * Get active alerts
   */
  getAlerts: async (): Promise<any[]> => {
    const response = await apiClient.get<any[]>('/dashboard/alerts');
    return response.data;
  },
};
