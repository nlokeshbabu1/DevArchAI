import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useScanWebSocket } from './useScanWebSocket'

vi.mock('../lib/api', () => ({
  buildWebSocketUrl: vi.fn((path: string) => `ws://localhost:8000${path}`),
}))

vi.mock('../lib/auth-token', () => ({
  getAccessToken: vi.fn(() => 'test-access-token'),
}))

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static OPEN = 1
  static CONNECTING = 0
  static CLOSED = 3
  static defaultAutoOpen = true
  url: string
  onopen: ((ev: Event) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null
  readyState = 0
  autoOpen: boolean

  constructor(url: string) {
    this.url = url
    this.autoOpen = MockWebSocket.defaultAutoOpen
    MockWebSocket.instances.push(this)
    if (this.autoOpen) {
      setTimeout(() => {
        this.readyState = 1
        this.onopen?.(new Event('open'))
      }, 0)
    }
  }

  send(_data: string) {}
  close() {
    this.readyState = 3
  }

  simulateMessage(data: any) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }))
  }

  simulateOpen() {
    this.readyState = 1
    this.onopen?.(new Event('open'))
  }

  simulateClose() {
    this.readyState = 3
    this.onclose?.(new CloseEvent('close'))
  }

  static reset() {
    MockWebSocket.instances = []
  }
}

describe('useScanWebSocket', () => {
  async function flushConnect() {
    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
      vi.advanceTimersByTime(1)
    })
  }

  beforeEach(() => {
    MockWebSocket.reset()
    vi.useFakeTimers()
    Object.defineProperty(globalThis, 'WebSocket', {
      value: MockWebSocket,
      writable: true,
      configurable: true,
    })
    localStorage.clear()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false } as Response)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('should start in idle state when disabled', () => {
    const { result } = renderHook(() =>
      useScanWebSocket({ scanId: 'scan-123', enabled: false })
    )
    expect(result.current.lifecycleState).toBe('idle')
    expect(result.current.scanState).toBeNull()
    expect(result.current.error).toBeNull()
    expect(result.current.connectionStatus).toBe('disconnected')
  })

  it('should not put access tokens in the WebSocket URL', async () => {
    renderHook(() => useScanWebSocket({ scanId: 'scan-123' }))
    await flushConnect()
    const ws = MockWebSocket.instances[0]
    expect(ws.url).not.toContain('token=')
    expect(ws.url).not.toContain('access_token')
  })

  it('should transition to running on progress_update', async () => {
    const { result } = renderHook(() =>
      useScanWebSocket({ scanId: 'scan-123' })
    )

    await flushConnect()

    expect(result.current.lifecycleState).toBe('running')

    const ws = MockWebSocket.instances[0]
    await act(async () => {
      ws.simulateMessage({
        type: 'progress_update',
        data: {
          scan_id: 'scan-123',
          status: 'running',
          progress: 50,
          current_step: 'scanning',
        },
      })
    })

    expect(result.current.scanState).not.toBeNull()
    expect(result.current.scanState?.progress).toBe(50)
    expect(result.current.scanState?.currentStage).toBe('scanning')
    expect(result.current.scanState?.scanners).toEqual({})
    expect(result.current.scanState?.liveFindings).toEqual([])
    expect(result.current.scanState?.aiProgress).toBeNull()
    expect(result.current.scanState?.stageTransitions).toEqual([])
  })

  it('should handle scanner_start', async () => {
    const { result } = renderHook(() =>
      useScanWebSocket({ scanId: 'scan-123' })
    )

    await flushConnect()

    const ws = MockWebSocket.instances[0]
    await act(async () => {
      ws.simulateMessage({
        type: 'scanner_start',
        data: {
          scanner_id: 'hadolint',
          scanner_name: 'Docker',
          rules_count: 42,
          timestamp: '2024-01-01T00:00:00Z',
        },
      })
    })

    expect(result.current.scanState).not.toBeNull()
    expect(result.current.scanState?.scanners['hadolint']).toBeDefined()
    expect(result.current.scanState?.scanners['hadolint'].status).toBe('running')
    expect(result.current.scanState?.scanners['hadolint'].scanner_name).toBe('Docker')
    expect(result.current.scanState?.scanners['hadolint'].rules_count).toBe(42)
    expect(result.current.scanState?.scanners['hadolint'].findings_count).toBe(0)
  })

  it('should handle scanner_complete', async () => {
    const { result } = renderHook(() =>
      useScanWebSocket({ scanId: 'scan-123' })
    )

    await flushConnect()

    const ws = MockWebSocket.instances[0]

    await act(async () => {
      ws.simulateMessage({
        type: 'scanner_start',
        data: { scanner_id: 'gitleaks', scanner_name: 'Secrets' },
      })
    })

    await act(async () => {
      ws.simulateMessage({
        type: 'scanner_complete',
        data: {
          scanner_id: 'gitleaks',
          status: 'completed_with_findings',
          findings_count: 5,
          duration_ms: 3200,
        },
      })
    })

    expect(result.current.scanState?.scanners['gitleaks'].status).toBe(
      'completed_with_findings'
    )
    expect(result.current.scanState?.scanners['gitleaks'].findings_count).toBe(5)
    expect(result.current.scanState?.scanners['gitleaks'].duration_ms).toBe(3200)
  })

  it('should handle finding_added', async () => {
    const { result } = renderHook(() =>
      useScanWebSocket({ scanId: 'scan-123' })
    )

    await flushConnect()

    const ws = MockWebSocket.instances[0]
    await act(async () => {
      ws.simulateMessage({
        type: 'finding_added',
        data: {
          rule_id: 'G101',
          rule_name: 'Hardcoded password',
          severity: 'high',
          category: 'secrets',
          file_path: 'config.yaml',
          line_number: 42,
          description: 'Hardcoded secret found',
          timestamp: '2024-01-01T00:00:00Z',
        },
      })
    })

    expect(result.current.scanState?.liveFindings).toHaveLength(1)
    expect(result.current.scanState?.liveFindings[0].rule_id).toBe('G101')
    expect(result.current.scanState?.liveFindings[0].rule_name).toBe('Hardcoded password')
    expect(result.current.scanState?.liveFindings[0].severity).toBe('high')
    expect(result.current.scanState?.liveFindings[0].file_path).toBe('config.yaml')
    expect(result.current.scanState?.liveFindings[0].line_number).toBe(42)
  })

  it('should handle ai_progress', async () => {
    const { result } = renderHook(() =>
      useScanWebSocket({ scanId: 'scan-123' })
    )

    await flushConnect()

    const ws = MockWebSocket.instances[0]
    await act(async () => {
      ws.simulateMessage({
        type: 'ai_progress',
        data: {
          phase: 'analyzing',
          message: 'Grouping findings by category',
          progress: 35,
          findings_processed: 7,
          findings_total: 20,
          timestamp: '2024-01-01T00:00:00Z',
        },
      })
    })

    expect(result.current.scanState?.aiProgress).not.toBeNull()
    expect(result.current.scanState?.aiProgress?.phase).toBe('analyzing')
    expect(result.current.scanState?.aiProgress?.message).toBe(
      'Grouping findings by category'
    )
    expect(result.current.scanState?.aiProgress?.progress).toBe(35)
    expect(result.current.scanState?.aiProgress?.findings_processed).toBe(7)
    expect(result.current.scanState?.aiProgress?.findings_total).toBe(20)
  })

  it('should handle stage_transition', async () => {
    const { result } = renderHook(() =>
      useScanWebSocket({ scanId: 'scan-123' })
    )

    await flushConnect()

    const ws = MockWebSocket.instances[0]
    await act(async () => {
      ws.simulateMessage({
        type: 'stage_transition',
        data: {
          stage: 'scanning',
          stage_label: 'Running security scanners',
          progress: 45,
          status: 'running',
          timestamp: '2024-01-01T00:00:00Z',
        },
      })
    })

    expect(result.current.scanState?.stageTransitions).toHaveLength(1)
    expect(result.current.scanState?.stageTransitions[0].stage).toBe('scanning')
    expect(result.current.scanState?.stageTransitions[0].stage_label).toBe(
      'Running security scanners'
    )
    expect(result.current.scanState?.stageTransitions[0].progress).toBe(45)
    expect(result.current.scanState?.stageTransitions[0].status).toBe('running')
  })

  it('should handle stack_detected', async () => {
    const { result } = renderHook(() =>
      useScanWebSocket({ scanId: 'scan-123' })
    )

    await flushConnect()

    const ws = MockWebSocket.instances[0]
    await act(async () => {
      ws.simulateMessage({
        type: 'stack_detected',
        data: {
          stack: ['Docker', 'Kubernetes', 'TypeScript'],
        },
      })
    })

    expect(result.current.scanState?.detectedStack).toEqual([
      'Docker',
      'Kubernetes',
      'TypeScript',
    ])
  })

  it('should cap liveFindings at 50', async () => {
    const { result } = renderHook(() =>
      useScanWebSocket({ scanId: 'scan-123' })
    )

    await flushConnect()

    const ws = MockWebSocket.instances[0]

    for (let i = 0; i < 60; i++) {
      await act(async () => {
        ws.simulateMessage({
          type: 'finding_added',
          data: {
            rule_id: `R${i}`,
            rule_name: `Rule ${i}`,
            severity: 'low',
            category: 'test',
            description: `Finding ${i}`,
          },
        })
      })
    }

    expect(result.current.scanState?.liveFindings).toHaveLength(50)
    expect(result.current.scanState?.liveFindings[0].rule_id).toBe('R10')
    expect(result.current.scanState?.liveFindings[49].rule_id).toBe('R59')
  })

  it('should transition to completed on scan_complete', async () => {
    const onComplete = vi.fn()

    const { result } = renderHook(() =>
      useScanWebSocket({ scanId: 'scan-123', onComplete })
    )

    await flushConnect()

    const ws = MockWebSocket.instances[0]
    await act(async () => {
      ws.simulateMessage({ type: 'scan_complete', data: { scan_id: 'scan-123' } })
    })

    expect(result.current.lifecycleState).toBe('completed')
    expect(result.current.scanState?.status).toBe('completed')
    expect(result.current.scanState?.isTerminal).toBe(true)
    expect(onComplete).toHaveBeenCalledWith({ scan_id: 'scan-123' })
  })

  it('should transition to failed on scan_failed', async () => {
    const onFailed = vi.fn()

    const { result } = renderHook(() =>
      useScanWebSocket({ scanId: 'scan-123', onFailed })
    )

    await flushConnect()

    const ws = MockWebSocket.instances[0]
    await act(async () => {
      ws.simulateMessage({
        type: 'scan_failed',
        data: { scan_id: 'scan-123', error: 'Connection lost' },
      })
    })

    expect(result.current.lifecycleState).toBe('failed')
    expect(result.current.scanState?.status).toBe('failed')
    expect(result.current.scanState?.isTerminal).toBe(true)
    expect(result.current.scanState?.errorMessage).toBe('Connection lost')
    expect(onFailed).toHaveBeenCalled()
  })

  it('should reconnect on disconnect with backoff', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue({ ok: false } as Response)

    const { result } = renderHook(() =>
      useScanWebSocket({ scanId: 'scan-123' })
    )

    await flushConnect()

    expect(result.current.lifecycleState).toBe('running')

    const ws = MockWebSocket.instances[0]

    await act(async () => {
      ws.simulateClose()
    })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/scan/state/scan-123'),
      expect.any(Object)
    )

    const countBefore = MockWebSocket.instances.length
    await act(async () => {
      vi.advanceTimersByTime(1100)
    })

    expect(MockWebSocket.instances.length).toBe(countBefore + 1)
  })

  it('should stop reconnecting after max attempts', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue({ ok: false } as Response)

    MockWebSocket.defaultAutoOpen = false

    renderHook(() => useScanWebSocket({ scanId: 'scan-123' }))
    await flushConnect()

    for (let i = 0; i < 55; i++) {
      const ws = MockWebSocket.instances[MockWebSocket.instances.length - 1]
      if (!ws) break
      await act(async () => {
        ws.simulateClose()
      })
      await act(async () => {
        vi.advanceTimersByTime(60000)
        await Promise.resolve()
      })
    }

    const countAfterExhausted = MockWebSocket.instances.length

    const lastWs = MockWebSocket.instances[MockWebSocket.instances.length - 1]
    if (lastWs) {
      await act(async () => {
        lastWs.simulateClose()
      })
    }
    await act(async () => {
      vi.advanceTimersByTime(60000)
    })

    expect(MockWebSocket.instances.length).toBe(countAfterExhausted)

    MockWebSocket.defaultAutoOpen = true
  })

  it('should fetch scan state on reconnect', async () => {
    const fetchSpy = vi.mocked(globalThis.fetch).mockResolvedValue({ ok: false } as Response)

    renderHook(() => useScanWebSocket({ scanId: 'scan-123' }))

    await flushConnect()

    const ws = MockWebSocket.instances[0]
    await act(async () => {
      ws.simulateClose()
    })

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/scan/state/scan-123'),
      expect.objectContaining({ headers: expect.any(Object) })
    )
  })

  it('should stop reconnecting if fetched state is terminal', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        scan_id: 'scan-123',
        status: 'completed',
        current_stage: null,
        progress: 100,
        is_terminal: true,
        detected_stack: [],
        created_at: '2024-01-01T00:00:00Z',
      }),
    } as Response)

    const onComplete = vi.fn()

    const { result } = renderHook(() =>
      useScanWebSocket({ scanId: 'scan-123', onComplete })
    )

    await flushConnect()

    const ws = MockWebSocket.instances[0]
    await act(async () => {
      ws.simulateClose()
    })

    expect(result.current.lifecycleState).toBe('completed')
    expect(onComplete).toHaveBeenCalled()

    const countAfter = MockWebSocket.instances.length
    await act(async () => {
      vi.advanceTimersByTime(30000)
    })
    expect(MockWebSocket.instances.length).toBe(countAfter)
  })

  it('should send heartbeat ping', async () => {
    renderHook(() => useScanWebSocket({ scanId: 'scan-123' }))

    await flushConnect()

    const ws = MockWebSocket.instances[0]
    expect(ws.readyState).toBe(1)
    const sendSpy = vi.spyOn(ws, 'send')

    await act(async () => {
      vi.advanceTimersByTime(15001)
    })

    expect(sendSpy).toHaveBeenCalledWith(
      expect.stringContaining('"type":"ping"')
    )
  })
})
