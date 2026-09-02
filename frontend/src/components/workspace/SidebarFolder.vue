<template>
  <div class="sb-folder">
    <!-- Folder header -->
    <div class="folder-row">
      <button class="folder-caret" @click="toggleExpanded">{{ expanded ? '▾' : '▸' }}</button>
      <span class="folder-icon">&#x1F4C1;</span>
      <input v-if="editing" v-model="nameDraft" class="folder-rename-input"
        @keyup.enter="commitRename" @blur="commitRename" @click.stop />
      <span v-else class="folder-name" @click="toggleExpanded">{{ folder.name }}</span>
      <span class="folder-actions">
        <n-dropdown trigger="click" :options="addOptions" title="Add Request or Folder">
          <n-button quaternary circle size="tiny">
            <template #icon><span class="btn-plus">+</span></template>
          </n-button>
        </n-dropdown>
        <n-button quaternary circle size="tiny" title="Rename" @click.stop="startRename">
          <template #icon><span>&#9998;</span></template>
        </n-button>
        <n-popconfirm :show-icon="false" positive-text="Delete" negative-text="Cancel"
          @positive-click="onDeleteFolder">
          <template #trigger>
            <n-button class="folder-del-btn" quaternary circle size="tiny" type="error" title="Delete folder">
              <template #icon><span class="del-icon">&times;</span></template>
            </n-button>
          </template>
          Delete folder "{{ folder.name }}" and all its contents?
        </n-popconfirm>
      </span>
    </div>

    <!-- Children (indented with a tree guide line per level) -->
    <div v-show="expanded" class="folder-children">
      <SidebarRequestRow
        v-for="req in folder.requests"
        :key="req.id"
        :req="req"
        :col="col"
        :folder-id="folder.id"
      />
      <SidebarFolder
        v-for="sub in folder.folders"
        :key="sub.id"
        :folder="sub"
        :col="col"
        :collapse-signal="childCollapseSignal"
        @add-request="emit('add-request', $event)"
        @add-folder="emit('add-folder', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { NButton, NPopconfirm, NDropdown, useMessage } from 'naive-ui'
import { useCollectionsStore } from '@/stores/collections'
import SidebarRequestRow from './SidebarRequestRow.vue'
import type { Collection, Folder } from '@/types'

const props = defineProps<{
  folder: Folder
  col: Collection
  /**
   * Bumped by an ancestor when it collapses — watching this lets every
   *  descendant collapse itself, so re-expanding the parent shows a clean tree.
   */
  collapseSignal?: number
}>()

const emit = defineEmits<{
  (e: 'add-request', folderId: string): void
  (e: 'add-folder', folderId: string): void
}>()

const collectionsStore = useCollectionsStore()
const message = useMessage()
const expanded = ref(true)
const editing = ref(false)
const nameDraft = ref('')

// Recursive collapse: when an ancestor collapses it bumps `collapseSignal`;
// each descendant watches it and collapses itself, and forwards the bumped
// signal to its own children via `childCollapseSignal`.
const localCollapseTick = ref(0)
const childCollapseSignal = computed(() => (props.collapseSignal ?? 0) + localCollapseTick.value)

watch(() => props.collapseSignal, () => {
  expanded.value = false
})

function toggleExpanded() {
  if (expanded.value) {
    // collapsing — bump the tick so descendants collapse too
    localCollapseTick.value++
  }
  expanded.value = !expanded.value
}

const addOptions = [
  { label: 'New Request', key: 'req', props: { onClick: () => emit('add-request', props.folder.id) } },
  { label: 'New Folder', key: 'folder', props: { onClick: () => emit('add-folder', props.folder.id) } },
]

function startRename() {
  nameDraft.value = props.folder.name
  editing.value = true
}
function commitRename() {
  if (editing.value && nameDraft.value.trim() && props.col.dbId) {
    collectionsStore.renameFolder(props.col.dbId, props.folder.id, nameDraft.value.trim())
  }
  editing.value = false
}
function onDeleteFolder() {
  if (props.col.dbId) {
    collectionsStore.deleteFolder(props.col.dbId, props.folder.id)
    message.success('Folder deleted')
  }
}
</script>

<style scoped>
.folder-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  cursor: default;
  border-bottom: 1px solid var(--border);
  background: var(--bg-subtle);
  user-select: none;
  -webkit-user-select: none;
  transition: background var(--duration-fast) var(--ease-out);
}
.folder-row:hover { background: var(--bg-hover); }

/* Nested children: deeper indent + strong 3px guide line + progressive
   background tint so each level reads as its own clearly-separated layer. */
.folder-children {
  margin-left: 22px;
  padding-left: 16px;
  border-left: 3px solid rgba(255, 255, 255, 0.22);
  background: var(--nest-1);
}
.folder-children .folder-children { background: var(--nest-2); }
.folder-children .folder-children .folder-children { background: var(--nest-3); }
.folder-children .folder-children .folder-children .folder-children { background: var(--nest-4); }
.folder-caret {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 10px;
  color: var(--text-muted);
  width: 14px;
  padding: 0;
  line-height: 1;
  flex-shrink: 0;
}
.folder-icon { font-size: 14px; flex-shrink: 0; }
.folder-name {
  font-size: 13px;
  font-weight: 600;
  user-select: none;
  cursor: pointer;
}
.folder-rename-input {
  font-size: 13px;
  font-weight: 500;
  padding: 2px 8px;
  border: 1.5px solid var(--brand);
  border-radius: 5px;
  outline: none;
  background: var(--bg-card);
  color: var(--text);
}
.folder-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-out);
}
.folder-row:hover .folder-actions { opacity: 1; }
.btn-plus { font-size: 15px; font-weight: 600; line-height: 1; }
.del-icon { font-size: 18px; }
.folder-del-btn:hover { color: #fff; background: #f87171; }
</style>
