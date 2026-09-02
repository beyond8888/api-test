<template>
  <div class="mock-page">
    <!-- Top bar -->
    <div class="page-top">
      <div class="page-title-wrap">
        <h2 class="page-title">Mock</h2>
        <input
          v-model="searchInput"
          class="mock-search"
          type="text"
          placeholder="搜索名称或路径"
          @input="onSearchInput"
        />
      </div>
      <div class="top-actions">
        <button class="form-btn form-btn-primary" @click="openCreate">
          <span class="btn-plus">+</span> 新建 Mock
        </button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="endpoints.length === 0 && !loading" class="empty-page">
      <div class="empty-graphic">
        <div class="empty-icon-circle">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
      </div>
      <template v-if="searchQuery">
        <div class="empty-text">未找到匹配的 Mock</div>
        <div class="empty-sub">没有与「{{ searchQuery }}」匹配的名称或路径</div>
      </template>
      <template v-else>
        <div class="empty-text">还没有 Mock 端点</div>
        <div class="empty-sub">创建自定义 Mock 接口，用 Python 脚本灵活构造响应数据</div>
      </template>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="empty-page">
      <p style="color: var(--text-muted);">加载中...</p>
    </div>

    <!-- Endpoint list -->
    <div v-if="endpoints.length > 0" class="list-container">
      <div class="list-header">
        <span style="width: 80px;">方法</span>
        <span style="flex: 1;">路径</span>
        <span style="width: 180px;">名称</span>
        <span style="width: 80px; text-align: center;">状态</span>
        <span style="width: 180px;">更新时间</span>
        <span style="width: 100px; text-align: right;"></span>
      </div>
      <div
        v-for="ep in endpoints"
        :key="ep.id"
        class="list-row"
        style="padding: 0 16px 0 20px;"
      >
        <!-- Method -->
        <span style="width: 80px;">
          <span :class="['method-tag', methodClass(ep.method)]">{{ ep.method }}</span>
        </span>

        <!-- Path -->
        <span style="flex: 1; min-width: 0; display: flex; align-items: center; gap: 8px;">
          <code style="font-family: var(--font-mono); font-size: 12.5px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            /mock/{{ ep.path }}
          </code>
          <button
            class="copy-btn"
            title="复制 Mock URL"
            @click="copyMockUrl(ep)"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
              <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
            </svg>
          </button>
        </span>

        <!-- Name -->
        <span style="width: 180px; font-size: 13px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
          {{ ep.name }}
        </span>

        <!-- Toggle -->
        <span style="width: 80px; text-align: center;">
          <n-switch
            :value="ep.enabled"
            size="small"
            @update:value="(val: boolean) => toggleEnabled(ep, val)"
          />
        </span>

        <!-- Updated -->
        <span class="row-date" style="width: 180px;">
          {{ formatDateTime(ep.updated_at) }}
        </span>

        <!-- Actions -->
        <span class="row-actions" style="width: 100px;">
          <button class="act-btn" title="测试" @click="openTest(ep)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </button>
          <button class="act-btn edit-btn" title="编辑" @click="openEdit(ep)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button class="act-btn del-btn" title="删除" @click="confirmDelete(ep)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
          </button>
        </span>
      </div>

      <!-- Load more -->
      <div v-if="nextUrl" class="list-more">
        <button class="form-btn" :disabled="loadingMore" @click="loadMore">
          {{ loadingMore ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </div>

    <!-- ========== Create / Edit Modal ========== -->
    <n-modal
      v-model:show="showModal"
      :mask-closable="false"
      preset="card"
      style="max-width: 800px; width: 92%;"
      :title="editingId ? '编辑 Mock 端点' : '新建 Mock 端点'"
    >
      <div class="form-section">
        <div class="form-label">名称 <span class="form-label-hint">（管理用，不对外暴露）</span></div>
        <input
          v-model="form.name"
          class="form-input"
          placeholder="例如: 用户信息 Mock"
        />
      </div>

      <div class="form-section">
        <div class="form-label">HTTP 方法</div>
        <n-radio-group v-model:value="form.method" name="method">
          <n-radio-button
            v-for="m in METHODS"
            :key="m"
            :value="m"
            :style="methodTagStyle(m, form.method)"
          >
            {{ m }}
          </n-radio-button>
        </n-radio-group>
      </div>

      <div class="form-section">
        <div class="form-label">路径 <span class="form-label-hint">（支持 &lt;param&gt; 占位符）</span></div>
        <input
          v-model="form.path"
          class="form-input"
          style="font-family: var(--font-mono);"
          placeholder="例如: api/users/&lt;user_id&gt;"
        />
        <div v-if="form.path" style="margin-top: 6px; font-size: 11px; color: var(--text-muted);">
          实际访问: <code style="color: var(--brand);">/mock/{{ form.path }}</code>
        </div>
      </div>

      <div class="form-section">
        <div class="form-label">描述 <span class="form-label-hint">（可选）</span></div>
        <input
          v-model="form.description"
          class="form-input"
          placeholder="简要说明这个 Mock 的作用"
        />
      </div>

      <div class="form-section">
        <div class="form-label">模拟延时 <span class="form-label-hint">（毫秒，0 表示无延时）</span></div>
        <input
          v-model.number="form.delay_ms"
          type="number"
          class="form-input"
          style="width: 140px;"
          min="0"
          max="30000"
          placeholder="0"
        />
      </div>

      <div class="form-section">
        <div class="form-label">
          Python 脚本
          <span class="form-label-hint">（定义 <code>handle(request)</code> 函数）</span>
        </div>
        <CodeEditor v-model="form.python_script" language="python" :min-height="'300px'" />
      </div>

      <div class="form-section" v-if="editingId">
        <div class="form-label">启用状态</div>
        <n-switch v-model:value="form.enabled" />
      </div>

      <div class="form-footer">
        <button class="form-btn form-btn-primary" @click="handleSave" :disabled="saving">
          {{ saving ? '保存中...' : (editingId ? '保存修改' : '创建') }}
        </button>
        <button class="form-btn" @click="showModal = false">取消</button>
        <button
          v-if="editingId"
          class="form-btn-danger"
          @click="confirmDeleteFromModal"
        >删除此端点</button>
      </div>

      <div v-if="error" style="margin-top: 12px; color: var(--error); font-size: 12px;">
        {{ error }}
      </div>
    </n-modal>

    <!-- ========== Test Modal ========== -->
    <n-modal
      v-model:show="showTestModal"
      preset="card"
      style="max-width: 700px; width: 92%;"
      :title="`测试: ${testingEp?.name || ''}`"
    >
      <div class="form-section">
        <div class="form-label">模拟 Query 参数 (JSON)</div>
        <textarea
          v-model="testQueryParams"
          class="form-textarea"
          style="font-family: var(--font-mono); min-height: 60px;"
          placeholder='{"key": "value"}'
        ></textarea>
      </div>
      <div class="form-section">
        <div class="form-label">模拟 Headers (JSON)</div>
        <textarea
          v-model="testHeaders"
          class="form-textarea"
          style="font-family: var(--font-mono); min-height: 60px;"
          placeholder='{"Content-Type": "application/json"}'
        ></textarea>
      </div>
      <div class="form-section">
        <div class="form-label">模拟 Path 参数 (JSON)</div>
        <textarea
          v-model="testPathParams"
          class="form-textarea"
          style="font-family: var(--font-mono); min-height: 60px;"
          placeholder='{"user_id": "123"}'
        ></textarea>
      </div>
      <div class="form-section">
        <div class="form-label">模拟 Request Body</div>
        <textarea
          v-model="testBody"
          class="form-textarea"
          style="font-family: var(--font-mono); min-height: 80px;"
          placeholder='{"name": "test"}'
        ></textarea>
      </div>
      <div class="form-footer">
        <button class="form-btn form-btn-primary" @click="runTest" :disabled="testing">
          {{ testing ? '执行中...' : '▶ 运行测试' }}
        </button>
        <button class="form-btn" @click="showTestModal = false">关闭</button>
      </div>

      <div v-if="testResult" style="margin-top: 16px;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
          <span :class="['method-tag', methodClass(testingEp?.method || 'GET')]">
            {{ testingEp?.method }}
          </span>
          <span style="font-size: 14px; color: var(--text);">
            {{ testResult.status_code }}
          </span>
          <span style="font-size: 11px; color: var(--text-muted);">
            {{ testResult.timing_ms }}ms
          </span>
        </div>
        <div class="test-response-body" v-if="testResult.body">
          <pre class="test-pre">{{ formatBody(testResult.body) }}</pre>
        </div>
        <div v-if="testResult.error" style="margin-top: 8px;">
          <div style="font-size: 11px; font-weight: 600; color: var(--error); margin-bottom: 4px;">
            Script Error:
          </div>
          <pre class="test-pre" style="color: var(--error);">{{ testResult.error }}</pre>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { NModal, NSwitch, NRadioGroup, NRadioButton, useMessage } from 'naive-ui'
import { useApiClient } from '@/composables/useApiClient'
import { copyToClipboard, formatDateTime } from '@/utils/format'
import CodeEditor from '@/components/common/CodeEditor.vue'

const { client: api } = useApiClient()
const message = useMessage()

const METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']

// 新建时预填的示例脚本（明文展示，用户按需修改返回/条件即可）
const SCRIPT_TEMPLATE = `def handle(request):
    # request.method / request.path / request.query_params
    # request.headers / request.body / request.path_params
    # request.json()
    #
    # 两种写法都可以，status_code / headers 平台会自动补全(默认200 + JSON):
    #   1) 直接返回 body:
    #      return {'message': 'hello'}
    #   2) 需要自定义时返回 dict:
    #      if request.query_params.get('aaBB') == 'abc':
    #          return {'status_code': 201, 'body': '{"ok": true}'}
    #      return '{"message": "hello"}'

    return {'message': 'hello'}`

// ---------- State ----------
const endpoints = ref<any[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const searchInput = ref('')
const searchQuery = ref('')
const nextUrl = ref<string | null>(null)
const totalCount = ref(0)
const showModal = ref(false)
const showTestModal = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const testing = ref(false)
const error = ref('')
const testResult = ref<any>(null)
const testingEp = ref<any>(null)
const testQueryParams = ref('{}')
const testHeaders = ref('{}')
const testPathParams = ref('{}')
const testBody = ref('')

// Form
const form = reactive({
  name: '',
  path: '',
  method: 'GET',
  python_script: '',
  description: '',
  delay_ms: 0,
  enabled: true,
})

// ---------- Load (paginated + search) ----------
async function loadEndpoints(reset = true) {
  if (reset) {
    loading.value = true
    endpoints.value = []
    nextUrl.value = null
  } else {
    if (!nextUrl.value || loadingMore.value) return
    loadingMore.value = true
  }
  try {
    const params: Record<string, any> = { page_size: 20 }
    if (searchQuery.value) params.search = searchQuery.value
    const url = reset
      ? `/mock/endpoints/`
      : `/${nextUrl.value!.split('/api/v1/')[1]}`
    const res: any = await api.get(url, { params: reset ? params : undefined })
    const data = res?.data
    const results = data?.results || (Array.isArray(data) ? data : [])
    totalCount.value = data?.count ?? results.length
    nextUrl.value = data?.next || null
    if (reset) {
      endpoints.value = results
    } else {
      endpoints.value = [...endpoints.value, ...results]
    }
  } catch {
    message.error('加载 Mock 端点失败')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

// Debounced search
let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    searchQuery.value = searchInput.value.trim()
    loadEndpoints(true)
  }, 300)
}

function loadMore() {
  loadEndpoints(false)
}

onMounted(() => loadEndpoints(true))

// ---------- Helpers ----------
function methodClass(m: string) {
  return `m-${m.toLowerCase()}`
}

function formatBody(body: any) {
  if (typeof body === 'string') {
    try {
      return JSON.stringify(JSON.parse(body), null, 2)
    } catch {
      return body
    }
  }
  return JSON.stringify(body, null, 2)
}

function methodTagStyle(m: string, selected: string) {
  const colors: Record<string, string> = {
    GET: '#60a5fa', POST: '#34d399', PUT: '#fbbf24',
    DELETE: '#f87171', PATCH: '#fbbf24', HEAD: '#9ca3af', OPTIONS: '#9ca3af',
  }
  if (m === selected) {
    return {
      color: '#fff',
      background: colors[m] || '#6366f1',
      borderColor: colors[m] || '#6366f1',
    }
  }
  return {}
}

function resetForm() {
  form.name = ''
  form.path = ''
  form.method = 'GET'
  form.python_script = SCRIPT_TEMPLATE
  form.description = ''
  form.delay_ms = 0
  form.enabled = true
  editingId.value = null
  error.value = ''
}

function fillForm(ep: any) {
  form.name = ep.name
  form.path = ep.path
  form.method = ep.method
  form.python_script = ep.python_script || ''
  form.description = ep.description || ''
  form.delay_ms = ep.delay_ms || 0
  form.enabled = ep.enabled
  editingId.value = ep.id
  error.value = ''
}

// ---------- CRUD Actions ----------
function openCreate() {
  resetForm()
  showModal.value = true
}

function openEdit(ep: any) {
  fillForm(ep)
  showModal.value = true
}

async function handleSave() {
  if (!form.name.trim() || !form.path.trim()) {
    error.value = '名称和路径不能为空'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const payload = {
      name: form.name.trim(),
      path: form.path.trim().replace(/^\/+|\/+$/g, ''),
      method: form.method,
      python_script: form.python_script,
      description: form.description,
      delay_ms: form.delay_ms,
      enabled: form.enabled,
    }
    if (editingId.value) {
      await api.patch(`/mock/endpoints/${editingId.value}/`, payload)
      message.success('更新成功')
    } else {
      await api.post('/mock/endpoints/', payload)
      message.success('创建成功')
    }
    showModal.value = false
    await loadEndpoints()
  } catch (e: any) {
    const msg = e?.response?.data?.message || e?.response?.data?.detail || e?.message || '保存失败'
    error.value = typeof msg === 'string' ? msg : JSON.stringify(msg)
  } finally {
    saving.value = false
  }
}

async function toggleEnabled(ep: any, val: boolean) {
  try {
    await api.patch(`/mock/endpoints/${ep.id}/`, { enabled: val })
    ep.enabled = val
    message.success(val ? '已启用' : '已停用')
  } catch {
    message.error('操作失败')
  }
}

function confirmDelete(ep: any) {
  fillForm(ep)
  confirmDeleteFromModal()
}

async function confirmDeleteFromModal() {
  if (!editingId.value) return
  try {
    await api.delete(`/mock/endpoints/${editingId.value}/`)
    message.success('已删除')
    showModal.value = false
    await loadEndpoints()
  } catch {
    message.error('删除失败')
  }
}

function copyMockUrl(ep: any) {
  const url = ep.mock_url || `${window.location.origin}/mock/${ep.path}`
  copyToClipboard(url).then((ok) => {
    if (ok) {
      message.success('Mock URL 已复制')
    } else {
      message.warning('复制失败，请手动复制')
    }
  })
}

// ---------- Test ----------
function openTest(ep: any) {
  testingEp.value = ep
  testQueryParams.value = '{}'
  testHeaders.value = '{}'
  testPathParams.value = '{}'
  testBody.value = ''
  testResult.value = null
  showTestModal.value = true
}

async function runTest() {
  if (!testingEp.value) return
  testing.value = true
  testResult.value = null
  try {
    const parse = (raw: string) => {
      try { return JSON.parse(raw) } catch { return {} }
    }
    const res: any = await api.post(`/mock/endpoints/${testingEp.value.id}/test/`, {
      query_params: parse(testQueryParams.value),
      headers: parse(testHeaders.value),
      path_params: parse(testPathParams.value),
      body: testBody.value,
    })
    const resultData = res?.data || res
    testResult.value = {
      ...resultData.response,
      timing_ms: resultData.timing_ms,
    }
  } catch (e: any) {
    const data = e?.response?.data
    testResult.value = {
      status_code: 500,
      body: JSON.stringify(data || { error: e.message }, null, 2),
      timing_ms: 0,
    }
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.mock-page {
  max-width: var(--page-max);
  margin: 0 auto;
  padding: 28px 25px 50px;
}

.copy-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: 1px solid var(--border);
  border-radius: 5px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--duration-fast);
  flex-shrink: 0;
  opacity: 0;
}
.list-row:hover .copy-btn { opacity: 1; }
.copy-btn:hover { color: var(--brand); border-color: var(--brand); background: var(--brand-bg); }

.test-response-body {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  max-height: 400px;
  overflow: auto;
}
.test-pre {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--code-text);
  white-space: pre-wrap;
  word-break: break-all;
}

/* Fix Naive UI radio button for dark theme */
:deep(.n-radio-group .n-radio-button) {
  font-size: 12px;
  font-weight: 600;
  font-family: var(--font-mono);
}
</style>
