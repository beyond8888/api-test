<template>
  <div class="settings-page">
    <!-- Environments -->
    <section class="settings-section">
      <div class="section-top">
        <n-button size="small" @click="showEnvCreate = true"><template #icon><span class="btn-plus">+</span></template>New</n-button>
      </div>
      <div class="env-list" v-if="envStore.environments.length">
        <div v-for="env in envStore.environments" :key="env.id" class="env-card">
          <div class="env-header">
            <div class="env-title">
              <span class="env-name">{{ env.name }}</span>
              <span v-if="envStore.activeId === env.id" class="env-badge">active</span>
            </div>
            <div class="env-actions">
              <n-button v-if="envStore.activeId !== env.id" size="tiny" quaternary @click="envStore.setActive(env.id)">Activate</n-button>
              <n-button size="tiny" quaternary type="error" @click="envStore.deleteEnv(env.id)">Delete</n-button>
            </div>
          </div>
          <div class="env-vars"><KVTable :rows="envToKV(env)" @update:rows="rows => updateVars(env.id, rows)" /></div>
        </div>
      </div>
      <n-modal v-model:show="showEnvCreate" style="width:400px" :mask-closable="false">
        <div class="modal-form">
          <div class="form-header">
            <span class="form-header-title">New Environment</span>
          </div>
          <n-space vertical>
            <n-input v-model:value="newEnvName" placeholder="e.g. Development, Staging" @keyup.enter="createEnv" />
            <div style="display:flex;justify-content:flex-end;gap:8px">
              <n-button size="small" @click="showEnvCreate = false">Cancel</n-button>
              <n-button size="small" type="primary" @click="createEnv" :disabled="!newEnvName.trim()">Create</n-button>
            </div>
          </n-space>
        </div>
      </n-modal>
    </section>

    <!-- Request Defaults -->
    <section class="settings-section">
      <h3>Request Defaults</h3>
      <div class="setting-row">
        <div class="setting-meta">
          <div class="setting-label">Default request timeout (seconds)</div>
          <div class="setting-desc">Applied to new requests when the per-request timeout field is left at 0.</div>
        </div>
        <n-input-number
          v-model:value="settings.defaultTimeout"
          :min="settings.MIN_TIMEOUT"
          :max="settings.MAX_TIMEOUT"
          :show-button="false"
          size="small"
          style="width: 120px"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NModal, NSpace, NInput, NInputNumber } from 'naive-ui'
import KVTable from '../components/common/KVTable.vue'
import { useEnvironmentStore } from '../stores/environment'
import { useSettingsStore } from '../stores/settings'
import type { Environment, KV } from '../types'

const envStore = useEnvironmentStore()
const settings = useSettingsStore()
const showEnvCreate = ref(false)
const newEnvName = ref('')

function envToKV(env: Environment): KV[] {
  return env.variables
}
function updateVars(envId: number, rows: KV[]) {
  envStore.updateVariables(envId, rows)
}
function createEnv() {
  if (!newEnvName.value.trim()) return
  envStore.createEnv(newEnvName.value.trim())
  newEnvName.value = ''
  showEnvCreate.value = false
}
</script>

<style scoped>
.settings-page { max-width: 800px; margin: 0 auto; padding: 20px 0 40px; }
.settings-section { margin-bottom: 32px; }
.section-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.section-top h3 { font-size: 15px; font-weight: 600; }
.btn-plus { font-size: 15px; font-weight: 600; line-height: 1; }

/* Request Defaults */
.settings-section h3 { font-size: 15px; font-weight: 600; margin-bottom: 14px; }
.setting-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 14px 16px; background: var(--bg-card); border-radius: var(--radius-md); box-shadow: var(--shadow-xs); }
.setting-meta { display: flex; flex-direction: column; gap: 4px; }
.setting-label { font-size: 13px; font-weight: 600; }
.setting-desc { font-size: 12px; color: var(--text-muted); }

/* Environments */
.env-list { display: flex; flex-direction: column; gap: 12px; }
.env-card { background: var(--bg-card); border-radius: var(--radius-md); box-shadow: var(--shadow-xs); overflow: hidden; }
.env-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; background: var(--bg-subtle); border-bottom: 1px solid var(--border); }
.env-title { display: flex; align-items: center; gap: 8px; }
.env-name { font-size: 13px; font-weight: 600; }
.env-badge { font-size: 10px; color: var(--success); background: var(--success-bg); padding: 1px 8px; border-radius: 10px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
.env-actions { display: flex; gap: 4px; }
.env-vars { padding: 0 16px 8px; }
</style>
