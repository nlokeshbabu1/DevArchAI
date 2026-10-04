import type { ReactNode } from 'react'

export type ConnectionStatus = 'not_connected' | 'connecting' | 'connected' | 'syncing' | 'verifying' | 'error' | 'coming_soon'

export interface IntegrationMeta {
  id: string
  name: string
  description: string
  icon: string
  category: string
  status: ConnectionStatus
  features?: string[]
  connectedAccount?: string
  connectionId?: string
  healthStatus?: string
  kubernetesVersion?: string
  lastVerified?: string
  providerLabel?: string
  lastSync?: string
  extraStats?: Record<string, string | number>
  lastScan?: string
  actionLabel?: string
  onClick?: () => void
}

export interface IntegrationCategory {
  id: string
  title: string
  description: string
  icon: ReactNode
  providers: IntegrationMeta[]
}
