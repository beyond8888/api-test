<template>
  <div class="tabbar-wrap">
    <button
      class="tab-scroll-btn"
      :class="{ hidden: !canScrollLeft }"
      title="Scroll left"
      @click="scrollBy(-SCROLL_STEP)"
    >‹</button>

    <div class="tabbar" ref="tabbarEl" @scroll="updateArrows">
      <div
        v-for="tab in tabsStore.tabs"
        :key="tab.id"
        class="tab"
        :class="{ active: tab.id === tabsStore.activeId }"
        :ref="(el) => registerTabRef(tab.id, el)"
        @click="tabsStore.setActive(tab.id)"
      >
        <span class="tab-dot" v-if="tab.dirty" title="Unsaved changes"></span>
        <span class="tab-title">{{ tab.title }}</span>
        <button class="tab-close" :class="{ 'show': tab.id === tabsStore.activeId }" title="Close"
          @click.stop="close(tab.id)">
&times;
</button>
      </div>
      <button class="tab-new" title="New Request" @click="tabsStore.newTab()">+</button>
    </div>

    <button
      class="tab-scroll-btn"
      :class="{ hidden: !canScrollRight }"
      title="Scroll right"
      @click="scrollBy(SCROLL_STEP)"
    >›</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useTabsStore } from '@/stores/tabs'

const tabsStore = useTabsStore()

const tabbarEl = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)
const SCROLL_STEP = 240

// Track tab DOM nodes so we can scroll the active one into view.
const tabRefs = new Map<string, HTMLElement>()
function registerTabRef(id: string, el: unknown) {
  if (el) tabRefs.set(id, el as HTMLElement)
  else tabRefs.delete(id)
}

function updateArrows() {
  const el = tabbarEl.value
  if (!el) return
  const { scrollLeft, scrollWidth, clientWidth } = el
  canScrollLeft.value = scrollLeft > 1
  canScrollRight.value = scrollLeft + clientWidth < scrollWidth - 1
}

function scrollBy(delta: number) {
  tabbarEl.value?.scrollBy({ left: delta, behavior: 'smooth' })
}

// Ensure the active tab is visible when it changes (e.g. opened / switched).
function scrollActiveIntoView() {
  const el = tabRefs.get(tabsStore.activeId || '')
  if (el && tabbarEl.value) {
    const { left, right } = el.getBoundingClientRect()
    const { left: barLeft, right: barRight } = tabbarEl.value.getBoundingClientRect()
    if (left < barLeft) tabbarEl.value.scrollLeft -= barLeft - left
    else if (right > barRight) tabbarEl.value.scrollLeft += right - barRight
  }
  updateArrows()
}

onMounted(() => {
  updateArrows()
  scrollActiveIntoView()
})

watch(() => tabsStore.activeId, () => nextTick(scrollActiveIntoView))
watch(() => tabsStore.tabs.length, () => nextTick(updateArrows))

function close(id: string) {
  tabsStore.closeTab(id)
  if (tabsStore.tabs.length === 0) tabsStore.newTab()
}
</script>

<style scoped>
.tabbar-wrap {
  display: flex;
  align-items: stretch;
  flex-shrink: 0;
  background: var(--bg-subtle);
  border-bottom: 1px solid var(--border);
}

.tabbar {
  display: flex;
  align-items: stretch;
  height: 38px;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  scroll-behavior: smooth;
}
.tabbar::-webkit-scrollbar { height: 0; }

.tab-scroll-btn {
  border: none;
  background: var(--bg-subtle);
  color: var(--text-muted);
  font-size: 16px;
  line-height: 1;
  width: 28px;
  flex-shrink: 0;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid var(--border);
}
.tabbar-wrap > .tab-scroll-btn:last-child {
  border-right: none;
  border-left: 1px solid var(--border);
}
.tab-scroll-btn:hover { background: var(--bg-hover); color: var(--text); }
.tab-scroll-btn.hidden { visibility: hidden; }

.tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px 0 14px;
  height: 100%;
  border-right: 1px solid var(--border);
  font-size: 12.5px;
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
  max-width: 220px;
  position: relative;
  transition: background var(--duration-fast) var(--ease-out);
}
.tab:hover { background: var(--bg-hover); }
.tab.active {
  background: var(--bg-card);
  color: var(--text);
  box-shadow: inset 0 -2px 0 var(--brand);
}

.tab-dot {
  width: 7px;
  height: 7px;
  border-radius: 99px;
  background: var(--brand);
  flex-shrink: 0;
}
.tab-title {
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.tab-close {
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 15px;
  line-height: 1;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  cursor: pointer;
  display: none;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.tab:hover .tab-close,
.tab.active .tab-close { display: inline-flex; }
.tab-close:hover { background: var(--bg-selected); color: var(--text); }

.tab-new {
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 18px;
  line-height: 1;
  width: 38px;
  cursor: pointer;
  flex-shrink: 0;
}
.tab-new:hover { background: var(--bg-hover); color: var(--text); }
</style>
