<template>
  <div class="builder">
    <!-- URL Bar -->
    <div class="url-bar">
      <div class="url-row">
        <n-select :value="store.method" @update:value="store.method = $event"
          :options="methods" class="method-select"
          :style="{ '--method-color': methodColor }" />
        <n-input :value="store.url" @update:value="store.url = $event"
          @blur="onUrlBlur" @paste="onUrlPaste"
          placeholder="Enter URL, or paste a curl command (auto-converted)..."
          class="url-input"
          type="textarea" :autosize="{ minRows: 1, maxRows: 6 }"
          :input-props="{ autocomplete: 'off', autocorrect: 'off', spellcheck: false }"
        />
        <div class="url-actions">
          <!-- Timeout -->
          <n-popover trigger="click" placement="bottom-end" :width="240">
            <template #trigger>
              <n-button quaternary circle class="action-btn" title="Request timeout">
                <span class="action-icon">⏱</span>
              </n-button>
            </template>
              <div class="timeout-popover">
              <div class="popover-label">Request timeout (seconds)</div>
              <n-input-number v-model:value="timeoutValue" :min="0" :max="60"
                :show-button="false" size="small" placeholder="30" style="width: 100%" />
              <div class="popover-hint">0 = use default ({{ settings.defaultTimeout }}s)</div>
            </div>
          </n-popover>

          <!-- cURL preview -->
          <n-popover trigger="click" placement="bottom-end" :width="600">
            <template #trigger>
              <n-button quaternary circle class="action-btn" title="View as cURL">
                <span class="action-icon">&lt;/&gt;</span>
              </n-button>
            </template>
            <div class="curl-popover-body">
              <div class="curl-popover-head">
                <span class="curl-popover-title">cURL</span>
                <n-button size="tiny" type="primary" tertiary @click="handleCopyCurl">Copy</n-button>
              </div>
              <pre class="curl-preview">{{ curlPreview }}</pre>
            </div>
          </n-popover>

          <div class="action-divider"></div>

          <n-button tertiary @click="handleSaveToCollection" title="Save request to a collection" class="save-btn">
            Save
          </n-button>
          <n-button v-if="!responseStore.isLoading" type="primary" @click="handleSend" class="send-btn">Send</n-button>
          <n-button v-else type="error" @click="handleStop" class="send-btn">Stop</n-button>
        </div>
      </div>
      <div class="url-footer">
        <span class="proxy-tag"><span class="proxy-dot"></span>via proxy</span>
      </div>
    </div>

    <!-- Split: Request config (top) / Response (bottom), resizable -->
    <div class="split" ref="splitRef">
      <div class="pane-top" :style="{ flex: topFlexTop }">
        <div class="config-card">
      <n-tabs v-model:value="activeTab" type="bar" animated size="small" class="config-tabs">
        <n-tab-pane name="headers" :tab="headerTab">
          <KVTable :rows="store.headers" @update:rows="store.headers = $event"
            placeholder-key="Header Name" placeholder-value="Header Value" />
        </n-tab-pane>
        <n-tab-pane name="params" :tab="paramTab">
          <KVTable :rows="store.queryParams" @update:rows="store.queryParams = $event"
            placeholder-key="Param" placeholder-value="Value" />
        </n-tab-pane>
        <n-tab-pane name="body" tab="Body">
          <BodyEditor />
        </n-tab-pane>
        <n-tab-pane name="auth" tab="Auth">
          <AuthTab v-model="store.auth" />
        </n-tab-pane>
        <n-tab-pane name="prerequest" tab="Pre-req">
          <ScriptEditor
            v-model="store.preRequestScript"
            hint="Pre-request script — runs before the request is sent. Use pm.variables, pm.environment, pm.request."
            :snippets="preSnippets"
            placeholder="// Example: set a dynamic header&#10;pm.variables.set('timestamp', Date.now().toString());&#10;pm.environment.set('token', '{{token}}');"
          />
        </n-tab-pane>
        <n-tab-pane name="postresponse" tab="Tests">
          <ScriptEditor
            v-model="store.postResponseScript"
            hint="Post-response script — runs after the response is received. Use pm.test(), pm.response, pm.expect()."
            :snippets="postSnippets"
            placeholder="// Example: check status code&#10;pm.test('Status is 200', () => {&#10;  pm.expect(pm.response.status).toBe(200);&#10;});&#10;&#10;// Example: extract value&#10;pm.environment.set('userId', pm.response.json().id);"
          />
        </n-tab-pane>
      </n-tabs>
      </div>

      <div class="divider" @mousedown="onDragStart" title="Drag to resize">
        <span class="divider-grip"></span>
      </div>

      <div class="pane-bottom" :style="{ flex: topFlexBottom }">
        <ResponsePanel @save-to-collection="handleSaveToCollection" />
      </div>
    </div>
  </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { NSelect, NInput, NButton, NTabs, NTabPane, NPopover, NInputNumber, useMessage } from 'naive-ui'
import KVTable from '../components/common/KVTable.vue'
import BodyEditor from '../components/builder/BodyEditor.vue'
import AuthTab from '../components/builder/AuthTab.vue'
import ScriptEditor from '../components/builder/ScriptEditor.vue'
import ResponsePanel from '../components/response/ResponsePanel.vue'
import { useRequestStore } from '../stores/request'
import { useResponseStore } from '../stores/response'
import { useHistoryStore } from '../stores/history'
import { useEnvironmentStore } from '../stores/environment'
import { useProxyExecutor } from '../composables/useProxyExecutor'
import { useCurlParser } from '../composables/useCurlParser'
import { useWorkspace } from '../composables/useWorkspace'
import { useSettingsStore } from '../stores/settings'
import { HTTP_METHOD_OPTIONS } from '../utils/constants'
import { requestToCurl } from '../utils/exportImport'
import { copyToClipboard } from '../utils/format'
import type { RequestConfig } from '@/types'

const store = useRequestStore()
const responseStore = useResponseStore()
const historyStore = useHistoryStore()
const envStore = useEnvironmentStore()
const workspace = useWorkspace()
const settings = useSettingsStore()
const message = useMessage()
const { execute: proxyExecute, abort: proxyAbort } = useProxyExecutor(responseStore)
const { parse: parseCurl, error: parseError } = useCurlParser()

const methods = HTTP_METHOD_OPTIONS
const activeTab = ref('headers')

// ─── Vertical split: request (top) / response (bottom) ───
const splitRef = ref<HTMLElement | null>(null)
const SPLIT_KEY = 'builder-split-ratio'
const topPct = ref(Number(localStorage.getItem(SPLIT_KEY)) || 55)
const topFlexTop = computed(() => `${topPct.value} 1 0%`)
const topFlexBottom = computed(() => `${100 - topPct.value} 1 0%`)

let dragging = false
function onDragMove(e: MouseEvent) {
  if (!dragging || !splitRef.value) return
  const rect = splitRef.value.getBoundingClientRect()
  const pct = ((e.clientY - rect.top) / rect.height) * 100
  topPct.value = Math.min(80, Math.max(20, pct))
}
function onDragEnd() {
  if (!dragging) return
  dragging = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
  localStorage.setItem(SPLIT_KEY, String(Math.round(topPct.value)))
}
function onDragStart(e: MouseEvent) {
  dragging = true
  document.body.style.cursor = 'row-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd)
  e.preventDefault()
}

// ---- Method color ----
const METHOD_COLORS: Record<string, string> = {
  GET: 'var(--method-get)',
  POST: 'var(--method-post)',
  PUT: 'var(--method-put)',
  PATCH: 'var(--method-patch)',
  DELETE: 'var(--method-delete)',
  HEAD: 'var(--method-head)',
  OPTIONS: 'var(--method-head)',
}
const methodColor = computed(() => METHOD_COLORS[store.method] || 'var(--text)')

// ---- Tabs ----
function tabLabel(text: string) {
  return h('span', { class: 'tab-label' }, [text])
}
const headerTab = computed(() => tabLabel('Headers'))
const paramTab = computed(() => tabLabel('Params'))

// ---- Shared request config (used by Send + cURL preview) ----
const currentConfig = computed<RequestConfig>(() => ({
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
}))

const curlPreview = computed(() => requestToCurl(currentConfig.value))

const timeoutValue = computed({
  get: () => store.customTimeout || 0,
  set: (v: number | null) => { store.customTimeout = v ?? 0 },
})

// Effective timeout: per-request value if set (>0), otherwise the global default.
const effectiveTimeout = computed(() =>
  store.customTimeout > 0 ? store.customTimeout : settings.defaultTimeout,
)

// Curl detection — when the URL box holds a curl command
const isCurl = computed(() =>
  typeof store.url === 'string' && store.url.trim().toLowerCase().startsWith('curl')
)

async function convertCurl() {
  const text = store.url.trim()
  if (!text.toLowerCase().startsWith('curl')) return
  const result = await parseCurl(text)
  if (result) {
    store.setFromParsed(result)
    message.success('已转换为请求')
  } else {
    message.error(parseError.value || 'curl 解析失败')
  }
}

function onUrlBlur() {
  if (isCurl.value) convertCurl()
}

function onUrlPaste(e: ClipboardEvent) {
  // Read raw clipboard text directly to avoid v-model update timing issues
  // and single-line truncation of multi-line curl commands.
  const text = e.clipboardData?.getData('text')?.trim() ?? ''
  if (text.toLowerCase().startsWith('curl')) {
    store.url = text
    convertCurl()
  }
}

const preSnippets = [
  { label: 'Set timestamp', code: `pm.variables.set('timestamp', Date.now().toString());` },
  { label: 'Set random', code: `pm.variables.set('random', Math.random().toString(36).slice(2));` },
  { label: 'Get env var', code: `const token = pm.environment.get('token');` },
]

const postSnippets = [
  { label: 'Status 200', code: `pm.test('Status is 200', () => {\n  pm.expect(pm.response.status).toBe(200);\n});` },
  { label: 'JSON has key', code: `pm.test('Has user id', () => {\n  const data = pm.response.json();\n  pm.expect(data).toHaveProperty('id');\n});` },
  { label: 'Extract token', code: `const data = pm.response.json();\npm.environment.set('token', data.token);` },
]

async function handleSend() {
  const config = currentConfig.value
  const res = await proxyExecute(config, {
    preRequestScript: store.preRequestScript || undefined,
    postResponseScript: store.postResponseScript || undefined,
    envVariables: envStore.activeVariables,
    onEnvSet: (key: string, value: string) => {
      envStore.setVariableValue(key, value)
    },
    timeout: effectiveTimeout.value,
  })

  if (res) {
    // 保存实际发出的请求快照（变量已解析），供响应面板展示具体值
    responseStore.setSentRequest(res.request)
    if (res.response) {
      historyStore.addEntry({ request: res.request, response: res.response })
    } else {
      historyStore.addEntry({ request: res.request })
    }
  }
}

function handleStop() {
  proxyAbort()
}

async function handleSaveToCollection() {
  workspace.saveActiveRequest()
}

async function handleCopyCurl() {
  const ok = await copyToClipboard(curlPreview.value)
  if (ok) {
    message.success('cURL 已复制到剪贴板')
  } else {
    message.error('复制失败，请检查浏览器剪贴板权限')
  }
}
</script>

<style scoped>
.builder {
  padding: 16px 24px 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* ---- URL Bar ---- */
.url-row {
  display: flex;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: box-shadow var(--duration-fast) var(--ease-out);
}
.url-row:focus-within {
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.28), var(--shadow-md);
  border-color: transparent;
}

.method-select {
  width: 116px; flex-shrink: 0;
}
.method-select :deep(.n-base-selection) {
  border: none !important;
  border-right: 1px solid var(--border) !important;
  border-radius: 0 !important;
  background: transparent !important;
}
.method-select :deep(.n-base-selection-label),
.method-select :deep(.n-base-selection-input__content),
.method-select :deep(.n-base-selection-label__content) {
  font-family: var(--font-mono);
  font-size: 13px; font-weight: 600; letter-spacing: 0.3px;
  color: var(--method-color);
}

.url-input {
  flex: 1; min-width: 0;
}
.url-input :deep(.n-input__input-el) {
  font-family: var(--font-mono);
  font-size: 14px; padding: 0 14px;
}
.url-input :deep(.n-input__border) {
  border: none !important; border-radius: 0 !important;
}
.url-input :deep(.n-input__state-border) {
  border: none !important;
}

.url-actions {
  display: flex; align-items: center; gap: 4px;
  padding: 0 8px 0 4px; flex-shrink: 0;
}
.action-btn {
  color: var(--text-muted);
  transition: color var(--duration-fast) var(--ease-out);
}
.action-btn:hover { color: var(--text); }
.action-icon {
  font-size: 14px; line-height: 1;
  font-family: var(--font-mono);
  display: inline-flex; align-items: center;
}

.action-divider {
  width: 1px; height: 20px;
  background: var(--border);
  margin: 0 4px;
}

.save-btn { font-weight: 500; }
.send-btn {
  height: 34px; padding: 0 22px; font-weight: 600; font-size: 13px;
  border-radius: var(--radius-sm);
  background: var(--brand-grad) !important;
  border: none !important;
  color: #fff !important;
  box-shadow: var(--shadow-glow);
  transition: filter var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out);
}
.send-btn:hover { filter: brightness(1.1); transform: translateY(-1px); }
.send-btn:active { transform: translateY(0); }

.url-footer {
  margin-top: 6px; padding-left: 6px;
}
.proxy-tag {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 10px; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.6px;
  opacity: 0.5;
}
.proxy-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: var(--success);
}

/* ---- Tab labels (rendered via :tab VNode) ---- */
.tab-label { display: inline-flex; align-items: center; }

/* ---- Vertical split (request / response) ---- */
.split {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-top: 12px;
}
.pane-top,
.pane-bottom {
  min-height: 0;
  overflow: auto;
}
.pane-bottom {
  padding-bottom: 24px;
}
.divider {
  flex: 0 0 9px;
  height: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: row-resize;
  background: transparent;
}
.divider-grip {
  width: 42px;
  height: 3px;
  border-radius: 2px;
  background: var(--border);
  transition: background var(--duration-fast) var(--ease-out);
}
.divider:hover .divider-grip,
.divider:active .divider-grip {
  background: var(--brand);
}

/* ---- Config Card ---- */
.config-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xs);
  padding: 0 16px 8px;
}
.config-tabs :deep(.n-tabs-nav) {
  padding-top: 4px;
}
</style>

<style>
/* Popover content is teleported to the body element, so these must be non-scoped.
   Class names are kept specific to avoid collisions. */

.curl-popover-body {
  display: flex; flex-direction: column;
  gap: 10px;
}
.curl-popover-head {
  display: flex; align-items: center; justify-content: space-between;
}
.curl-popover-title {
  font-size: 11px; font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.8px;
}
.curl-preview {
  margin: 0;
  padding: 12px 14px;
  background: var(--code-bg);
  color: var(--code-text);
  border-left: 2px solid var(--brand);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 12px; line-height: 1.6;
  white-space: pre-wrap; word-break: break-all;
  max-height: 320px; overflow: auto;
}

.timeout-popover {
  display: flex; flex-direction: column; gap: 8px;
}
.timeout-popover .popover-label {
  font-size: 12px; font-weight: 600; color: var(--text);
}
.timeout-popover .popover-hint {
  font-size: 11px; color: var(--text-muted);
}
</style>
