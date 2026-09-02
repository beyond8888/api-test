<template>
  <n-modal
    :show="workspace.showSaveModal.value"
    preset="card"
    title="Save Request"
    :bordered="false"
    style="width: 440px"
    :mask-closable="false"
    @update:show="(v: boolean) => { if (!v) workspace.cancelSave() }"
  >
    <n-space vertical size="medium">
      <div>
        <label class="field-label">Name</label>
        <n-input v-model:value="workspace.saveName.value" placeholder="Request name" size="medium" />
      </div>

      <div>
        <label class="field-label">Collection</label>
        <n-select
          v-if="!workspace.createNewCollection.value"
          :value="workspace.saveTargetColId.value"
          :options="collectionOptions"
          placeholder="Select a collection"
          @update:value="(v: number | null) => (workspace.saveTargetColId.value = v)"
        />
        <label v-else class="new-col-toggle">
          <input type="checkbox" checked disabled />
          Creating “{{ workspace.newCollectionName.value || 'Default' }}”
        </label>
      </div>

      <div>
        <label class="field-label">
          <label class="new-col-check">
            <input type="checkbox" v-model="workspace.createNewCollection.value" />
            Save into a new collection
          </label>
        </label>
        <n-input
          v-if="workspace.createNewCollection.value"
          v-model:value="workspace.newCollectionName.value"
          placeholder="New collection name"
          size="medium"
        />
      </div>

      <div v-if="!workspace.createNewCollection.value">
        <label class="field-label">Folder</label>
        <n-select
          :value="workspace.saveTargetFolderId.value"
          :options="workspace.folderOptions.value"
          placeholder="Root"
          clearable
          @update:value="(v: string | null) => (workspace.saveTargetFolderId.value = v)"
        />
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 8px">
        <n-button @click="workspace.cancelSave()">Cancel</n-button>
        <n-button type="primary" @click="workspace.confirmSave()">Save</n-button>
      </div>
    </n-space>
  </n-modal>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NModal, NSpace, NInput, NSelect, NButton } from 'naive-ui'
import { useWorkspace } from '@/composables/useWorkspace'

const workspace = useWorkspace()

const collectionOptions = computed(() =>
  workspace.saveTargets.value.map((c) => ({ label: c.name, value: c.dbId as number })),
)
</script>

<style scoped>
.field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.new-col-check {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
}
.new-col-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
