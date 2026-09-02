<template>
  <div class="sb-req" :class="{ 'is-active': isActive }">
    <!-- Request row -->
    <div class="req-row" @click="openReq">
      <span class="cell-name">
        <n-ellipsis :tooltip="true" style="max-width: 100%;">{{ req.name }}</n-ellipsis>
      </span>
      <span class="cell-actions" @click.stop>
        <n-dropdown trigger="click" :options="moveOptions" @select="(fid) => onMove(fid)">
          <n-button quaternary circle size="tiny" title="Move">
            <template #icon><span>&#8596;</span></template>
          </n-button>
        </n-dropdown>
        <n-button quaternary circle size="tiny" title="Rename" @click.stop="startRename">
          <template #icon><span>&#9998;</span></template>
        </n-button>
        <n-button quaternary circle size="tiny" title="Duplicate" @click.stop="onDuplicate">
          <template #icon><span>&#10697;</span></template>
        </n-button>
        <n-popconfirm :show-icon="false" positive-text="Delete" negative-text="Cancel" @positive-click="onDelete">
          <template #trigger>
            <n-button class="row-del-btn" quaternary circle size="tiny" type="error" title="Delete">
              <template #icon><span class="del-icon">&times;</span></template>
            </n-button>
          </template>
          Delete this request?
        </n-popconfirm>
        <input v-if="renaming" v-model="nameDraft" class="inline-rename" @keyup.enter="commitRename"
          @blur="commitRename" @click.stop />
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { NButton, NEllipsis, NPopconfirm, NDropdown, useMessage } from 'naive-ui'
import { useCollectionsStore } from '@/stores/collections'
import { useTabsStore } from '@/stores/tabs'
import { useWorkspace } from '@/composables/useWorkspace'
import type { Collection, SavedRequest, Folder } from '@/types'

const props = defineProps<{
  req: SavedRequest
  col: Collection
  folderId: string | null
}>()

const collectionsStore = useCollectionsStore()
const tabsStore = useTabsStore()
const workspace = useWorkspace()
const message = useMessage()

const renaming = ref(false)
const nameDraft = ref('')

const isActive = computed(() => tabsStore.activeTab?.savedRequestId === props.req.id)

const ROOT = '__root__'
const moveOptions = computed(() => {
  const flat: { label: string; value: string | null }[] = [{ label: 'Root', value: null }]
  const walk = (folders: Folder[], prefix = '') => {
    for (const f of folders) {
      const label = prefix ? `${prefix} / ${f.name}` : f.name
      flat.push({ label, value: f.id })
      walk(f.folders, label)
    }
  }
  walk(props.col.folders)
  return flat.map((o) => ({ label: o.label, key: o.value ?? ROOT }))
})

function openReq() {
  workspace.openRequestInTab(props.req, props.col, props.folderId)
}

function startRename() {
  nameDraft.value = props.req.name
  renaming.value = true
}
function commitRename() {
  if (renaming.value && nameDraft.value.trim() && props.col.dbId) {
    collectionsStore.renameRequest(props.col.dbId, props.req.id, nameDraft.value.trim())
  }
  renaming.value = false
}
function onDuplicate() {
  if (props.col.dbId) {
    collectionsStore.duplicateRequest(props.col.dbId, props.req.id)
    message.success('Request duplicated')
  }
}
function onDelete() {
  if (props.col.dbId) {
    collectionsStore.removeRequest(props.col.dbId, props.req.id, props.folderId)
    message.success('Request deleted')
  }
}
function onMove(folderId: string) {
  if (props.col.dbId) {
    collectionsStore.moveRequest(props.col.dbId, props.req.id, props.folderId, folderId === ROOT ? null : folderId)
    message.success('Request moved')
  }
}
</script>

<style scoped>
.sb-req { position: relative; }
.req-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  user-select: none;
  -webkit-user-select: none;
  transition: background var(--duration-fast) var(--ease-out);
}
.req-row:hover { background: var(--bg-hover); }
.sb-req.is-active > .req-row {
  background: var(--brand-bg);
  box-shadow: inset 2px 0 0 var(--brand);
}

.cell-name {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
}

.cell-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-out);
}
.req-row:hover .cell-actions { opacity: 1; }

.inline-rename {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 500;
  padding: 2px 8px;
  border: 1.5px solid var(--brand);
  border-radius: 5px;
  outline: none;
  background: var(--bg-card);
  color: var(--text);
}
.row-del-btn:hover { color: #fff; background: #f87171; }
.del-icon { font-size: 18px; }
</style>
