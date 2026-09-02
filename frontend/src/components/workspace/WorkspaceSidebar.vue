<template>
  <aside class="sidebar">
    <div class="sidebar-head">
      <span class="sidebar-title">COLLECTIONS</span>
      <div class="head-actions">
        <n-button size="tiny" tertiary @click="openImport">
          <template #icon><span class="btn-import">&#x2193;</span></template>
          Import
        </n-button>
        <n-button size="tiny" tertiary type="primary" @click="showCreate = true">
          <template #icon><span class="btn-plus">+</span></template>
          New
        </n-button>
      </div>
    </div>

    <div class="sidebar-body">
      <div v-if="collectionsStore.collections.length === 0" class="sidebar-empty">
        No collections yet.
        <br />Create one to start saving requests.
      </div>

      <div v-for="col in collectionsStore.collections" :key="col.id" class="col-block">
        <!-- Collection header -->
        <div class="col-row" @click="workspace.toggle(col.id)">
          <button class="col-caret" @click.stop="workspace.toggle(col.id)">{{ workspace.collapsed[col.id] ? '▸' : '▾' }}</button>
          <span class="col-icon">&#x1F4C2;</span>
          <span class="col-name" :title="col.name">{{ col.name }}</span>
          <span class="col-actions" @click.stop>
            <n-dropdown trigger="click" :options="getAddOptions(col, null)" title="Add Request or Folder">
              <n-button quaternary circle size="tiny">
                <template #icon><span class="btn-plus">+</span></template>
              </n-button>
            </n-dropdown>
            <n-dropdown trigger="click" :options="getExportOptions(col)" title="Export">
              <n-button quaternary circle size="tiny">
                <template #icon><span class="btn-export">&#x2193;</span></template>
              </n-button>
            </n-dropdown>
            <n-popconfirm
              positive-text="Delete"
              negative-text="Cancel"
              @positive-click="removeCollection(col)"
            >
              <template #trigger>
                <n-button quaternary circle size="tiny" title="Delete Collection">
                  <template #icon><span class="btn-del">&#x1F5D1;</span></template>
                </n-button>
              </template>
              Delete collection “{{ col.name }}”? This cannot be undone.
            </n-popconfirm>
          </span>
        </div>

        <!-- Contents -->
        <div v-show="!workspace.collapsed[col.id]">
          <div v-if="col.requests.length === 0 && col.folders.length === 0" class="col-empty">
            Empty — add a request or folder
          </div>
          <SidebarRequestRow
            v-for="req in col.requests"
            :key="req.id"
            :req="req"
            :col="col"
            :folder-id="null"
          />
          <SidebarFolder
            v-for="folder in col.folders"
            :key="folder.id"
            :folder="folder"
            :col="col"
            @add-request="(fid: string) => addRequest(col, fid)"
            @add-folder="(fid: string) => addFolder(col, fid)"
          />
        </div>
      </div>
    </div>

    <!-- New Collection modal -->
    <n-modal
      v-model:show="showCreate"
      preset="card"
      title="New Collection"
      :bordered="false"
      style="width: 420px"
      :mask-closable="false"
    >
      <n-space vertical size="medium">
        <n-input v-model:value="newName" placeholder="Collection name" size="large"
          :input-props="{ autofocus: true }" @keyup.enter="createCollection" />
        <div class="modal-footer">
          <n-button @click="showCreate = false">Cancel</n-button>
          <n-button type="primary" :disabled="!newName.trim()" @click="createCollection">Create</n-button>
        </div>
      </n-space>
    </n-modal>

    <!-- Import Collection modal -->
    <n-modal
      v-model:show="showImport"
      preset="card"
      title="Import Collection"
      :bordered="false"
      style="width: 520px"
      :mask-closable="false"
    >
      <n-space vertical size="medium">
        <p class="modal-hint">Import a Postman Collection v2.1 or a native collection export.</p>

        <!-- Dropzone -->
        <input ref="fileInput" type="file" accept=".json,application/json" class="file-input"
          @change="handleImportFile" />
        <div
          class="dropzone"
          :class="{ 'is-dragover': dragover, 'has-file': !!importFileName }"
          @click="triggerFile"
          @dragover.prevent="dragover = true"
          @dragleave.prevent="dragover = false"
          @drop.prevent="onDrop"
        >
          <template v-if="!importFileName">
            <div class="dz-icon">&#x2193;</div>
            <div class="dz-title">Drop a <b>.json</b> file here</div>
            <div class="dz-sub">or click to browse — Postman v2.1 or native format</div>
          </template>
          <div v-else class="dz-file">
            <span class="dz-file-icon">&#x1F4C4;</span>
            <span class="dz-file-name">{{ importFileName }}</span>
            <n-button size="tiny" tertiary @click.stop="clearFile">Clear</n-button>
          </div>
        </div>

        <div class="dz-divider"><span>or paste JSON</span></div>

        <n-input v-model:value="importText" type="textarea" :rows="8"
          placeholder="Paste a Postman Collection v2.1 or native collection JSON…"
          :input-props="{ autofocus: true }" />

        <!-- Format detection -->
        <div v-if="detectedFormat" class="fmt-badge" :class="detectedFormat">
          <span class="fmt-dot" />
          {{ detectedFormat === 'postman' ? 'Detected: Postman Collection v2.1' : 'Detected: Native JSON' }}
        </div>
        <div v-else-if="importText.trim()" class="fmt-badge invalid">
          <span class="fmt-dot" />
          Unrecognized format — please check the file
        </div>

        <div v-if="importError" class="import-error">{{ importError }}</div>

        <div class="modal-footer">
          <n-button @click="closeImport">Cancel</n-button>
          <n-button type="primary" :loading="importing" :disabled="!canImport" @click="runImportFromState">
            Import
          </n-button>
        </div>
      </n-space>
    </n-modal>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { NButton, NModal, NSpace, NInput, NDropdown, NPopconfirm, useMessage } from 'naive-ui'
import { useCollectionsStore } from '@/stores/collections'
import { useWorkspace } from '@/composables/useWorkspace'
import SidebarRequestRow from './SidebarRequestRow.vue'
import SidebarFolder from './SidebarFolder.vue'
import { downloadFile, detectCollectionFormat } from '@/utils/exportImport'
import { uuid } from '@/utils/format'
import type { Collection, SavedRequest } from '@/types'

const collectionsStore = useCollectionsStore()
const workspace = useWorkspace()
const message = useMessage()

const showCreate = ref(false)
const newName = ref('')

// ─── Import ───────────────────────────────────────────────────────
const showImport = ref(false)
const importText = ref('')
const importFileName = ref('')
const importing = ref(false)
const dragover = ref(false)
const importError = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

const detectedFormat = computed(() =>
  importText.value.trim() ? detectCollectionFormat(importText.value) : null,
)
const canImport = computed(() => detectedFormat.value !== null)

function openImport() {
  resetImport()
  showImport.value = true
}
function closeImport() {
  showImport.value = false
  resetImport()
}
function resetImport() {
  importText.value = ''
  importFileName.value = ''
  importing.value = false
  dragover.value = false
  importError.value = ''
}

function triggerFile() {
  fileInput.value?.click()
}

async function readFile(file: File) {
  try {
    importText.value = await file.text()
    importFileName.value = file.name
    importError.value = ''
  } catch {
    importError.value = 'Failed to read file'
  }
}

async function handleImportFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) await readFile(file)
  input.value = ''
}

async function onDrop(e: DragEvent) {
  dragover.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) await readFile(file)
}

function clearFile() {
  importText.value = ''
  importFileName.value = ''
  importError.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

async function runImportFromState() {
  if (!canImport.value) return
  importing.value = true
  importError.value = ''
  try {
    const ok = await collectionsStore.importCollectionRaw(importText.value)
    if (ok) {
      const newest = collectionsStore.collections[0]
      if (newest?.dbId) workspace.expandCollection(newest.dbId)
      message.success('Collection imported')
      closeImport()
    } else {
      importError.value = 'Unrecognized file format. Please provide a Postman Collection v2.1 or native collection export.'
    }
  } catch (e) {
    // Network / API / auth errors surface here (importCollectionRaw only
    // returns false for a bad format — anything else throws). Show the real
    // cause instead of silently resetting the modal.
    const msg = e instanceof Error && e.message ? e.message : String(e)
    importError.value = `Import failed: ${msg}`
    console.error('[import] failed:', e)
  } finally {
    importing.value = false
  }
}

// ─── Export ───────────────────────────────────────────────────────
function getExportOptions(col: Collection) {
  return [
    {
      label: 'Export (Native JSON)',
      key: `native-${col.id}`,
      props: {
        onClick: () => {
          const data = collectionsStore.exportCollectionNative(col)
          downloadFile(data, `${col.name}.json`)
        },
      },
    },
    {
      label: 'Export (Postman v2.1)',
      key: `postman-${col.id}`,
      props: {
        onClick: () => {
          const data = collectionsStore.exportCollectionPostman(col)
          downloadFile(data, `${col.name}-postman.json`)
        },
      },
    },
  ]
}

function blankConfig(): SavedRequest['request'] {
  return {
    method: 'GET',
    url: '',
    headers: [{ id: uuid(), key: 'Content-Type', value: 'application/json', desc: '', enabled: true }],
    queryParams: [],
    body: '',
    bodyType: 'raw',
    rawFormat: 'json',
    multipartFields: [],
    multipartFiles: [],
    auth: { type: 'none' },
  }
}

// ── Add (one "+" per level: collection root + each folder) ──
function getAddOptions(col: Collection, parentId: string | null) {
  return [
    {
      label: 'New Request',
      key: `req-${col.id}-${parentId ?? 'root'}`,
      props: { onClick: () => addRequest(col, parentId) },
    },
    {
      label: 'New Folder',
      key: `folder-${col.id}-${parentId ?? 'root'}`,
      props: { onClick: () => addFolder(col, parentId) },
    },
  ]
}

async function addRequest(col: Collection, parentId: string | null) {
  if (!col.dbId) return
  const id = uuid()
  const req: SavedRequest = { id, name: 'New Request', request: blankConfig() }
  await collectionsStore.addRequest(col.dbId, parentId, req)
  if (parentId && col.dbId) workspace.expandCollection(col.dbId)
  workspace.openRequestInTab(req, col, parentId)
}

function addFolder(col: Collection, parentId: string | null) {
  if (!col.dbId) return
  collectionsStore.createFolder(col.dbId, parentId, 'New Folder').then(() => {
    if (col.dbId) workspace.expandCollection(col.dbId)
  })
}

async function removeCollection(col: Collection) {
  if (!col.dbId) return
  await collectionsStore.deleteCollection(col.dbId)
  message.success('Collection deleted')
}

async function createCollection() {
  if (!newName.value.trim()) return
  await collectionsStore.createCollection(newName.value.trim())
  newName.value = ''
  showCreate.value = false
}
</script>

<style scoped>
.sidebar {
  width: 280px;
  flex-shrink: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border-right: 1px solid var(--border);
}
.sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 12px 10px;
  border-bottom: 1px solid var(--border);
}
.sidebar-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.6px;
  color: var(--text-muted);
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}
.btn-import { font-size: 14px; font-weight: 700; line-height: 1; transform: rotate(180deg); display: inline-block; }
.btn-export { font-size: 14px; font-weight: 700; line-height: 1; }

/* ── Import dropzone ── */
.dropzone {
  border: 1.5px dashed var(--border);
  border-radius: var(--radius-md);
  padding: 22px 16px;
  text-align: center;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  background: var(--bg-subtle);
}
.dropzone:hover { border-color: var(--brand); background: var(--brand-bg); }
.dropzone.is-dragover {
  border-color: var(--brand);
  background: var(--brand-bg);
  box-shadow: inset 0 0 0 1px var(--brand);
}
.dropzone.has-file { cursor: default; }
.dropzone .file-input { display: none; }
.dz-icon { font-size: 26px; opacity: 0.7; }
.dz-title { font-size: 13px; font-weight: 600; margin-top: 6px; color: var(--text); }
.dz-sub { font-size: 11px; color: var(--text-muted); margin-top: 3px; }
.dz-file {
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.dz-file-icon { font-size: 16px; }
.dz-file-name {
  font-size: 12px; font-weight: 600; color: var(--text);
  max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.dz-divider {
  text-align: center; font-size: 11px; color: var(--text-muted);
  position: relative;
}
.dz-divider::before {
  content: ''; position: absolute; left: 0; right: 0; top: 50%;
  height: 1px; background: var(--border);
}
.dz-divider span { position: relative; background: var(--bg-card); padding: 0 10px; }

/* ── Format detection badge ── */
.fmt-badge {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; font-weight: 600;
  padding: 8px 12px; border-radius: var(--radius-sm);
}
.fmt-badge .fmt-dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
}
.fmt-badge.postman, .fmt-badge.native {
  color: #34d399; background: rgba(52, 211, 153, 0.1);
  border: 1px solid rgba(52, 211, 153, 0.3);
}
.fmt-badge.postman .fmt-dot, .fmt-badge.native .fmt-dot { background: #34d399; }
.fmt-badge.invalid {
  color: #f87171; background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.3);
}
.fmt-badge.invalid .fmt-dot { background: #f87171; }
.import-error {
  font-size: 12px; color: #f87171;
  padding: 8px 12px; border-radius: var(--radius-sm);
  background: rgba(248, 113, 113, 0.1); border: 1px solid rgba(248, 113, 113, 0.3);
}
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; }
.modal-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-muted);
}
.sidebar-body {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 24px;
}
.sidebar-empty {
  padding: 24px 16px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-muted);
  text-align: center;
}

.col-block { border-bottom: 1px solid var(--border); }
.col-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 10px;
  background: var(--bg-subtle);
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  transition: background var(--duration-fast) var(--ease-out);
}
.col-row:hover { background: var(--bg-hover); }
.col-caret {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 10px;
  color: var(--text-muted);
  width: 14px;
  padding: 0;
  line-height: 1;
}
.col-icon { font-size: 14px; }
.col-name {
  font-size: 13px;
  font-weight: 700;
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.col-actions {
  display: flex;
  align-items: center;
  gap: 1px;
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-out);
}
.col-row:hover .col-actions { opacity: 1; }
.col-empty {
  padding: 10px 16px 10px 32px;
  font-size: 11px;
  color: var(--text-muted);
  font-style: italic;
}
.btn-plus { font-size: 15px; font-weight: 600; line-height: 1; }
.req-plus { font-size: 14px; font-weight: 700; line-height: 1; }
.btn-del { font-size: 13px; line-height: 1; }
.col-actions .btn-del:hover { filter: brightness(0.8); }
</style>
