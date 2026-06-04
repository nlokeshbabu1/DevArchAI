import { api } from '../lib/api'

export const analysisApi = {
  // Deep analysis with rule engine and AI explanations (with branch support)
  startDeepAnalysis: (repoUrl: string, branch?: string) =>
    api.post('/analyze/repo/deep', {
      repo_url: repoUrl,
      branch: branch || 'main'
    }),

  // Legacy analysis (file detection only)
  startAnalysis: (data: { repository_url: string; include_ai_explanations: boolean; branch?: string }) =>
    api.post('/analyze', data),

  getAnalysisStatus: (jobId: string) =>
    api.get(`/analysis/${jobId}`),

  getReport: (reportId: string) =>
    api.get(`/reports/${reportId}`),

  downloadReport: (reportId: string) =>
    api.get(`/reports/${reportId}/download`, { responseType: 'blob' }),

  // Scans API
  listScans: () =>
    api.get('/scans'),

  getScan: (scanId: string) =>
    api.get(`/scans/${scanId}`),

  getScanFindings: (scanId: string) =>
    api.get(`/scans/${scanId}/findings`),
}
