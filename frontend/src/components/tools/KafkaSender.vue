<template>
  <div class="tool-panel">
    <div class="tool-desc">向 Kafka Topic 发送测试消息，通过后端代理转发</div>

    <div class="tool-form">
      <div class="form-row">
        <label class="field-label">Broker 地址</label>
        <n-input v-model:value="broker" placeholder="localhost:9092" />
      </div>

      <div class="form-row">
        <label class="field-label">Topic</label>
        <n-input v-model:value="topic" placeholder="test-topic" />
      </div>

      <div class="form-row">
        <label class="field-label">Key <span class="opt-tag">可选</span></label>
        <n-input v-model:value="key" placeholder="message-key" />
      </div>

      <div class="form-row">
        <label class="field-label">消息内容</label>
        <n-input
          v-model:value="payload"
          type="textarea"
          :rows="6"
          placeholder="{&quot;event&quot;: &quot;test&quot;, &quot;data&quot;: {}}"
          class="json-input"
        />
      </div>

      <div class="form-row">
        <label class="field-label">
          Headers <span class="opt-tag">可选</span>
          <n-button size="tiny" quaternary @click="addHeader" class="add-hdr-btn">
            + 添加
          </n-button>
        </label>
        <div v-for="(h, idx) in headers" :key="idx" class="header-row">
          <n-input v-model:value="h.key" placeholder="Key" size="small" class="hdr-input" />
          <n-input v-model:value="h.value" placeholder="Value" size="small" class="hdr-input" />
          <n-button size="tiny" quaternary type="error" @click="headers.splice(idx, 1)">
            <template #icon>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </template>
          </n-button>
        </div>
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
import { NButton, NInput, useMessage } from 'naive-ui'
import { sendKafkaMessage } from '@/services/kafka'

const message = useMessage()

const broker = ref('localhost:9092')
const topic = ref('')
const key = ref('')
const payload = ref(`{\n  "event": "test",\n  "timestamp": ${Date.now()}\n}`)
const sending = ref(false)

interface HeaderPair { key: string; value: string }
const headers = ref<HeaderPair[]>([])

interface HistoryItem {
  topic: string
  payload: string
  time: string
  success: boolean
  detail?: string
  error?: string
}

const history = ref<HistoryItem[]>([])

function addHeader() {
  headers.value.push({ key: '', value: '' })
}

async function send() {
  if (!topic.value.trim()) {
    message.warning('请输入 Topic')
    return
  }

  sending.value = true
  const now = new Date().toLocaleTimeString('zh-CN', { hour12: false })

  try {
    const headerObj: Record<string, string> = {}
    headers.value.forEach(h => {
      if (h.key.trim()) headerObj[h.key.trim()] = h.value
    })

    const res = await sendKafkaMessage({
      broker: broker.value,
      topic: topic.value,
      key: key.value || undefined,
      value: payload.value,
      headers: headerObj,
    })

    history.value.unshift({
      topic: res.topic,
      payload: payload.value,
      time: now,
      success: true,
      detail: `partition=${res.partition} offset=${res.offset}`,
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
.add-hdr-btn { margin-left: auto; font-size: 11px; }
.header-row {
  display: flex; gap: 8px; margin-bottom: 8px; align-items: center;
}
.hdr-input { flex: 1; }

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
