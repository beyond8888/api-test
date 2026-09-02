<template>
  <div class="tools-page">
    <!-- ---- Sidebar ---- -->
    <aside class="tools-sidebar">
      <div class="sidebar-inner">
        <template v-for="cat in toolCategories" :key="cat.key">
          <div class="cat-label">{{ cat.label }}</div>
          <button
            v-for="tool in getToolsByCategory(cat.key)"
            :key="tool.id"
            class="tool-item"
            :class="{ active: activeTool === tool.id }"
            @click="selectTool(tool.id)"
          >
            <span class="tool-icon" v-html="toolIcon(tool.icon)"></span>
            <div class="tool-text">
              <span class="tool-name">{{ tool.name }}</span>
              <span class="tool-desc">{{ tool.desc }}</span>
            </div>
          </button>
        </template>
      </div>
    </aside>

    <!-- ---- Workspace ---- -->
    <main class="tools-workspace">
      <template v-if="activeToolDef">
        <div class="workspace-header">
          <span class="ws-icon" v-html="toolIcon(activeToolDef.icon)"></span>
          <div>
            <h2 class="ws-title">{{ activeToolDef.name }}</h2>
          </div>
        </div>
        <div class="workspace-body">
          <component :is="activeToolDef.component" />
        </div>
      </template>

      <!-- Empty placeholder -->
      <div v-else class="workspace-empty">
        <div class="empty-icon-circle">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="6" width="20" height="12" rx="2"/>
            <path d="M12 12h.01M17 12h.01M7 12h.01"/>
          </svg>
        </div>
        <div class="empty-text">选择一个工具</div>
        <div class="empty-sub">从左侧列表中选择一个工具开始使用</div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { toolCategories, toolRegistry, getToolsByCategory } from '@/composables/useToolRegistry'

const activeTool = ref('')

const activeToolDef = computed(() => {
  return toolRegistry.find(t => t.id === activeTool.value)
})

function selectTool(id: string) {
  activeTool.value = id
}

// Simple SVG icons for each tool type
const iconMap: Record<string, string> = {
  idcard: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><line x1="8" y1="2" x2="8" y2="4"/><line x1="16" y1="2" x2="16" y2="4"/><circle cx="9" cy="10" r="2"/><line x1="12" y1="14" x2="18" y2="14"/><line x1="12" y1="16" x2="18" y2="16"/></svg>`,
  license: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><line x1="2" y1="9" x2="22" y2="9"/><line x1="8" y1="2" x2="8" y2="7"/><line x1="16" y1="2" x2="16" y2="7"/><circle cx="12" cy="16" r="3"/></svg>`,
  kafka: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>`,
  rocketmq: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8l9-5 9 5-9 5-9-5z"/><path d="M3 8v8l9 5 9-5V8"/><line x1="12" y1="13" x2="12" y2="21"/></svg>`,
  'vehicle-license': `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><rect x="5" y="9" width="8" height="6" rx="1"/><line x1="16" y1="10" x2="19" y2="10"/><line x1="16" y1="13" x2="19" y2="13"/><line x1="6" y1="3" x2="6" y2="5"/><line x1="18" y1="3" x2="18" y2="5"/></svg>`,
}

function toolIcon(key: string): string {
  return iconMap[key] || ''
}
</script>

<style scoped>
.tools-page {
  max-width: var(--page-max);
  margin: 0 auto;
  padding: 28px 0 48px;
  display: flex;
  gap: 24px;
  min-height: calc(100vh - 130px);
}

/* ---- Sidebar ---- */
.tools-sidebar {
  width: 268px;
  flex-shrink: 0;
}
.sidebar-inner {
  position: sticky; top: 80px;
}
.cat-label {
  font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.8px;
  color: var(--text-muted);
  padding: 16px 4px 8px;
}
.cat-label:first-child { padding-top: 0; }

.tool-item {
  display: flex; align-items: flex-start; gap: 12px;
  width: 100%;
  padding: 12px 12px;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  text-align: left;
  transition: all var(--duration-fast) var(--ease-out);
  color: var(--text-secondary);
}
.tool-item:hover {
  background: var(--bg-hover);
  color: var(--text);
}
.tool-item.active {
  background: var(--brand-bg);
  color: var(--text);
  box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.25);
}
.tool-icon {
  flex-shrink: 0; margin-top: 1px;
  display: flex; align-items: center; justify-content: center;
  width: 32px; height: 32px;
  border-radius: var(--radius-xs);
  background: var(--bg-subtle);
}
.tool-item.active .tool-icon {
  background: linear-gradient(135deg, rgba(99,102,241,0.3), rgba(168,85,247,0.25));
}
.tool-text { min-width: 0; }
.tool-name {
  display: block; font-size: 13.5px; font-weight: 600;
  margin-bottom: 2px;
}
.tool-desc {
  display: block; font-size: 11.5px;
  color: var(--text-muted);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ---- Workspace ---- */
.tools-workspace {
  flex: 1; min-width: 0;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.workspace-header {
  display: flex; align-items: center; gap: 14px;
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border);
}
.ws-icon {
  width: 40px; height: 40px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(168,85,247,0.15));
}
.ws-title {
  font-size: 18px; font-weight: 600;
  color: var(--text); margin: 0;
}
.workspace-body {
  padding: 24px;
}

/* Empty */
.workspace-empty {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 100px 40px; text-align: center;
}
.workspace-empty .empty-icon-circle {
  margin-bottom: 20px;
}
.workspace-empty .empty-text {
  font-size: 17px; font-weight: 600; color: var(--text);
  margin-bottom: 6px;
}
.workspace-empty .empty-sub {
  font-size: 13px; color: var(--text-muted);
}
</style>
