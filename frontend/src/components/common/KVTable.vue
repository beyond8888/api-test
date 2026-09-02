<template>
  <div class="kv-editor">
    <!-- Bulk Edit Toggle -->
    <div class="kv-toolbar">
      <n-space align="center">
        <n-button text size="tiny" @click="addRow">
          <template #icon>+</template>
        </n-button>
        <n-text depth="3" style="font-size: 12px">{{ rows.length }} rows</n-text>
      </n-space>
      <n-button text size="tiny" @click="bulkMode = !bulkMode">
        {{ bulkMode ? 'Key-Value Edit' : 'Bulk Edit' }}
      </n-button>
    </div>

    <!-- Bulk Edit Mode -->
    <div v-if="bulkMode">
      <n-input
        v-model:value="bulkText"
        type="textarea"
        :rows="Math.max(6, rows.length + 2)"
        placeholder="key: value (one per line)"
        class="bulk-textarea"
        :input-props="{ spellcheck: false }"
        @update:value="onBulkChange"
      />
    </div>

    <!-- Key-Value Table Mode -->
    <div v-else class="kv-rows">
      <div class="kv-header-row">
        <div class="kv-col-check"></div>
        <div class="kv-col-key">Key</div>
        <div class="kv-col-value">Value</div>
        <div class="kv-col-desc">Description</div>
        <div class="kv-col-action"></div>
      </div>

      <div
        v-for="(row, idx) in rows"
        :key="row.id"
        class="kv-row"
        :class="{ 'kv-row-disabled': !row.enabled }"
      >
        <div class="kv-col-check">
          <n-checkbox v-model:checked="row.enabled" size="small" />
        </div>
        <div class="kv-col-key">
          <n-auto-complete
            v-model:value="row.key"
            :options="headerSuggestions"
            :get-show="() => true"
            placeholder="Header name"
            size="small"
            :input-props="{ style: 'font-family: monospace; font-size: 12px', spellcheck: false }"
          />
        </div>
        <div class="kv-col-value">
          <n-input
            v-model:value="row.value"
            placeholder="Header value"
            size="small"
            :input-props="{ style: 'font-family: monospace; font-size: 12px', spellcheck: false }"
          />
        </div>
        <div class="kv-col-desc">
          <n-input
            v-model:value="row.desc"
            placeholder="Description"
            size="small"
            :input-props="{ spellcheck: false }"
          />
        </div>
        <div class="kv-col-action">
          <n-button text size="tiny" type="error" @click="removeRow(idx)" class="kv-remove-btn">&times;</n-button>
        </div>
      </div>

      <div v-if="rows.length === 0" class="kv-empty">
        This request has no {{ placeholderKey.toLowerCase() }}s.
        <br />
        <n-button text size="tiny" type="primary" @click="addRow">Add one</n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { NCheckbox, NInput, NButton, NText, NSpace, NAutoComplete } from 'naive-ui'
import type { KV } from '../../types'

const props = withDefaults(defineProps<{
  rows: KV[]
  placeholderKey?: string
  placeholderValue?: string
}>(), {
  placeholderKey: 'Key',
  placeholderValue: 'Value',
})

const emit = defineEmits<{
  'update:rows': [value: KV[]]
}>()

let idCounter = Date.now()

const bulkMode = ref(false)
const bulkText = ref('')

// Common HTTP headers for autocomplete
const headerSuggestions = ref([
  'Accept', 'Accept-Charset', 'Accept-Encoding', 'Accept-Language',
  'Authorization', 'Cache-Control', 'Connection', 'Content-Length',
  'Content-Type', 'Cookie', 'Host', 'Origin', 'Referer',
  'User-Agent', 'X-Requested-With', 'X-CSRF-Token',
  'X-API-Key', 'X-Auth-Token', 'If-Match', 'If-None-Match',
  'Access-Control-Allow-Origin', 'API-Key',
].map(v => ({ label: v, value: v })))

// Build bulk text from current rows
watch(() => props.rows, (newRows) => {
  if (!bulkMode.value) {
    bulkText.value = newRows
      .map(r => `${r.key}: ${r.value}`)
      .join('\n')
  }
}, { deep: true, immediate: true })

function addRow() {
  const newRows = [...props.rows, {
    id: String(++idCounter),
    key: '',
    value: '',
    desc: '',
    enabled: true,
  }]
  emit('update:rows', newRows)
}

function removeRow(idx: number) {
  const newRows = props.rows.filter((_, i) => i !== idx)
  emit('update:rows', newRows)
}

function onBulkChange(value: string) {
  if (!bulkMode.value) return
  const lines = value.split('\n').filter(l => l.trim())
  const newRows: KV[] = lines.map(line => {
    const colonIdx = line.indexOf(':')
    if (colonIdx >= 0) {
      return {
        id: String(++idCounter),
        key: line.substring(0, colonIdx).trim(),
        value: line.substring(colonIdx + 1).trim(),
        desc: '',
        enabled: true,
      }
    }
    return {
      id: String(++idCounter),
      key: line.trim(),
      value: '',
      desc: '',
      enabled: true,
    }
  })
  emit('update:rows', newRows)
}
</script>

<style scoped>
.kv-editor { background: transparent; }

.kv-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 0 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 4px;
}

.kv-header-row {
  display: flex; align-items: center; padding: 5px 0;
  font-size: 10px; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.6px;
  font-weight: 500;
}

.kv-row {
  display: flex; align-items: center; padding: 3px 0;
  border-radius: var(--radius-xs);
  transition: background var(--duration-fast) var(--ease-out);
}
.kv-row:hover { background: var(--bg-hover); }

.kv-row-disabled { opacity: 0.3; }

.kv-col-check  { width: 28px; display: flex; justify-content: center; flex-shrink: 0; }
.kv-col-key    { flex: 1; min-width: 120px; padding: 0 4px; }
.kv-col-value  { flex: 2; min-width: 160px; padding: 0 4px; }
.kv-col-desc   { flex: 1; min-width: 80px; padding: 0 4px; }
.kv-col-action { width: 28px; display: flex; justify-content: center; flex-shrink: 0; }

.kv-remove-btn {
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-out);
}
.kv-row:hover .kv-remove-btn { opacity: 1; }

.kv-empty {
  padding: 28px; text-align: center;
  color: var(--text-muted); font-size: 13px; line-height: 1.7;
}

.bulk-textarea {
  font-family: var(--font-mono);
  font-size: 12px;
}
.bulk-textarea :deep(textarea) {
  background: var(--bg-subtle) !important;
  border-radius: var(--radius-sm);
}
</style>
