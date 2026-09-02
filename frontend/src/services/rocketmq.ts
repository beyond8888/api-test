/**
 * RocketMQ 5.x send API service — sends a single message to a RocketMQ topic via the backend.
 */
import { useApiClient } from '@/composables/useApiClient'
import { API_ROCKETMQ_SEND } from '@/utils/constants'

const { client } = useApiClient()

export type RocketMQMessageType = 'NORMAL' | 'FIFO' | 'DELAY' | 'TRANSACTION'

export interface RocketMQSendResult {
  message_id: string
  topic: string
}

export interface RocketMQSendPayload {
  endpoint: string
  instance_id: string
  access_key: string
  secret_key: string
  topic: string
  body: string
  message_type?: RocketMQMessageType
  message_group?: string
  delay_time?: number
  tag?: string
  keys?: string[]
}

/**
 * Send a single message to the given RocketMQ 5.x topic.
 * The response interceptor unwraps the envelope, so `resp.data` is the inner payload.
 */
export async function sendRocketMQMessage(payload: RocketMQSendPayload): Promise<RocketMQSendResult> {
  const resp = await client.post<RocketMQSendResult>(API_ROCKETMQ_SEND, payload)
  return resp.data
}
