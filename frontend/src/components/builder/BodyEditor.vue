<template>
  <n-space vertical style="width: 100%">
    <div class="body-toolbar">
      <n-radio-group :value="store.bodyType" @update:value="store.setBodyType($event)" name="body-type" size="small">
        <n-space>
          <n-radio value="none">none</n-radio>
          <n-radio value="form">Form</n-radio>
          <n-radio value="multipart">Multipart</n-radio>
          <n-radio value="raw">Raw</n-radio>
          <n-radio value="binary">Binary</n-radio>
        </n-space>
      </n-radio-group>

      <n-select
        v-if="store.bodyType === 'raw'"
        :value="store.rawFormat"
        @update:value="store.setRawFormat($event)"
        :options="rawFormatOptions"
        size="tiny"
        style="width: 120px"
      />

      <n-button
        v-if="store.bodyType === 'raw' && store.rawFormat === 'json'"
        size="tiny"
        secondary
        :disabled="!store.body.trim()"
        @click="formatBody"
        class="format-btn"
      >
      格式化
</n-button>
    </div>

    <template v-if="store.bodyType === 'multipart'">
      <div class="mp-block">
        <div class="mp-head">
          <span class="mp-title">Files</span>
          <n-button size="small" @click="pickFile">+ Add File</n-button>
          <input ref="fileInput" type="file" multiple hidden @change="onFileChange" />
        </div>
        <div v-for="f in store.multipartFiles" :key="f.id" class="mp-file">
          <n-input v-model:value="f.field" placeholder="field name" class="mp-field" />
          <span class="mp-meta">{{ f.name }} <small>({{ formatSize(f.size) }})</small></span>
          <n-button quaternary circle size="tiny" type="error" @click="removeFile(f.id)">
            <template #icon><span>&times;</span></template>
          </n-button>
        </div>
        <div v-if="!store.multipartFiles.length" class="mp-empty">No files added</div>
      </div>
      <KVTable
        :rows="store.multipartFields"
        @update:rows="store.multipartFields = $event"
        placeholder-key="Field"
        placeholder-value="Value"
      />
    </template>

    <n-input
      v-else-if="store.bodyType === 'raw' || store.bodyType === 'form'"
      :value="store.body"
      @update:value="store.body = $event"
      type="textarea"
      :rows="8"
      :placeholder="bodyPlaceholder"
      :input-props="{ spellcheck: false }"
      class="body-textarea"
      style="font-family: monospace; font-size: 13px"
    />

    <div v-else-if="store.bodyType === 'binary'" class="binary-placeholder">
      Binary body is not supported in this build.
    </div>
  </n-space>
</template>

<script setup lang="ts">
import { uuid, formatSize  } from '@/utils/format'
import { computed, ref } from 'vue'
import { NSpace, NRadioGroup, NRadio, NInput, NButton, NSelect, useMessage } from 'naive-ui'
import { useRequestStore } from '../../stores/request'
import type { RawFormat } from '../../types'
import KVTable from '../common/KVTable.vue'

const store = useRequestStore()
const fileInput = ref<HTMLInputElement | null>(null)
const message = useMessage()

const rawFormatOptions = [
  { label: 'JSON', value: 'json' },
  { label: 'Text', value: 'text' },
  { label: 'XML', value: 'xml' },
  { label: 'HTML', value: 'html' },
  { label: 'JavaScript', value: 'javascript' },
]

const bodyPlaceholder = computed(() => {
  switch (store.bodyType) {
    case 'form': return 'key1=value1&key2=value2'
    case 'raw':
      return store.rawFormat === 'json'
        ? '{ "key": "value" }'
        : `Raw ${store.rawFormat} body content...`
    default: return ''
  }
})

function pickFile() {
  fileInput.value?.click()
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files
  if (!files) return
  for (const file of Array.from(files)) {
    const reader = new FileReader()
    reader.onload = () => {
      store.multipartFiles.push({
        id: uuid(),
        field: file.name,
        name: file.name,
        type: file.type || 'application/octet-stream',
        size: file.size,
        dataUrl: reader.result as string,
      })
    }
    reader.readAsDataURL(file)
  }
  input.value = ''
}

function removeFile(id: string) {
  store.multipartFiles = store.multipartFiles.filter((f) => f.id !== id)
}

// Pretty-print the body as JSON (json/raw types). Shows an error if it's not valid JSON.
// Uses the de-facto industry layout: 2-space indent, expanded arrays, trailing newline
// (matches Prettier / VS Code "Format Document" / Postman beautify).
function formatBody() {
  if (!store.body.trim()) return
  try {
    const parsed = JSON.parse(store.body)
    store.body = `${JSON.stringify(parsed, null, 2)}\n`
    message.success('已格式化')
  } catch {
    message.error('JSON 格式有误，无法格式化')
  }
}
</script>

<style scoped>
.body-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.format-btn {
  font-size: 12px;
  font-weight: 500;
}

/* Keep JSON on its own logical lines (no soft-wrap) so the 2-space
   indentation stays visually aligned, like an editor / Postman. */
.body-textarea :deep(textarea) {
  white-space: pre;
  overflow: auto;
  word-break: normal;
  overflow-wrap: normal;
}

.mp-block {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 12px;
}
.mp-head {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 8px;
}
.mp-title {
  font-size: 12px; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.5px;
}
.mp-file {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 6px;
}
.mp-field { width: 160px; flex-shrink: 0; }
.mp-meta {
  flex: 1; min-width: 0;
  font-size: 12px; color: var(--text-muted);
  font-family: var(--font-mono);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.mp-empty {
  font-size: 12px; color: var(--text-muted);
  padding: 4px 0;
}
</style>
