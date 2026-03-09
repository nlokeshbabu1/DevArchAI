import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const analysisApi = {
  // Deep analysis with rule engine and AI explanations (with branch support)
  startDeepAnalysis: (repoUrl: string, branch?: string) =>
    api.post('/api/v1/analyze/repo/deep', {
      repo_url: repoUrl,
      branch: branch || 'main'
    }),

  // Legacy analysis (file detection only)
  startAnalysis: (data: { repository_url: string; include_ai_explanations: boolean; branch?: string }) =>
    api.post('/api/v1/analyze', data),

  getAnalysisStatus: (jobId: string) =>
    api.get(`/api/v1/analysis/${jobId}`),

  getReport: (reportId: string) =>
    api.get(`/api/v1/reports/${reportId}`),

  downloadReport: (reportId: string) =>
    api.get(`/api/v1/reports/${reportId}/download`, { responseType: 'blob' }),

  // Scans API
  listScans: () =>
    api.get('/api/v1/scans'),

  getScan: (scanId: string) =>
    api.get(`/api/v1/scans/${scanId}`),

  getScanFindings: (scanId: string) =>
    api.get(`/api/v1/scans/${scanId}/findings`),
}
