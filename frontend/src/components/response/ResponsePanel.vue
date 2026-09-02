<template>
  <div class="response-panel">
    <!-- Mode switch (always visible so History is reachable even before a send) -->
    <div class="panel-head">
      <div class="mode-switch">
        <button class="mode-btn" :class="{ active: mode === 'response' }" @click="setMode('response')">Response</button>
        <button class="mode-btn" :class="{ active: mode === 'history' }" @click="setMode('history')">
          History<span v-if="historyCount" class="mode-badge">{{ historyCount }}</span>
        </button>
      </div>
      <button v-if="mode === 'history' && viewing" class="back-btn" @click="backToList">&#8592; Back to history</button>
    </div>

    <!-- RESPONSE MODE: states -->
    <template v-if="mode === 'response'">
      <div v-if="!responseStore.response && !responseStore.responseError && !responseStore.isLoading" class="panel-empty">
        <div class="empty-illustration">&#8593;</div>
        <div class="empty-text">Send a request to get a response</div>
      </div>
      <div v-if="responseStore.isLoading" class="panel-loading">
        <span class="loading-dot"></span>
        <span>Sending request...</span>
      </div>
      <div v-if="responseStore.responseError" class="panel-error">
        <div class="error-icon">!</div>
        <div>
          <div class="error-title">Request Failed</div>
          <div class="error-body">{{ responseStore.responseError }}</div>
        </div>
      </div>
    </template>

    <!-- BODY (shared: live response in Response mode, or a viewed history response) -->
    <template v-if="displayResp || viewing">
      <!-- Request summary shown when a request context exists -->
      <div v-if="displayRequest" class="req-summary">
        <span class="req-method" :class="`pill-${(displayRequest.method || 'GET').toLowerCase()}`">{{ displayRequest.method }}</span>
        <span class="req-url">{{ displayRequest.url }}</span>
      </div>

      <div class="status-bar" v-if="displayResp">
        <div class="status-left">
          <span class="status-code" :class="statusClass">{{ displayResp.status }}</span>
          <span class="status-label">{{ displayResp.statusText }}</span>
        </div>
        <div class="status-meta">
          <span>{{ displayResp.timing }}ms</span>
          <span>{{ formatSize(displayResp.size) }}</span>
        </div>
        <div class="status-actions" v-if="mode === 'response'">
          <button class="action-chip" @click="handleSave" title="Save to Collection">
            <span class="chip-icon">+</span>
            Save
          </button>
        </div>
      </div>

      <div class="response-tabs">
        <n-tabs type="bar" size="small" :default-value="'response'" v-model:value="activeTab">
          <n-tab-pane name="headers" tab="Headers">
            <div class="rd-pane">
              <RequestDetail v-if="displayRequest" :request="displayRequest" :response="displayResp" />
              <div v-else class="panel-empty">
                <div class="empty-illustration">&#8212;</div>
                <div class="empty-text">No request context</div>
              </div>
            </div>
          </n-tab-pane>
          <n-tab-pane name="response" tab="Response">
            <div class="rd-pane">
              <ResponseBody
                v-if="displayResp"
                :body="displayResp.body"
                :body-type="displayResp.bodyType"
              />
              <div v-else class="panel-empty">
                <div class="empty-illustration">&#8212;</div>
                <div class="empty-text">No response data</div>
              </div>
            </div>
          </n-tab-pane>
          <n-tab-pane name="tests" tab="Tests">
            <div class="rd-pane">
              <div v-if="displayTests?.length" class="test-list">
                <div
                  v-for="t in displayTests"
                  :key="t.name"
                  class="test-row"
                  :class="{ pass: t.passed, fail: !t.passed }"
                >
                  <span class="test-icon">{{ t.passed ? '&#10003;' : '&#10007;' }}</span>
                  <span class="test-name">{{ t.name }}</span>
                  <span v-if="!t.passed && t.error" class="test-error">{{ t.error }}</span>
                </div>
              </div>
              <div v-else class="panel-empty">
                <div class="empty-illustration">&#8212;</div>
                <div class="empty-text">No tests</div>
              </div>
            </div>
          </n-tab-pane>
        </n-tabs>
      </div>
    </template>

    <!-- HISTORY MODE -->
    <template v-if="mode === 'history'">
      <!-- Drilled into a single entry that has no response -->
      <div v-if="viewing && !viewing.response" class="panel-empty">
        <div class="empty-illustration">&#8212;</div>
        <div class="empty-text">This run has no response data (the request may have failed)</div>
      </div>

      <!-- List of recent runs (global) -->
      <div v-else-if="!viewing" class="history-list">
        <div
          v-for="h in historyEntries"
          :key="h.id"
          class="hist-row"
          @click="openHistory(h)"
        >
          <span class="h-method" :class="`pill-${(h.request.method || 'GET').toLowerCase()}`">{{ h.request.method }}</span>
          <span class="h-url" :title="h.request.url">{{ h.request.url }}</span>
          <span class="h-status" :class="respStatusClass(h.response?.status)">{{ h.response ? h.response.status : '—' }}</span>
          <span class="h-time">{{ formatRel(h.timestamp) }}</span>
        </div>
        <div v-if="historyStore.hasMore" class="history-loadmore">
          <n-button text size="small" :loading="historyStore.loading" @click="historyStore.loadMore()">
            Load more ({{ historyStore.total - historyEntries.length }} remaining)
          </n-button>
        </div>
        <div v-if="!historyEntries.length" class="panel-empty">
          <div class="empty-illustration">&#128340;</div>
          <div class="empty-text">No history yet — send a request to record it</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NTabs, NTabPane, NButton, useMessage } from 'naive-ui'
import { useRequestStore } from '../../stores/request'
import { useResponseStore } from '../../stores/response'
import { useHistoryStore } from '../../stores/history'
import { formatSize } from '@/utils/format'
import ResponseBody from './ResponseBody.vue'
import RequestDetail from './RequestDetail.vue'
import type { HistoryEntry, RequestConfig, ScriptTestResult } from '@/types'

const emit = defineEmits<{
  (e: 'save-to-collection'): void
}>()
const store = useRequestStore()
const responseStore = useResponseStore()
const historyStore = useHistoryStore()
const message = useMessage()

type Mode = 'response' | 'history'
const mode = ref<Mode>('response')
// When drilled into a single history entry's response (History mode only).
const viewingId = ref<number | null>(null)

const historyEntries = computed(() =>
  [...historyStore.entries].sort((a, b) => String(b.timestamp).localeCompare(String(a.timestamp)))
)
const historyCount = computed(() => historyStore.entries.length)
const viewing = computed(() => historyStore.entries.find((e) => e.id === viewingId.value) ?? null)

// The response shown in the body area: the live response (Response mode) or the
// selected history entry's response (History mode, when drilled in).
const displayResp = computed(() =>
  mode.value === 'response' ? responseStore.response : (viewing.value?.response ?? null)
)

// Default to the Response tab whenever a new response is shown.
const activeTab = ref('response')
watch(displayResp, (val) => {
  if (val) activeTab.value = 'response'
})

const displayTests = computed<ScriptTestResult[]>(() =>
  mode.value === 'response' ? (responseStore.testResults ?? []) : []
)

// Request context shown in the Request tab.
// Prefer the currently viewed history entry; otherwise fall back to the live editor state.
const displayRequest = computed<RequestConfig | null>(() => {
  // History mode → use drilled entry's resolved request
  if (viewing.value?.request) return viewing.value.request
  if (!displayResp.value) return null

  // Live response mode → show the ACTUALLY SENT request (variables already
  // resolved by the executor), not the raw builder config which still holds
  // {{var}} placeholders. Fall back to builder config only if no send happened.
  if (responseStore.sentRequest) return responseStore.sentRequest

  return {
    method: store.method,
    url: store.url,
    headers: store.headers,
    queryParams: store.queryParams,
    body: store.body,
    bodyType: store.bodyType,
    rawFormat: store.rawFormat,
    multipartFields: store.multipartFields,
    multipartFiles: store.multipartFiles,
    auth: store.auth,
  }
})

// The request's headers / query params are rendered inside RequestDetail.

const statusClass = computed(() => {
  const s = displayResp.value?.status
  if (!s) return ''
  if (s >= 200 && s < 300) return 'sc-2xx'
  if (s >= 400 && s < 500) return 'sc-4xx'
  if (s >= 500) return 'sc-5xx'
  return ''
})

function setMode(m: Mode) {
  mode.value = m
  if (m === 'response') viewingId.value = null
}
function openHistory(h: HistoryEntry) {
  if (h.response) viewingId.value = h.id
  else message.info('该记录没有响应数据（请求可能未成功）')
}
function backToList() {
  viewingId.value = null
}

function respStatusClass(s?: number): string {
  if (!s) return ''
  if (s >= 200 && s < 300) return 'h-2xx'
  if (s >= 400 && s < 500) return 'h-4xx'
  if (s >= 500) return 'h-5xx'
  return ''
}

function formatRel(ts: string | number): string {
  const tsNum = typeof ts === 'string' ? new Date(ts).getTime() : ts
  if (Number.isNaN(tsNum)) return ''
  const diff = Date.now() - tsNum
  const MIN = 60_000
  const HOUR = 3_600_000
  const DAY = 86_400_000
  if (diff < MIN) return 'just now'
  if (diff < HOUR) return `${Math.floor(diff / MIN)}m ago`
  if (diff < DAY) return `${Math.floor(diff / HOUR)}h ago`
  return new Date(tsNum).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function handleSave() {
  emit('save-to-collection')
}
</script>

<style scoped>
.response-panel {
  margin-top: 12px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xs);
  overflow: hidden;
  animation: fadeIn 0.2s var(--ease-out);
}

/* ---- Mode switch ---- */
.panel-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  background: var(--bg-subtle);
  border-bottom: 1px solid var(--border);
}
.mode-switch {
  display: inline-flex;
  gap: 2px;
  background: var(--bg-root);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 2px;
}
.mode-btn {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all var(--duration-fast) var(--ease-out);
}
.mode-btn:hover { color: var(--text); }
.mode-btn.active {
  background: var(--brand-bg);
  color: var(--brand);
}
.mode-badge {
  font-size: 10px;
  font-weight: 700;
  background: var(--brand);
  color: #fff;
  border-radius: 99px;
  padding: 0 6px;
  min-width: 16px;
  text-align: center;
  line-height: 16px;
}
.back-btn {
  margin-left: auto;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}
.back-btn:hover { color: var(--brand); border-color: var(--brand); }

/* ---- Empty / Loading ---- */
.panel-empty, .panel-loading {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 48px 20px; color: var(--text-muted); font-size: 13px;
}
.empty-illustration { font-size: 24px; opacity: 0.15; }

.loading-dot {
  width: 8px; height: 8px; background: var(--brand);
  border-radius: 50%; animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.85); }
}

/* ---- Error ---- */
.panel-error {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 16px 20px;
  background: var(--error-bg);
}
.error-icon {
  width: 20px; height: 20px; background: var(--error);
  color: #fff; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; flex-shrink: 0;
}
.error-title { font-size: 13px; font-weight: 600; color: var(--error); }
.error-body {
  font-size: 12px; color: var(--text-secondary);
  margin-top: 2px; white-space: pre-line;
}

/* ---- Status Bar ---- */
.status-bar {
  display: flex; align-items: center; gap: 16px;
  padding: 10px 16px;
  background: var(--bg-subtle);
  border-bottom: 1px solid var(--border);
}
.status-left { display: flex; align-items: center; gap: 8px; }
.status-code {
  padding: 2px 8px; border-radius: var(--radius-xs);
  font-size: 12px; font-weight: 700;
  font-family: var(--font-mono);
}
.sc-2xx { color: #059669; background: rgba(16,185,129,0.1); }
.sc-4xx { color: #d97706; background: rgba(245,158,11,0.1); }
.sc-5xx { color: #dc2626; background: rgba(239,68,68,0.1); }
.status-label { font-size: 12px; color: var(--text-secondary); font-weight: 500; }

.status-meta {
  display: flex; gap: 16px;
  font-size: 11px; color: var(--text-muted);
  font-family: var(--font-mono);
}

.status-actions { margin-left: auto; }
.action-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 20px;
  font-size: 11px; font-weight: 500; color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}
.action-chip:hover {
  background: var(--brand-bg);
  border-color: var(--brand);
  color: var(--brand);
}
.chip-icon { font-size: 13px; font-weight: 600; }

/* ---- Response Body ---- */
.response-tabs { padding: 0; }
.response-tabs :deep(.n-tabs-nav) { padding: 0 12px; }

/* ---- Tests ---- */
.test-list {
  max-height: 320px;
  overflow-y: auto;
}
.test-row {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 16px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}
.test-row:last-child { border-bottom: none; }
.test-icon {
  font-size: 13px; font-weight: 700; width: 18px; text-align: center;
}
.test-row.pass .test-icon { color: #10b981; }
.test-row.fail .test-icon { color: #ef4444; }
.test-row.pass { background: rgba(16, 185, 129, 0.04); }
.test-row.fail { background: rgba(239, 68, 68, 0.04); }
.test-name { flex: 1; font-weight: 500; }
.test-row.pass .test-name { color: #059669; }
.test-row.fail .test-name { color: #dc2626; }
.test-error {
  font-size: 11px; color: var(--text-muted);
  font-family: var(--font-mono);
  white-space: pre-line; max-width: 300px;
}

/* ---- Request (history) ---- */
.req-summary {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px;
  background: var(--bg-subtle);
  border-bottom: 1px solid var(--border);
}
.req-method {
  flex-shrink: 0;
  font-size: 10px; font-weight: 700; font-family: var(--font-mono);
  padding: 2px 6px; border-radius: 4px; letter-spacing: 0.3px;
  color: var(--text-secondary); background: var(--bg-subtle);
}
.req-method.pill-get { color: #34d399; background: rgba(52, 211, 153, 0.12); }
.req-method.pill-post { color: #60a5fa; background: rgba(96, 165, 250, 0.12); }
.req-method.pill-put { color: #fbbf24; background: rgba(251, 191, 36, 0.12); }
.req-method.pill-delete { color: #f87171; background: rgba(248, 113, 113, 0.12); }
.req-method.pill-patch { color: #c084fc; background: rgba(192, 132, 252, 0.12); }
.req-method.pill-head, .req-method.pill-options { color: #94a3b8; background: rgba(148, 163, 184, 0.12); }
.req-url {
  flex: 1; min-width: 0;
  font-size: 12px; font-family: var(--font-mono); color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* ---- History list ---- */
.history-list { max-height: 360px; overflow-y: auto; }
.history-loadmore { display: flex; justify-content: center; padding: 10px; }
.hist-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 16px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}
.hist-row:hover { background: var(--bg-hover); }
.h-method {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  font-family: var(--font-mono);
  padding: 2px 6px;
  border-radius: 4px;
  letter-spacing: 0.3px;
  color: var(--text-secondary);
  background: var(--bg-subtle);
}
.h-method.pill-get { color: #34d399; background: rgba(52, 211, 153, 0.12); }
.h-method.pill-post { color: #60a5fa; background: rgba(96, 165, 250, 0.12); }
.h-method.pill-put { color: #fbbf24; background: rgba(251, 191, 36, 0.12); }
.h-method.pill-delete { color: #f87171; background: rgba(248, 113, 113, 0.12); }
.h-method.pill-patch { color: #c084fc; background: rgba(192, 132, 252, 0.12); }
.h-method.pill-head, .h-method.pill-options { color: #94a3b8; background: rgba(148, 163, 184, 0.12); }

.h-url {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.h-status {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--text-muted);
}
.h-status.h-2xx { color: #34d399; }
.h-status.h-4xx { color: #fbbf24; }
.h-status.h-5xx { color: #f87171; }
.h-time {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--text-muted);
  min-width: 64px;
  text-align: right;
}
</style>
