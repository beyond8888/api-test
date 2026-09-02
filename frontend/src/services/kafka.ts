/**
 * Kafka send API service — sends a single message to a Kafka topic via the backend.
 */
import { useApiClient } from '@/composables/useApiClient'
import { API_KAFKA_SEND } from '@/utils/constants'

const { client } = useApiClient()

export interface KafkaSendResult {
  topic: string
  partition: number
  offset: number
}

export interface KafkaSendPayload {
  broker: string
  topic: string
  value: string
  key?: string
  headers?: Record<string, string>
  timeout?: number
}

/**
 * Produce a single message to the given Kafka topic.
 * The response interceptor unwraps the envelope, so `resp.data` is the inner payload.
 */
export async function sendKafkaMessage(payload: KafkaSendPayload): Promise<KafkaSendResult> {
  const resp = await client.post<KafkaSendResult>(API_KAFKA_SEND, payload)
  return resp.data
}
