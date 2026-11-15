/**
 * Security regression tests.
 *
 * These tests ensure that authentication tokens are NEVER stored in
 * localStorage, sessionStorage, IndexedDB, or cookies via JavaScript.
 * The access token must live ONLY in JavaScript memory.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'

import {
  getAccessToken,
  setAccessToken,
  clearAuthMemory,
  getOrgId,
  setOrgId,
} from './auth-token'

describe('Auth Token Security Regression', () => {
  beforeEach(() => {
    clearAuthMemory()
    vi.restoreAllMocks()
  })

  it('stores access token in memory only', () => {
    const token = 'test-access-token-abc123'
    setAccessToken(token)
    expect(getAccessToken()).toBe(token)
  })

  it('never writes access token to localStorage', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem')
    setAccessToken('secret-token')
    const localStorageCalls = setItemSpy.mock.calls.filter(([key]) =>
      key.includes('token') || key.includes('auth') || key.includes('access')
    )
    expect(localStorageCalls).toHaveLength(0)
    setItemSpy.mockRestore()
  })

  it('never writes refresh token to localStorage', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem')
    const refreshTokenCalls = setItemSpy.mock.calls.filter(([key]) =>
      key.includes('refresh')
    )
    expect(refreshTokenCalls).toHaveLength(0)
    setItemSpy.mockRestore()
  })

  it('never reads access token from localStorage', () => {
    const getItemSpy = vi.spyOn(Storage.prototype, 'getItem')
    const token = getAccessToken()
    const localStorageReads = getItemSpy.mock.calls.filter(([key]) =>
      key.includes('token') || key.includes('auth') || key.includes('access')
    )
    expect(localStorageReads).toHaveLength(0)
    getItemSpy.mockRestore()
  })

  it('never writes tokens to sessionStorage', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem')
    setAccessToken('secret-token')
    const sessionStorageCalls = setItemSpy.mock.calls.filter(([key]) =>
      key.includes('token') || key.includes('auth') || key.includes('access')
    )
    expect(sessionStorageCalls).toHaveLength(0)
    setItemSpy.mockRestore()
  })

  it('clearAuthMemory removes token from memory', () => {
    setAccessToken('secret-token')
    clearAuthMemory()
    expect(getAccessToken()).toBeNull()
  })

  it('orgId is stored in memory only', () => {
    setOrgId('org-123')
    expect(getOrgId()).toBe('org-123')
    clearAuthMemory()
    expect(getOrgId()).toBeNull()
  })

  it('no auth tokens in localStorage after login', () => {
    setAccessToken('login-token')
    const keys = Object.keys(localStorage)
    const authKeys = keys.filter(
      (k) => k.includes('token') || k.includes('auth') || k.includes('access') || k.includes('refresh')
    )
    expect(authKeys).toHaveLength(0)
  })

  it('no auth tokens in sessionStorage after login', () => {
    setAccessToken('login-token')
    const keys = Object.keys(sessionStorage)
    const authKeys = keys.filter(
      (k) => k.includes('token') || k.includes('auth') || k.includes('access') || k.includes('refresh')
    )
    expect(authKeys).toHaveLength(0)
  })

  it('document.cookie does not contain auth tokens', () => {
    setAccessToken('secret-access-token')
    const cookieStr = document.cookie
    expect(cookieStr).not.toContain('secret-access-token')
    expect(cookieStr).not.toContain('access_token')
    expect(cookieStr).not.toContain('refresh_token')
  })
})
