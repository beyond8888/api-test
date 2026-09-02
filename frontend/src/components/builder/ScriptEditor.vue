<template>
  <div class="script-editor">
    <div class="script-hint">
      <span class="hint-dot" :class="{ active: hasScript }"></span>
      {{ hint }}
    </div>
    <n-input
      :value="modelValue"
      @update:value="$emit('update:modelValue', $event)"
      type="textarea"
      :placeholder="placeholder"
      :rows="14"
      :input-props="{ autocorrect: 'off', spellcheck: false }"
      class="script-input"
    />
    <div class="script-snippets">
      <span class="snippet-label">Quick snippets:</span>
      <n-button
        v-for="s in snippets"
        :key="s.label"
        size="tiny"
        quaternary
        @click="insertSnippet(s.code)"
      >
{{ s.label }}
</n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NInput, NButton } from 'naive-ui'

const props = defineProps<{
  modelValue: string
  hint: string
  snippets: Array<{ label: string; code: string }>
  placeholder: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const hasScript = computed(() => props.modelValue.trim().length > 0)

function insertSnippet(code: string) {
  const newVal = props.modelValue ? `${props.modelValue}\n${code}` : code
  emit('update:modelValue', newVal)
}
</script>

<style scoped>
.script-editor {
  padding: 8px 0;
}

.script-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.hint-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--border);
  transition: background var(--duration-fast) var(--ease-out);
}
.hint-dot.active {
  background: var(--brand-color, #6366f1);
  box-shadow: 0 0 6px rgba(99, 102, 241, 0.4);
}

.script-input :deep(textarea) {
  font-family: var(--font-mono) !important;
  font-size: 13px !important;
  line-height: 1.55 !important;
  tab-size: 2;
}

.script-snippets {
  display: flex; align-items: center; gap: 6px;
  margin-top: 8px; flex-wrap: wrap;
}
.snippet-label {
  font-size: 11px; color: var(--text-muted);
  margin-right: 4px;
}
</style>
