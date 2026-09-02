<template>
  <n-card size="small" style="margin-top: 8px" :title="resolvedTitle">
    <template #header-extra>
      <div class="rb-toolbar">
        <n-button size="tiny" quaternary @click="copyBody">
          <template #icon><span>&#10697;</span></template>
          Copy
        </n-button>
        <n-button size="tiny" quaternary @click="downloadBody">
          <template #icon><span>&#8595;</span></template>
          Download
        </n-button>
        <n-radio-group
          v-if="bodyType === 'json'"
          :value="viewMode"
          @update:value="viewMode = $event"
          size="small"
        >
          <n-radio-button value="pretty">Pretty</n-radio-button>
          <n-radio-button value="raw">Raw</n-radio-button>
        </n-radio-group>
      </div>
    </template>

    <div v-if="bodyType === 'json' && viewMode === 'pretty' && parsed !== null">
      <JsonTree :data="parsed" :depth="0" />
    </div>
    <pre v-else-if="bodyType === 'json'" class="code-block" v-html="highlightedRaw" />
    <pre v-else class="code-block">{{ rawDisplay }}</pre>
  </n-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NCard, NButton, NRadioGroup, NRadioButton, useMessage } from 'naive-ui'
import JsonTree from './JsonTree.vue'
import { highlightJson } from '@/utils/highlightJson'

const props = defineProps<{
  body: string
  bodyType: 'json' | 'html' | 'xml' | 'text'
  title?: string
}>()

const resolvedTitle = computed(() => props.title ?? 'Response Body')

const message = useMessage()
const viewMode = ref<'pretty' | 'raw'>('raw')

const parsed = computed(() => {
  if (props.bodyType !== 'json') return null
  try {
    return JSON.parse(props.body)
  } catch {
    return null
  }
})

const highlightedBody = computed(() => highlightJson(display.value))
// Raw mode: show the server response verbatim (no re-formatting).
const rawDisplay = computed(() => props.body)
const highlightedRaw = computed(() => highlightJson(props.body))

const display = computed(() => {
  if (props.bodyType === 'json') {
    try {
      return JSON.stringify(JSON.parse(props.body), null, 2)
    } catch {
      return props.body
    }
  }
  return props.body
})

function copyBody() {
  const text = viewMode.value === 'raw' || props.bodyType !== 'json'
    ? props.body
    : display.value
  navigator.clipboard
    .writeText(text)
    .then(() => message.success('Copied to clipboard'))
    .catch(() => message.error('Copy failed'))
}

function downloadBody() {
  const mime
    = props.bodyType === 'json' ? 'application/json' : 'text/plain'
  const blob = new Blob([props.body], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `response.${props.bodyType === 'json' ? 'json' : 'txt'}`
  a.click()
  URL.revokeObjectURL(url)
  message.success('Download started')
}
</script>

<style scoped>
.rb-toolbar { display: flex; align-items: center; gap: 6px; }
</style>
