<script setup lang="ts">
import { ref, shallowRef, watch } from 'vue'
import { EditorView, lineNumbers, highlightActiveLine, highlightActiveLineGutter, keymap } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands'
import { python } from '@codemirror/lang-python'
import { syntaxHighlighting, defaultHighlightStyle, bracketMatching, indentOnInput } from '@codemirror/language'
import { oneDark } from '@codemirror/theme-one-dark'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    language?: 'python' | 'json'
    readOnly?: boolean
    minHeight?: string
  }>(),
  { modelValue: '', language: 'python', readOnly: false, minHeight: '300px' },
)

const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const editor = ref<HTMLElement | null>(null)
const view = shallowRef<EditorView | null>(null)

const langExt = () => (props.language === 'python' ? python() : [])

const baseTheme = EditorView.theme({
  '&': { fontSize: '13px', height: '100%' },
  '.cm-scroller': { fontFamily: "var(--font-mono, 'SF Mono', Menlo, Consolas, monospace)", lineHeight: '1.6' },
  '.cm-gutters': { border: 'none', background: 'transparent' },
  '.cm-content': { padding: '12px 0' },
})

function buildState(doc: string) {
  return EditorState.create({
    doc,
    extensions: [
      lineNumbers(),
      highlightActiveLineGutter(),
      highlightActiveLine(),
      history(),
      indentOnInput(),
      bracketMatching(),
      syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
      oneDark,
      baseTheme,
      langExt(),
      keymap.of([...defaultKeymap, ...historyKeymap, indentWithTab]),
      EditorState.readOnly.of(props.readOnly),
      EditorView.editable.of(!props.readOnly),
      EditorView.updateListener.of((u) => {
        if (u.docChanged) emit('update:modelValue', u.state.doc.toString())
      }),
    ],
  })
}

watch(
  () => props.modelValue,
  (val) => {
    const v = view.value
    if (v && val !== v.state.doc.toString()) {
      v.dispatch({ changes: { from: 0, to: v.state.doc.length, insert: val ?? '' } })
    }
  },
)

watch(
  () => props.language,
  () => {
    if (view.value) view.value.dispatch({ effects: [] })
  },
)

import { onMounted } from 'vue'
onMounted(() => {
  if (!editor.value) return
  view.value = new EditorView({ state: buildState(props.modelValue), parent: editor.value })
})

import { onBeforeUnmount } from 'vue'
onBeforeUnmount(() => view.value?.destroy())
</script>

<template>
  <div class="code-editor" :style="{ minHeight }">
    <div ref="editor" class="code-editor-inner" :class="{ readonly: readOnly }"></div>
  </div>
</template>

<style scoped>
.code-editor {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: #282c34;
}
.code-editor-inner {
  height: 100%;
}
.code-editor-inner :deep(.cm-editor) {
  height: 100%;
}
.code-editor-inner.readonly :deep(.cm-editor) {
  background: #1e2227;
}
</style>
