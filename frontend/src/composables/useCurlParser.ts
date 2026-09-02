import { ref } from 'vue'
import type { ParseResult } from '@/types'
import { parseCurl } from '@/services/curl'

export function useCurlParser() {
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const result = ref<ParseResult | null>(null)

  async function parse(curlCommand: string): Promise<ParseResult | null> {
    isLoading.value = true
    error.value = null
    result.value = null

    try {
      const data = await parseCurl(curlCommand)
      result.value = data
      return data
    } catch (err: unknown) {
      const msg
        = err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { message?: string } } }).response?.data?.message
          : ''
      error.value = msg || (err instanceof Error ? err.message : 'Failed to parse curl command')
      return null
    } finally {
      isLoading.value = false
    }
  }

  return { isLoading, error, result, parse }
}
