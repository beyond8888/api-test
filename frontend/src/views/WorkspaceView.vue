<template>
  <div class="workspace">
    <WorkspaceSidebar />
    <main class="workspace-main">
      <TabBar />
      <div class="editor-scroll">
        <BuilderView />
      </div>
    </main>
    <SaveRequestModal />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import WorkspaceSidebar from '@/components/workspace/WorkspaceSidebar.vue'
import TabBar from '@/components/workspace/TabBar.vue'
import SaveRequestModal from '@/components/workspace/SaveRequestModal.vue'
import BuilderView from '@/views/BuilderView.vue'
import { provideWorkspace } from '@/composables/useWorkspace'

const workspace = provideWorkspace()

onMounted(() => {
  workspace.init()
})
</script>

<style scoped>
.workspace {
  height: calc(100vh - 52px);
  display: flex;
  min-height: 0;
  overflow: hidden;
}
.workspace-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.editor-scroll {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
</style>
