/**
 * Proxy API service — centralized HTTP layer for the proxy endpoint.
 *
 * All proxy requests go through this module so composables
 * (useProxyExecutor) don't touch axios directly.
 */
import { useApiClient } from '@/composables/useApiClient'
import { API_PROXY } from '@/utils/constants'
import type { ResponseData } from '@/types'
import { parseProxyResponse, ProxyError } from '@/utils/http'

const { client } = useApiClient()

/**
 * Send a proxy request to the backend.
 *
 * @param payload  The proxy payload built by buildProxyPayload()
 * @param opts     Optional config: { signal?: AbortSignal } for cancellation
 * @param opts.signal Optional AbortSignal for request cancellation
 * @returns Parsed ResponseData
 * @throws ProxyError if upstream returned an error
 */
export async function proxyRequest(
  payload: Record<string, any>,
  opts?: { signal?: AbortSignal },
): Promise<ResponseData> {
  const resp = await client.post(API_PROXY, payload, { signal: opts?.signal })
  return parseProxyResponse(resp.data)
}

export { ProxyError }
