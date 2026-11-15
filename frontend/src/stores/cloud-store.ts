import { create } from 'zustand'

import type {
  CloudAIRecommendation,
  CloudAIRecommendationSummary,
  CloudConnection,
  CloudOverview,
  CloudResource,
  CloudFinding,
  CloudCostRecommendation,
  CloudComplianceResult,
} from '../api/endpoints/cloud'

type CloudTab = 'overview' | 'resources' | 'findings' | 'recommendations' | 'cost' | 'compliance'

interface CloudState {
  activeTab: CloudTab
  setActiveTab: (tab: CloudTab) => void

  connections: CloudConnection[]
  setConnections: (connections: CloudConnection[]) => void

  selectedConnectionId: string | null
  setSelectedConnectionId: (id: string | null) => void

  overview: CloudOverview | null
  setOverview: (overview: CloudOverview) => void

  resources: CloudResource[]
  setResources: (resources: CloudResource[]) => void

  findings: CloudFinding[]
  setFindings: (findings: CloudFinding[]) => void

  costs: CloudCostRecommendation[]
  setCosts: (costs: CloudCostRecommendation[]) => void

  compliance: CloudComplianceResult[]
  setCompliance: (results: CloudComplianceResult[]) => void

  recommendations: CloudAIRecommendation[]
  setRecommendations: (recommendations: CloudAIRecommendation[]) => void

  recommendationsSummary: CloudAIRecommendationSummary | null
  setRecommendationsSummary: (summary: CloudAIRecommendationSummary) => void

  scanInProgress: boolean
  setScanInProgress: (inProgress: boolean) => void

  scanProgress: number
  setScanProgress: (progress: number) => void

  scanStage: string
  setScanStage: (stage: string) => void

  isLoading: boolean
  setIsLoading: (loading: boolean) => void

  error: string | null
  setError: (error: string | null) => void

  reset: () => void
}

const initialState = {
  activeTab: 'overview' as CloudTab,
  connections: [],
  selectedConnectionId: null,
  overview: null,
  resources: [],
  findings: [],
  costs: [],
  compliance: [],
  recommendations: [],
  recommendationsSummary: null,
  scanInProgress: false,
  scanProgress: 0,
  scanStage: '',
  isLoading: false,
  error: null,
}

export const useCloudStore = create<CloudState>()((set) => ({
  ...initialState,

  setActiveTab: (tab) => set({ activeTab: tab }),

  setConnections: (connections) => set({ connections }),

  setSelectedConnectionId: (id) => set({ selectedConnectionId: id }),

  setOverview: (overview) => set({ overview }),

  setResources: (resources) => set({ resources }),

  setFindings: (findings) => set({ findings }),

  setCosts: (costs) => set({ costs }),

  setCompliance: (results) => set({ compliance: results }),

  setRecommendations: (recommendations) => set({ recommendations }),

  setRecommendationsSummary: (summary) => set({ recommendationsSummary: summary }),

  setScanInProgress: (inProgress) => set({ scanInProgress: inProgress }),

  setScanProgress: (progress) => set({ scanProgress: progress }),

  setScanStage: (stage) => set({ scanStage: stage }),

  setIsLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  reset: () => set(initialState),
}))
