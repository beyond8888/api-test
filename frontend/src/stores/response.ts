import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { RequestConfig, ResponseData, ScriptTestResult } from '@/types'

/**
 * Holds request *result* state (response, errors, in-flight flag, test results,
 * and the resolved request snapshot actually sent). This is intentionally kept
 * separate from `requestStore`, which is the live editor mirror / tab snapshot.
 *
 * Splitting the two means a request's result is owned by one dedicated store
 * regardless of which tab triggered it, instead of being mixed into the editor
 * state that the tab-snapshot mechanism saves and restores.
 */
export const useResponseStore = defineStore('response', () => {
  const response = ref<ResponseData | null>(null)
  const responseError = ref<string | null>(null)
  const sentRequest = ref<RequestConfig | null>(null)
  const isLoading = ref(false)
  const testResults = ref<ScriptTestResult[] | null>(null)

  function setResponse(
    resp: ResponseData | null,
    error: string | null = null,
    req: RequestConfig | null = null,
  ): void {
    response.value = resp
    responseError.value = error
    if (req !== null) sentRequest.value = req
  }

  function setSentRequest(req: RequestConfig): void {
    sentRequest.value = req
  }

  function setLoading(loading: boolean): void {
    isLoading.value = loading
  }

  function setTestResults(results: ScriptTestResult[] | null): void {
    testResults.value = results
  }

  function reset(): void {
    response.value = null
    responseError.value = null
    sentRequest.value = null
    isLoading.value = false
    testResults.value = null
  }

  return {
    response,
    responseError,
    sentRequest,
    isLoading,
    testResults,
    setResponse,
    setSentRequest,
    setLoading,
    setTestResults,
    reset,
  }
})
