/**
 * First-message WebSocket authentication (no tokens in the URL).
 */
export function buildWebSocketAuthMessage(options: {
  accessToken?: string | null
  apiKey?: string | null
  sessionToken?: string | null
}): string {
  const payload: Record<string, string> = { type: 'auth' }
  if (options.accessToken) payload.access_token = options.accessToken
  if (options.apiKey) payload.api_key = options.apiKey
  if (options.sessionToken) payload.session_token = options.sessionToken
  return JSON.stringify(payload)
}
