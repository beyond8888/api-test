import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useProxyExecutor, type ExecutorStore } from './useProxyExecutor'

import { proxyRequest } from '@/services/proxy'

// Mock the network layer so we control abort behavior without a live server.
vi.mock('@/services/proxy', () => ({
  ProxyError: class ProxyError extends Error {
    timing?: number
    constructor(message: string, timing?: number) {
      super(message)
      this.name = 'ProxyError'
      this.timing = timing
    }
  },
  proxyRequest: vi.fn(),
}))

function makeStore(): ExecutorStore {
  return { isLoading: false, response: null, responseError: null, testResults: [] }
}

// Minimal but complete RequestConfig so buildProxyPayload doesn't choke.
function makeConfig(url: string) {
  return {
    method: 'GET',
    url,
    headers: [] as Array<{ key: string; value: string; enabled: boolean }>,
    queryParams: [] as Array<{ key: string; value: string; enabled: boolean }>,
    body: '',
    bodyType: 'none',
    auth: { type: 'none' },
    multipartFields: [] as Array<{ key: string; value: string; enabled: boolean }>,
    multipartFiles: [] as Array<{ name: string; field: string; type: string; dataUrl: string }>,
  } as any
}

// Simulates an in-flight request: hangs until the signal aborts (like axios
// cancelling on AbortSignal). axios rejects with a CanceledError (name
// 'CanceledError', with __CANCEL__ = true) — NOT a native AbortError.
function abortableRequest(signal: AbortSignal, resolveWith?: unknown) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => resolve(resolveWith), 60_000)
    signal.addEventListener('abort', () => {
      clearTimeout(timer)
      const err = new Error('canceled')
      err.name = 'CanceledError'
      ;(err as any).__CANCEL__ = true
      reject(err)
    })
  })
}

describe('useProxyExecutor — Stop / abort behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('flags "Request canceled" when abort() is called (Stop button)', async () => {
    const store = makeStore()
    const { execute, abort } = useProxyExecutor(store)

    ;(proxyRequest as any).mockImplementation((_p: unknown, opts: { signal: AbortSignal }) =>
      abortableRequest(opts.signal),
    )

    const p = execute(makeConfig('http://example.com'))
    expect(store.isLoading).toBe(true)

    abort() // user clicks Stop
    await p

    expect(store.responseError).toBe('Request canceled')
    expect(store.isLoading).toBe(false)
  })

  it('does NOT show "Request canceled" when a newer request supersedes it', async () => {
    const store = makeStore()
    const { execute, abort } = useProxyExecutor(store)

    ;(proxyRequest as any).mockImplementation((_p: unknown, opts: { signal: AbortSignal }) =>
      abortableRequest(opts.signal),
    )

    const p1 = execute(makeConfig('http://a.com'))
    // A second send aborts the first one (dedup path) — must stay silent.
    const p2 = execute(makeConfig('http://b.com'))

    await p1
    expect(store.responseError).not.toBe('Request canceled')
    expect(store.responseError).toBeNull()

    // Clean up the still-pending second request.
    abort()
    await p2
  })

  it('succeeds normally when not aborted and stores the response', async () => {
    const store = makeStore()
    const { execute } = useProxyExecutor(store)
    const fakeResponse = { status: 200, statusText: 'OK', headers: {}, body: 'ok', bodyType: 'text', size: 2, timing: 5 }

    ;(proxyRequest as any).mockResolvedValue(fakeResponse)

    const result = await execute(makeConfig('http://a.com'))
    expect(result).toEqual(fakeResponse)
    expect(store.response).toEqual(fakeResponse)
    expect(store.responseError).toBeNull()
    expect(store.isLoading).toBe(false)
  })

  it('abort() before any request is a no-op (no throw)', () => {
    const store = makeStore()
    const { abort } = useProxyExecutor(store)
    expect(() => abort()).not.toThrow()
    expect(store.isLoading).toBe(false)
  })
})
