<template>
  <n-space vertical style="width: 100%">
    <n-select
      :value="modelValue.type"
      @update:value="updateType"
      :options="authTypes"
      style="width: 200px"
    />

    <template v-if="modelValue.type === 'basic'">
      <n-input v-model:value="local.username" placeholder="Username" @update:value="emitChange" />
      <n-input v-model:value="local.password" type="password" placeholder="Password" @update:value="emitChange" />
    </template>

    <template v-if="modelValue.type === 'bearer'">
      <n-input v-model:value="local.token" placeholder="Token" @update:value="emitChange" />
    </template>

    <template v-if="modelValue.type === 'api-key'">
      <n-input v-model:value="local.key" placeholder="Key" @update:value="emitChange" />
      <n-input v-model:value="local.value" placeholder="Value" @update:value="emitChange" />
      <n-select v-model:value="local.addTo" :options="[{ label: 'Header', value: 'header' }, { label: 'Query Param', value: 'query' }]" @update:value="emitChange" />
    </template>
  </n-space>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { NSelect, NInput, NSpace } from 'naive-ui'
import type { AuthConfig } from '@/types'

const props = defineProps<{ modelValue: AuthConfig }>()
const emit = defineEmits<{ 'update:modelValue': [AuthConfig] }>()

const local = reactive<AuthConfig>({ ...props.modelValue })

// Keep local in sync when the bound value changes externally
watch(() => props.modelValue, (v) => {
  Object.assign(local, v)
}, { deep: true })

function updateType(type: AuthConfig['type']) {
  local.type = type
  emitChange()
}

function emitChange() {
  emit('update:modelValue', { ...local })
}

const authTypes = [
  { label: 'No Auth', value: 'none' },
  { label: 'Basic Auth', value: 'basic' },
  { label: 'Bearer Token', value: 'bearer' },
  { label: 'API Key', value: 'api-key' },
]
</script>
