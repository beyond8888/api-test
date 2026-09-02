<template>
  <div class="req-detail">
    <!-- General -->
    <section class="rd-section">
      <div class="rd-title">General</div>
      <div class="rd-grid">
        <div class="rd-cell" v-if="request.url">
          <span class="rd-k">Request URL</span>
          <span class="rd-v url">{{ request.url }}</span>
        </div>
        <div class="rd-cell" v-if="request.method">
          <span class="rd-k">Request Method</span>
          <span class="rd-v method" :class="`m-${request.method.toLowerCase()}`">{{ request.method }}</span>
        </div>
        <div class="rd-cell" v-if="response">
          <span class="rd-k">Status Code</span>
          <span class="rd-v">
            <span class="rd-status" :class="statusClass(response.status)">{{ response.status }}</span>
            {{ response.statusText }}
          </span>
        </div>
        <div class="rd-cell" v-if="response">
          <span class="rd-k">Referrer Policy</span>
          <span class="rd-v">strict-origin-when-cross-origin</span>
        </div>
      </div>
    </section>

    <!-- Response Headers -->
    <section class="rd-section" v-if="response && responseHeaders.length">
      <div class="rd-title collapsible" @click="respOpen = !respOpen">
        <span class="rd-triangle" :class="{ open: respOpen }">&#9656;</span>
        Response Headers
        <button class="rd-viewsrc" @click.stop="respSource = !respSource">
          {{ respSource ? 'view parsed' : 'view source' }}
        </button>
      </div>
      <div v-show="respOpen">
        <pre v-if="respSource" class="rd-source">{{ responseHeadersSource }}</pre>
        <div v-else class="rd-table">
          <div v-for="(h, i) in responseHeaders" :key="i" class="rd-tr">
            <span class="rd-td key">{{ h.key }}</span>
            <span class="rd-td value">{{ h.value }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Request Headers -->
    <section class="rd-section">
      <div class="rd-title collapsible" @click="reqOpen = !reqOpen">
        <span class="rd-triangle" :class="{ open: reqOpen }">&#9656;</span>
        Request Headers
        <button class="rd-viewsrc" @click.stop="reqSource = !reqSource">
          {{ reqSource ? 'view parsed' : 'view source' }}
        </button>
      </div>
      <div v-show="reqOpen">
        <pre v-if="reqSource" class="rd-source">{{ requestHeadersSource }}</pre>
        <div v-else class="rd-table">
          <div v-for="(h, i) in headers" :key="i" class="rd-tr">
            <span class="rd-td key">{{ h.key }}</span>
            <span class="rd-td value">{{ h.value }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Query String Parameters -->
    <section class="rd-section" v-if="queryParams.length">
      <div class="rd-title">
        Query String Parameters
        <button class="rd-viewsrc" @click="qSource = !qSource">
          {{ qSource ? 'view parsed' : 'view source' }}
        </button>
      </div>
      <pre v-if="qSource" class="rd-source">{{ querySource }}</pre>
      <div v-else class="rd-table">
        <div v-for="(kv, i) in queryParams" :key="i" class="rd-tr">
          <span class="rd-td key">{{ kv.key }}</span>
          <span class="rd-td value">{{ kv.value }}</span>
        </div>
      </div>
    </section>

    <!-- Form Data / Request Payload -->
    <section class="rd-section" v-if="payloadRows.length || bodyType">
      <div class="rd-title">
        {{ payloadRows.length ? 'Form Data' : 'Request Payload' }}
        <button class="rd-viewsrc" @click="pSource = !pSource" v-if="!payloadRows.length || request.body">
          {{ pSource ? 'view parsed' : 'view source' }}
        </button>
      </div>

      <!-- form / multipart as params table OR source view -->
      <pre v-if="pSource && (payloadRows.length ? request.body : true)" class="rd-source">{{ sourceBody }}</pre>
      <div v-else-if="payloadRows.length" class="rd-table">
        <div v-for="(row, i) in payloadRows" :key="i" class="rd-tr">
          <span class="rd-td key">{{ row.key }}</span>
          <span class="rd-td value">{{ row.value }}</span>
        </div>
      </div>
      <ResponseBody
        v-else
        title=""
        :body="request.body"
        :body-type="bodyType"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import ResponseBody from './ResponseBody.vue'
import type { KV, RequestConfig, ResponseData } from '@/types'

const props = defineProps<{
  request: RequestConfig
  response?: ResponseData | null
}>()

const reqSource = ref(false)
const respSource = ref(false)
const qSource = ref(false)
const pSource = ref(false)

const headers = computed<KV[]>(
  () => (props.request.headers ?? []).filter((kv) => kv.enabled !== false)
)
const queryParams = computed<KV[]>(
  () => (props.request.queryParams ?? []).filter((kv) => kv.enabled !== false)
)

// Collapsible state for header sections. Auto-collapse when there are many
// headers so long lists are easier to scan.
const respOpen = ref((props.response?.headers ? Object.keys(props.response.headers).length : 0) <= 6)
const reqOpen = ref(headers.value.length <= 6)

const responseHeaders = computed<{ key: string; value: string }[]>(() => {
  const h = props.response?.headers
  if (!h) return []
  if (Array.isArray(h))
    return h.map((kv: { key: string; value: string }) => ({ key: String(kv.key), value: String(kv.value) }))
  if (typeof h === 'object')
    return Object.entries(h).map(([k, v]) => ({ key: k, value: String(v) }))
  return []
})
const requestHeadersSource = computed(() =>
  headers.value.map((h) => `${h.key}: ${h.value}`).join('\n')
)
const responseHeadersSource = computed(() =>
  responseHeaders.value.map((h) => `${h.key}: ${h.value}`).join('\n')
)
const querySource = computed(() =>
  queryParams.value.map((kv) => `${kv.key}: ${kv.value}`).join('\n')
)

// form / multipart parameters
const payloadRows = computed<{ key: string; value: string }[]>(() => {
  const type = props.request.bodyType
  if (type === 'multipart') {
    return (props.request.multipartFields ?? [])
      .filter((f: KV) => f.enabled !== false && f.key)
      .map((f: KV) => ({ key: f.key, value: f.value }))
  }
  if (type === 'form') {
    const body = props.request.body || ''
    if (!body) return []
    return body
      .split('&')
      .map((pair) => pair.split('='))
      .filter(([k]) => k)
      .map(([k, v = '']) => ({
        key: decodeURIComponent(k),
        value: decodeURIComponent(v),
      }))
  }
  return []
})

const bodyType = computed<'json' | 'html' | 'xml' | 'text'>(() => {
  const type = props.request.bodyType
  if (!type || type === 'none') return 'text'
  if (type === 'json') return 'json'
  if (type === 'raw') return 'text'
  if (type === 'form' || type === 'multipart') return 'text'
  return 'text'
})

const sourceBody = computed(() => props.request.body || '')

function statusClass(status?: number): string {
  if (!status) return ''
  if (status >= 200 && status < 300) return 'ok'
  if (status >= 300 && status < 400) return 'redirect'
  if (status >= 400 && status < 500) return 'client'
  if (status >= 500) return 'server'
  return ''
}
</script>

<style scoped>
.req-detail { padding: 4px 0 14px; }
.rd-section {
  border-bottom: 1px solid var(--border);
  padding: 10px 16px;
}
.rd-section:last-child { border-bottom: none; }
.rd-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.rd-title.collapsible {
  cursor: pointer;
  user-select: none;
}
.rd-title.collapsible:hover { color: var(--text-secondary); }
.rd-triangle {
  display: inline-block;
  font-size: 9px;
  color: var(--text-muted);
  transition: transform 0.12s ease;
  transform: rotate(0deg);
}
.rd-triangle.open {
  transform: rotate(90deg);
}
.rd-viewsrc {
  margin-left: auto;
  font-size: 11px;
  color: #1a73e8;
  background: none;
  border: none;
  cursor: pointer;
  font-weight: 600;
  padding: 0;
}
.rd-viewsrc:hover { text-decoration: underline; }

.rd-grid { display: flex; flex-direction: column; gap: 4px; }
.rd-cell {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 12px;
}
.rd-k {
  flex-shrink: 0;
  min-width: 130px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.rd-v {
  color: var(--text);
  font-family: var(--font-mono);
  word-break: break-all;
}
.rd-v.url { color: #1a73e8; }
.rd-v.method { font-weight: 700; }
.rd-v.m-get { color: #34d399; }
.rd-v.m-post { color: #60a5fa; }
.rd-v.m-put { color: #fbbf24; }
.rd-v.m-delete { color: #f87171; }
.rd-v.m-patch { color: #c084fc; }
.rd-status { font-weight: 700; }
.rd-status.ok { color: #34d399; }
.rd-status.redirect { color: #60a5fa; }
.rd-status.client { color: #fbbf24; }
.rd-status.server { color: #f87171; }

.rd-table {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.rd-tr {
  display: flex;
  border-bottom: 1px solid var(--border);
}
.rd-tr:last-child { border-bottom: none; }
.rd-tr:nth-child(odd) { background: var(--bg-subtle); }
.rd-td {
  padding: 6px 12px;
  font-size: 12px;
  font-family: var(--font-mono);
  word-break: break-all;
}
.rd-td.key {
  flex: 0 0 220px;
  color: var(--text-secondary);
  font-weight: 600;
  border-right: 1px solid var(--border);
}
.rd-td.value { flex: 1; color: var(--text); }

.rd-source {
  margin: 0;
  padding: 10px 12px;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.6;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--bg-subtle);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}
</style>
