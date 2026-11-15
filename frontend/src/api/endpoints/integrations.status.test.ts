import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()

vi.mock('../client', () => ({
  default: {
    get: (...args: unknown[]) => getMock(...args),
  },
}))

import { integrationsApi } from './integrations'

describe('integrationsApi.getStatus', () => {
  beforeEach(() => {
    getMock.mockReset()
  })

  it('does not mark GitHub OAuth connected when only manual repositories exist', async () => {
    getMock.mockResolvedValue({
      data: {
        github: true,
        github_oauth: false,
        github_app_installed: false,
        github_repository_access: true,
        gitlab: false,
        gitlab_oauth: false,
        aws: false,
        azure: false,
        bitbucket: false,
        kubernetes: false,
        eks: false,
      },
    })

    const result = await integrationsApi.getStatus({ authProvider: 'email' })
    const github = result.find((entry) => entry.provider === 'github')
    expect(github?.connected).toBe(false)
    expect(github?.status).toBe('not_connected')
    expect(github?.connectionDetail).toContain('manually')
  })
})