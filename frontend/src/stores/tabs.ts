import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { EditorSnapshot } from '@/types'
import { uuid } from '@/utils/format'

/** A single open editor tab. Tabs are ephemeral — never persisted to the backend. */
export interface TabState {
  id: string
  title: string
  /** Set when this tab is bound to a saved collection request. */
  savedRequestId?: string
  savedColDbId?: number
  savedFolderId?: string | null
  snapshot: EditorSnapshot
  /** True when the live editor differs from the saved request. */
  dirty: boolean
}

/** A blank "New Request" editor snapshot. */
export function blankSnapshot(): EditorSnapshot {
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
    preRequestScript: '',
    postResponseScript: '',
    customTimeout: 0,
  }
}

export const useTabsStore = defineStore('tabs', () => {
  const tabs = ref<TabState[]>([])
  const activeId = ref<string | null>(null)

  const activeTab = computed(() => tabs.value.find((t) => t.id === activeId.value) || null)

  function makeTab(partial?: Partial<TabState>): TabState {
    return {
      id: uuid(),
      title: 'New Request',
      savedRequestId: undefined,
      savedColDbId: undefined,
      savedFolderId: undefined,
      snapshot: blankSnapshot(),
      dirty: false,
      ...partial,
    }
  }

  /**
   * Open a request in a tab. If a tab is already bound to the same saved
   *  request, focus it instead of opening a duplicate.
   */
  function openTab(opts?: {
    snapshot?: EditorSnapshot
    title?: string
    savedRequestId?: string
    savedColDbId?: number
    savedFolderId?: string | null
  }): string {
    if (opts?.savedRequestId) {
      const existing = tabs.value.find((t) => t.savedRequestId === opts.savedRequestId)
      if (existing) {
        activeId.value = existing.id
        return existing.id
      }
    }
    const tab = makeTab({
      snapshot: opts?.snapshot ?? blankSnapshot(),
      title: opts?.title ?? 'New Request',
      savedRequestId: opts?.savedRequestId,
      savedColDbId: opts?.savedColDbId,
      savedFolderId: opts?.savedFolderId,
    })
    tabs.value.push(tab)
    activeId.value = tab.id
    return tab.id
  }

  /** A brand-new blank tab. */
  function newTab(): string {
    return openTab({ snapshot: blankSnapshot(), title: 'New Request' })
  }

  function closeTab(id: string) {
    const idx = tabs.value.findIndex((t) => t.id === id)
    if (idx === -1) return
    tabs.value.splice(idx, 1)
    if (activeId.value === id) {
      // Focus a neighbour (prefer the one to the left)
      const neighbour = tabs.value[idx - 1] || tabs.value[0]
      activeId.value = neighbour ? neighbour.id : null
    }
  }

  function setActive(id: string) {
    activeId.value = id
  }

  /**
   * Persist the live editor snapshot into a tab.
   *  markDirty=true (default) flips the dirty flag — used for live edits.
   *  Call with markDirty=false when simply switching tabs so a clean tab
   *  doesn't become dirty just because we stashed its state.
   */
  function updateSnapshot(id: string, snap: EditorSnapshot, markDirty = true) {
    const tab = tabs.value.find((t) => t.id === id)
    if (!tab) return
    tab.snapshot = snap
    if (markDirty) tab.dirty = true
  }

  /** Record that a tab's contents were saved to a collection request. */
  function markSaved(
    id: string,
    meta: { savedRequestId: string; savedColDbId: number; savedFolderId: string | null; title: string },
  ) {
    const tab = tabs.value.find((t) => t.id === id)
    if (!tab) return
    tab.savedRequestId = meta.savedRequestId
    tab.savedColDbId = meta.savedColDbId
    tab.savedFolderId = meta.savedFolderId
    tab.title = meta.title
    tab.dirty = false
  }

  function renameTab(id: string, title: string) {
    const tab = tabs.value.find((t) => t.id === id)
    if (tab) tab.title = title
  }

  return {
    tabs,
    activeId,
    activeTab,
    openTab,
    newTab,
    closeTab,
    setActive,
    updateSnapshot,
    markSaved,
    renameTab,
  }
})
