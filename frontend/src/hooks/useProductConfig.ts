import { useEffect, useState } from 'react'
import { api } from '../lib/api'

export type ProductConfig = {
  beta_access_mode: boolean
  checkout_enabled: boolean
  show_upgrade_prompts: boolean
  beta_label: string | null
  limits?: Record<string, number | null>
}

const DEFAULT_CONFIG: ProductConfig = {
  beta_access_mode: false,
  checkout_enabled: true,
  show_upgrade_prompts: true,
  beta_label: null,
}

let cached: ProductConfig | null = null
let inflight: Promise<ProductConfig> | null = null

export async function fetchProductConfig(): Promise<ProductConfig> {
  if (cached) return cached
  if (inflight) return inflight
  inflight = api
    .get<ProductConfig>('/billing/product-config')
    .then((res) => {
      cached = { ...DEFAULT_CONFIG, ...res.data }
      return cached
    })
    .catch(() => DEFAULT_CONFIG)
    .finally(() => {
      inflight = null
    })
  return inflight
}

export type ProductConfigState = {
  config: ProductConfig
  isLoading: boolean
  error: boolean
}

export function useProductConfigState(): ProductConfigState {
  const [config, setConfig] = useState<ProductConfig>(cached ?? DEFAULT_CONFIG)
  const [isLoading, setIsLoading] = useState(cached === null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (cached) {
      setConfig(cached)
      setIsLoading(false)
      return
    }
    let active = true
    setIsLoading(true)
    api
      .get<ProductConfig>('/billing/product-config')
      .then((res) => {
        if (!active) return
        cached = { ...DEFAULT_CONFIG, ...res.data }
        setConfig(cached)
        setError(false)
      })
      .catch(() => {
        if (!active) return
        setConfig(DEFAULT_CONFIG)
        setError(true)
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  return { config, isLoading, error }
}

/** @deprecated Prefer useProductConfigState when loading UI matters */
export function useProductConfig(): ProductConfig {
  return useProductConfigState().config
}

export function clearProductConfigCache() {
  cached = null
  inflight = null
}

export const LIMIT_DISPLAY_LABELS: Record<string, string> = {
  max_scans_per_month: 'Scans per month',
  max_repositories: 'Repositories',
  max_reports_per_month: 'Reports per month',
  max_concurrent_scans: 'Concurrent scans',
  max_ai_requests_per_month: 'AI requests per month',
  max_ai_tokens_per_month: 'AI tokens per month',
  max_remediation_per_month: 'Remediation jobs per month',
}

export function formatConfigLimits(limits?: Record<string, number | null>): { label: string; value: string }[] {
  if (!limits) return []
  return Object.entries(limits)
    .filter(([, value]) => typeof value === 'number' && value > 0)
    .map(([key, value]) => ({
      label: LIMIT_DISPLAY_LABELS[key] ?? key.replace(/_/g, ' '),
      value: String(value),
    }))
}
