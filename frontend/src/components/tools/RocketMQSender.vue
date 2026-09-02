<template>
  <div class="tool-panel">
    <div class="tool-desc">向阿里云 RocketMQ 5.x 实例发送测试消息，通过后端 gRPC 代理转发（支持普通 / 顺序 / 延时消息）</div>

    <div class="tool-form">
      <div class="form-row">
        <label class="field-label">接入点 (gRPC Endpoint)</label>
        <n-input v-model:value="endpoint" placeholder="rmq-cn-xxxx.rmq.aliyuncs.com:8080" />
      </div>

      <div class="form-row two-col">
        <div>
          <label class="field-label">实例 ID</label>
          <n-input v-model:value="instanceId" placeholder="rmq-cn-xxxx" />
        </div>
        <div>
          <label class="field-label">Topic</label>
          <n-input v-model:value="topic" placeholder="test-topic" />
        </div>
      </div>

      <div class="form-row two-col">
        <div>
          <label class="field-label">AccessKeyId</label>
          <n-input v-model:value="accessKey" placeholder="LTAI5txxxx" />
        </div>
        <div>
          <label class="field-label">AccessKeySecret</label>
          <n-input v-model:value="secretKey" type="password" show-password-on="click" placeholder="••••••••" />
        </div>
      </div>

      <div class="form-row two-col">
        <div>
          <label class="field-label">消息类型</label>
          <n-select v-model:value="messageType" :options="msgTypeOptions" />
        </div>
        <div v-if="messageType === 'FIFO'">
          <label class="field-label">消息分组 (MessageGroup)</label>
          <n-input v-model:value="messageGroup" placeholder="group-1" />
        </div>
        <div v-else-if="messageType === 'DELAY'">
          <label class="field-label">延时 (秒)</label>
          <n-input-number v-model:value="delayTime" :min="0" :max="604800" />
        </div>
      </div>

      <div class="form-row two-col">
        <div>
          <label class="field-label">Tag <span class="opt-tag">可选</span></label>
          <n-input v-model:value="tag" placeholder="tagA" />
        </div>
        <div>
          <label class="field-label">Keys <span class="opt-tag">可选，逗号分隔</span></label>
          <n-input v-model:value="keys" placeholder="key1,key2" />
        </div>
      </div>

      <div class="form-row">
        <label class="field-label">消息内容</label>
        <n-input
          v-model:value="payload"
          type="textarea"
          :rows="6"
          placeholder='{ "event": "test", "data": {} }'
          class="json-input"
        />
      </div>

      <div class="form-actions">
        <n-button type="primary" @click="send" :loading="sending">
          <template #icon>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          </template>
          发送消息
        </n-button>
      </div>
    </div>

    <!-- send history -->
    <div v-if="history.length" class="history-section">
      <div class="history-header">
        <span class="history-title">发送记录</span>
        <n-button size="tiny" quaternary @click="history = []">清空</n-button>
      </div>
      <div v-for="(h, i) in history" :key="i" class="history-item" :class="h.success ? 'success' : 'error'">
        <div class="hi-top">
          <span class="hi-topic">{{ h.topic }}</span>
          <span class="hi-time">{{ h.time }}</span>
          <span class="hi-status" :class="h.success ? 's-ok' : 's-err'">
            {{ h.success ? '成功' : '失败' }}
          </span>
        </div>
        <div class="hi-body">
          <code class="hi-code">{{ h.payload }}</code>
        </div>
        <div v-if="h.detail" class="hi-detail">{{ h.detail }}</div>
        <div v-if="h.error" class="hi-error">{{ h.error }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NInput, NInputNumber, NSelect, useMessage } from 'naive-ui'
import { sendRocketMQMessage, type RocketMQMessageType } from '@/services/rocketmq'

const message = useMessage()

const endpoint = ref('')
const instanceId = ref('')
const topic = ref('')
const accessKey = ref('')
const secretKey = ref('')
const messageType = ref<RocketMQMessageType>('NORMAL')
const messageGroup = ref('')
const delayTime = ref(0)
const tag = ref('')
const keys = ref('')
const payload = ref(`{\n  "event": "test",\n  "timestamp": ${Date.now()}\n}`)
const sending = ref(false)

const msgTypeOptions = [
  { label: '普通消息 (NORMAL)', value: 'NORMAL' },
  { label: '顺序消息 (FIFO)', value: 'FIFO' },
  { label: '延时消息 (DELAY)', value: 'DELAY' },
  { label: '事务消息 (TRANSACTION)', value: 'TRANSACTION' },
]

interface HistoryItem {
  topic: string
  payload: string
  time: string
  success: boolean
  detail?: string
  error?: string
}
const history = ref<HistoryItem[]>([])

async function send() {
  if (!endpoint.value.trim() || !instanceId.value.trim() || !topic.value.trim()
    || !accessKey.value.trim() || !secretKey.value.trim()) {
    message.warning('请填写接入点、实例ID、Topic、AccessKey 与 SecretKey')
    return
  }

  sending.value = true
  const now = new Date().toLocaleTimeString('zh-CN', { hour12: false })

  try {
    const res = await sendRocketMQMessage({
      endpoint: endpoint.value.trim(),
      instance_id: instanceId.value.trim(),
      topic: topic.value.trim(),
      access_key: accessKey.value.trim(),
      secret_key: secretKey.value,
      body: payload.value,
      message_type: messageType.value,
      message_group: messageType.value === 'FIFO' ? messageGroup.value.trim() : undefined,
      delay_time: messageType.value === 'DELAY' ? (delayTime.value || 0) : undefined,
      tag: tag.value.trim() || undefined,
      keys: keys.value.trim() ? keys.value.split(',').map(k => k.trim()).filter(Boolean) : undefined,
    })

    history.value.unshift({
      topic: res.topic,
      payload: payload.value,
      time: now,
      success: true,
      detail: `messageId=${res.message_id}`,
    })
    message.success('消息发送成功')
  } catch (e: any) {
    history.value.unshift({
      topic: topic.value,
      payload: payload.value,
      time: now,
      success: false,
      error: e?.message || '发送失败',
    })
    message.error(`发送失败: ${e?.message || '未知错误'}`)
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.tool-panel { padding: 0; }
.tool-desc {
  font-size: 13px; color: var(--text-muted);
  margin-bottom: 24px; line-height: 1.5;
}
.tool-form {
  background: var(--bg-subtle);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 20px;
}
.form-row { margin-bottom: 16px; }
.form-row.two-col {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
}
.form-actions { margin-bottom: 0; padding-top: 4px; }
.field-label {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; font-weight: 600;
  color: var(--text-secondary); margin-bottom: 6px;
}
.opt-tag {
  font-size: 10px; font-weight: 400;
  color: var(--text-muted);
  background: rgba(255,255,255,0.05);
  padding: 1px 6px; border-radius: 4px;
}
.json-input :deep(textarea) {
  font-family: var(--font-mono);
  font-size: 13px;
}
.history-section { margin-top: 24px; }
.history-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px;
}
.history-title {
  font-size: 14px; font-weight: 600; color: var(--text);
}
.history-item {
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  margin-bottom: 8px;
}
.history-item.success { border-left: 3px solid var(--success); }
.history-item.error   { border-left: 3px solid var(--error); }
.hi-top {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 6px;
}
.hi-topic {
  font-size: 13px; font-weight: 600; color: var(--text);
}
.hi-time {
  font-size: 11px; color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.hi-status { font-size: 11px; font-weight: 600; }
.s-ok  { color: var(--success); }
.s-err { color: var(--error); }
.hi-body {
  background: var(--code-bg);
  border-radius: 4px;
  padding: 8px 12px;
  max-height: 200px; overflow: auto;
}
.hi-detail {
  font-size: 11px; color: var(--text-muted);
  margin-top: 6px;
  font-family: var(--font-mono);
}
.hi-code {
  font-size: 12px; color: var(--code-text);
  font-family: var(--font-mono);
  white-space: pre-wrap; word-break: break-all;
}
.hi-error {
  font-size: 12px; color: var(--error);
  margin-top: 6px;
}
</style>
