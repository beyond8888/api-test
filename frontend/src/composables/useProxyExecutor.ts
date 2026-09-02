import type { RequestConfig, ResponseData, ScriptTestResult, KV, AuthConfig, MultipartFile } from '@/types'
import type { HttpMethod } from '@/utils/constants'
import { isCancel } from 'axios'
import { executePreRequestScript, executePostResponseScript } from '@/utils/scriptEngine'
import { buildProxyPayload } from '@/utils/http'
import { proxyRequest, ProxyError } from '@/services/proxy'
import { logger } from '@/utils/logger'

/** The request snapshot as it was actually sent (variables already resolved). */
export interface ResolvedRequest {
  method: HttpMethod
  url: string
  headers: KV[]
  queryParams: KV[]
  body: string
  bodyType: RequestConfig['bodyType']
  rawFormat: RequestConfig['rawFormat']
  multipartFields: KV[]
  multipartFiles: MultipartFile[]
  auth: AuthConfig
}

/** Result of `execute()` — the response (if any) plus the resolved request. */
export interface ExecuteResult {
  response: ResponseData | null
  request: ResolvedRequest
}

export interface ExecutorStore {
  isLoading: boolean
  response: ResponseData | null
  responseError: string | null
  testResults: ScriptTestResult[] | null
}

/**
 * Proxy request executor.
 *
 * Concurrency model — single-flight: each `execute()` aborts the previously
 * in-flight request (Postman-style Stop / supersede), so this is designed for
 * ONE active request at a time. It writes progress/results into the provided
 * store, which is normally the app-wide request store — therefore results
 * only ever reflect the ACTIVE tab (tab switching preserves each tab's result
 * via EditorSnapshot snapshot/restore, so there is no cross-tab leakage).
 */
export function useProxyExecutor(store: ExecutorStore) {
  // AbortController for request deduplication — abort previous in-flight request
  let _abortController: AbortController | null = null
  // Set when the user manually cancels (Stop button), so we can surface a
  // "Request canceled" message instead of silently swallowing the abort.
  let _manualAbort = false

  /** Cancel the currently in-flight request (Postman-style Stop button). */
  function abort() {
    if (_abortController) {
      _manualAbort = true
      _abortController.abort()
    }
  }

  async function execute(
    config: RequestConfig,
    opts?: {
      preRequestScript?: string
      postResponseScript?: string
      envVariables?: Record<string, string>
      onEnvSet?: (key: string, value: string) => void
      timeout?: number
    },
  ): Promise<ExecuteResult | null> {
    // Abort any previous in-flight request to prevent race conditions
    if (_abortController) _abortController.abort()
    _abortController = new AbortController()
    _manualAbort = false

    store.isLoading = true
    store.responseError = null
    store.response = null
    store.testResults = []

    const envVars = opts?.envVariables || {}

    // ---- Pre-request Script ----
    let runtimeVars: Record<string, any> = {}
    if (opts?.preRequestScript) {
      try {
        const preResult = executePreRequestScript(
          { config, envVariables: envVars },
          opts.preRequestScript,
        )
        runtimeVars = preResult.variables
      } catch (e: unknown) {
        store.responseError = `Pre-request script error: ${e instanceof Error ? e.message : String(e)}`
        store.isLoading = false
        _abortController = null
        return null
      }
    }

    // Merge runtime + environment variables for replacement
    const allVars = { ...envVars, ...runtimeVars }

    // Build the proxy payload (headers + auth + body / multipart)
    const { payload, resolvedUrl } = buildProxyPayload(config, allVars, { timeout: opts?.timeout })

    // Snapshot the *resolved* request (variables already substituted) so history
    // stores the actual values that were sent — unresolvable `{{vars}}` remain
    // untouched because buildProxyPayload re-applies applyVariables on each field.
    const resolvedRequest: ResolvedRequest = {
      method: config.method,
      url: payload.url,
      headers: Object.entries(payload.headers || {}).map(([key, value], i) => ({
        id: `h${i}`,
        key,
        value: String(value),
        enabled: true,
      })),
      queryParams: Object.entries(payload.query_params || {}).map(([key, value], i) => ({
        id: `q${i}`,
        key,
        value: String(value),
        enabled: true,
      })),
      body: config.bodyType === 'multipart'
        ? config.multipartFields
            .filter((f) => f.enabled && f.key)
            .map((f) => `${f.key}=${f.value}`)
            .join('&')
        : (payload.body ?? ''),
      bodyType: config.bodyType,
      rawFormat: config.rawFormat,
      multipartFields: config.multipartFields,
      multipartFiles: config.multipartFiles,
      auth: config.auth,
    }

    const SENSITIVE_HEADERS = [
      'authorization',
      'cookie',
      'x-api-key',
      'x-auth-token',
      'proxy-authorization',
    ]
    const safeHeaders = Object.fromEntries(
      Object.entries(payload.headers || {}).map(([key, value]) => [
        key,
        SENSITIVE_HEADERS.includes(key.toLowerCase()) ? '[redacted]' : value,
      ]),
    )
    logger.debug(`[Proxy] ${config.method} ${resolvedUrl}`, { headers: safeHeaders })
    if (config.bodyType !== 'none' && config.body) {
      // Avoid logging request bodies (may contain credentials/secrets).
      logger.debug(`[Proxy] Body: type=${config.bodyType}, length=${config.body.length}`)
    }

    // Execute the actual request
    try {
      const result = await proxyRequest(payload, { signal: _abortController.signal })

      // ---- Post-response Script ----
      if (opts?.postResponseScript) {
        try {
          const postResult = executePostResponseScript(
            {
              config,
              response: result,
              envVariables: envVars,
              envWriter: (key: string, value: string) => {
                if (opts.onEnvSet) opts.onEnvSet(key, value)
              },
            },
            opts.postResponseScript,
          )
          store.testResults = postResult.testResults
        } catch (e: unknown) {
          logger.error('[Post-response script error]', e instanceof Error ? e.message : String(e))
        }
      }

      logger.debug(`[Proxy] Response ${result.status} ${result.timing}ms ${result.size}B`)
      store.response = result
      store.isLoading = false
      _abortController = null
      return { response: result, request: resolvedRequest }
    } catch (err: unknown) {
      // Aborted (manual Stop OR superseded by a newer request) — axios rejects
      // with a CanceledError, not a native AbortError.
      if (isCancel(err)) {
        if (_manualAbort) {
          // User clicked Stop — show a clear canceled state
          store.responseError = 'Request canceled'
          store.isLoading = false
          _abortController = null
          _manualAbort = false
          return null
        }
        logger.debug('[Proxy] Request aborted (superseded by newer request)')
        return null
      }
      // Distinguish ProxyError (from upstream) vs transport error
      if (err instanceof ProxyError) {
        store.responseError = err.message
        logger.error('[Proxy] Error:', err.message, `(${err.timing}ms)`)
      } else {
        // Extract error message from various response shapes:
        //   {data: {error: "..."}} (proxy error) or {message: "..."} (envelope) or {error: "..."}
        const respData = (err && typeof err === 'object' && 'response' in err)
          ? (err as { response?: { data?: any } }).response?.data
          : null
        const msg = respData?.data?.error || respData?.message || respData?.error
          || (err instanceof Error ? err.message : 'Proxy request failed')
        store.responseError = msg
        logger.error('[Proxy] Failed:', store.responseError)
      }
      store.isLoading = false
      _abortController = null
      // Even on transport/proxy errors, keep the resolved request so it can be
      // stored in history (showing what was actually attempted).
      return { response: null, request: resolvedRequest }
    }
  }

  return { execute, abort }
}
