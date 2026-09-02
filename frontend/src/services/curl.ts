/**
 * Curl parse API service — centralized HTTP layer for the curl parse endpoint.
 */
import { useApiClient } from '@/composables/useApiClient'
import { API_PARSE_CURL } from '@/utils/constants'
import type { ParseResult } from '@/types'

const { client } = useApiClient()

/**
 * Parse a curl command into a structured request config.
 *
 * @param curlCommand Raw curl command string
 * @returns Parsed result
 */
export async function parseCurl(curlCommand: string): Promise<ParseResult> {
  const resp = await client.post<ParseResult>(API_PARSE_CURL, {
    curl_command: curlCommand,
  })
  return resp.data
}
