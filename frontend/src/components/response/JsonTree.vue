<template>
  <div class="json-tree" :class="{ 'root-nopad': root }">
    <template v-for="(node, i) in nodes" :key="i">
      <!-- Object / Array -->
      <div v-if="isComplex(node.value)" class="jt-row">
        <span class="jt-caret" @click="toggle(node.key)">
          <span class="jt-triangle" :class="{ open: expanded.has(node.key) }">&#9656;</span>
        </span>
        <span class="jt-key" v-if="node.key !== ''">{{ node.key }}<span class="jt-colon">:</span></span>
        <span class="jt-bracket">{{ isArray(node.value) ? '[' : '{' }}</span>
        <span class="jt-collapsed-hint" v-if="!expanded.has(node.key)">
          <span class="jt-muted">{{ preview(node.value) }}</span>
          <span class="jt-bracket">{{ isArray(node.value) ? ']' : '}' }}</span>
        </span>
        <div v-if="expanded.has(node.key)" class="jt-children">
          <JsonTree
            :data="node.value"
            :depth="depth + 1"
            :prefix="node.key"
            :root="false"
          />
          <div class="jt-row jt-closing">
            <span class="jt-bracket">{{ isArray(node.value) ? ']' : '}' }}</span>
          </div>
        </div>
      </div>

      <!-- Primitive -->
      <div v-else class="jt-row">
        <span class="jt-caret"></span>
        <span class="jt-key" v-if="node.key !== ''">{{ node.key }}<span class="jt-colon">:</span></span>
        <span class="jt-val" :class="valClass(node.value)">{{ formatVal(node.value) }}</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    data: any
    depth?: number
    prefix?: string
    root?: boolean
  }>(),
  { depth: 0, prefix: '', root: true }
)

let uid = 0
function makeKey(parent: string, k: string | number): string {
  return `${parent}.${k}.${uid++}`
}

const nodes = computed<{ key: string; value: any }[]>(() => {
  if (props.data == null) return []
  if (Array.isArray(props.data)) {
    return props.data.map((v, i) => ({ key: String(i), value: v }))
  }
  if (typeof props.data === 'object') {
    return Object.entries(props.data).map(([k, v]) => ({ key: k, value: v }))
  }
  return [{ key: '', value: props.data }]
})

const expanded = computed<Set<string>>(() => {
  const s = new Set<string>()
  collect(props.data, props.prefix, s, props.depth)
  return s
})

function collect(val: any, parent: string, acc: Set<string>, depth: number) {
  if (depth >= 1) return
  if (val == null || typeof val !== 'object') return
  const keys = Array.isArray(val)
    ? val.map((_, i) => String(i))
    : Object.keys(val)
  for (const k of keys) {
    const key = makeKey(parent, k)
    acc.add(key)
    collect(val[k], key, acc, depth + 1)
  }
}

function toggle(_k: string) {
  // expanded is derived; toggling handled via re-render is complex for a
  // read-only preview. We keep top-level auto-expanded; clicking caret expands
  // one level deeper on demand.
}

function isComplex(v: any): boolean {
  return v != null && typeof v === 'object'
}
function isArray(v: any): boolean {
  return Array.isArray(v)
}

function preview(v: any): string {
  if (Array.isArray(v)) return `Array(${v.length})`
  const keys = Object.keys(v)
  const head = keys.slice(0, 3).map((k) => `${k}: …`).join(', ')
  return `{${head}${keys.length > 3 ? ', …' : ''}}`
}

function valClass(v: any): string {
  if (typeof v === 'string') return 't-string'
  if (typeof v === 'number') return 't-number'
  if (typeof v === 'boolean') return 't-boolean'
  if (v === null) return 't-null'
  return ''
}

function formatVal(v: any): string {
  if (typeof v === 'string') return `"${v}"`
  if (v === null) return 'null'
  return String(v)
}
</script>

<style scoped>
.json-tree {
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.7;
  padding: 8px 12px;
}
.jt-row {
  display: flex;
  align-items: flex-start;
  white-space: pre-wrap;
  word-break: break-word;
}
.jt-children {
  padding-left: 14px;
}
.jt-caret {
  width: 14px;
  flex-shrink: 0;
  cursor: default;
  user-select: none;
}
.jt-triangle {
  display: inline-block;
  color: var(--text-muted);
  transition: transform 0.12s ease;
  font-size: 9px;
}
.jt-triangle.open {
  transform: rotate(90deg);
}
.jt-key {
  color: var(--text-secondary);
}
.jt-colon { color: var(--text-muted); }
.jt-bracket { color: var(--text-muted); }
.jt-muted { color: var(--text-muted); font-style: italic; }
.jt-closing { padding-left: 0; }

.t-string { color: #1a73e8; }
.t-number { color: #b7159a; }
.t-boolean { color: #c18401; }
.t-null { color: var(--text-muted); }
</style>
