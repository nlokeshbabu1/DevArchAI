import { QueryClient } from '@tanstack/react-query'

let queryClientSingleton: QueryClient | null = null

export function registerQueryClient(client: QueryClient): void {
  queryClientSingleton = client
}

export function getQueryClient(): QueryClient | null {
  return queryClientSingleton
}

export function clearUserQueryCache(): void {
  queryClientSingleton?.clear()
}
