import { watch, ref, reactive, computed, inject, provide, type InjectionKey, type Ref, type ComputedRef } from 'vue'
import { useMessage } from 'naive-ui'
import { useRequestStore } from '@/stores/request'
import { useTabsStore } from '@/stores/tabs'
import { useCollectionsStore } from '@/stores/collections'
import { useResponseStore } from '@/stores/response'
import { uuid } from '@/utils/format'
import type { EditorSnapshot, RequestConfig, SavedRequest, Collection, Folder } from '@/types'

export interface WorkspaceApi {
  /** Create the initial blank tab if none exist. Call from WorkspaceView onMounted. */
  init: () => void
  /** Save the active tab: update the linked request, or open the save modal. */
  saveActiveRequest: () => void
  /** Close the currently active tab (opening a fresh one if none remain). */
  closeActiveTab: () => void
  /** Open a saved collection request in a tab (focusing it if already open). */
  openRequestInTab: (req: SavedRequest, col: Collection, folderId: string | null) => void
  /** Open a request config (e.g. from history) in a new unsaved tab. */
  openHistoryInTab: (config: RequestConfig) => void
  // ── Sidebar collection expand state ──
  collapsed: Record<string, boolean>
  toggle: (id: string) => void
  expandCollection: (colDbId: number) => void
  // ── Save modal state ──
  showSaveModal: Ref<boolean>
  saveName: Ref<string>
  saveTargetColId: Ref<number | null>
  createNewCollection: Ref<boolean>
  newCollectionName: Ref<string>
  saveTargetFolderId: Ref<string | null>
  saveTargets: ComputedRef<Collection[]>
  folderOptions: ComputedRef<{ label: string; value: string }[]>
  confirmSave: () => Promise<void>
  cancelSave: () => void
}

export const WorkspaceKey: InjectionKey<WorkspaceApi> = Symbol('workspace')

/** Build a RequestConfig out of an editor snapshot. */
function snapshotToConfig(s: EditorSnapshot): RequestConfig {
  return {
    method: s.method,
    url: s.url,
    headers: s.headers,
    queryParams: s.queryParams,
    body: s.body,
    bodyType: s.bodyType,
    rawFormat: s.rawFormat || (s.bodyType === 'json' ? 'json' : 'text'),
    multipartFields: s.multipartFields,
    multipartFiles: s.multipartFiles,
    auth: s.auth,
    preRequestScript: s.preRequestScript,
    postResponseScript: s.postResponseScript,
  }
}

function defaultName(config: RequestConfig): string {
  let path = config.url
  try { path = new URL(config.url).pathname } catch { /* keep raw url */ }
  return `${config.method} ${path || 'request'}`
}

function buildSnapshotFromRequest(req: SavedRequest): EditorSnapshot {
  const r = req.request
  return {
    method: r.method,
    url: r.url,
    headers: r.headers,
    queryParams: r.queryParams,
    body: r.body,
    bodyType: r.bodyType,
    rawFormat: (r as any).rawFormat || (r.bodyType === 'json' ? 'json' : 'text'),
    multipartFields: r.multipartFields || [],
    multipartFiles: r.multipartFiles || [],
    auth: r.auth,
    preRequestScript: req.preRequestScript || r.preRequestScript || '',
    postResponseScript: req.postResponseScript || r.postResponseScript || '',
    customTimeout: 0,
  }
}

function buildSnapshotFromConfig(config: RequestConfig): EditorSnapshot {
  return {
    method: config.method,
    url: config.url,
    headers: config.headers,
    queryParams: config.queryParams,
    body: config.body,
    bodyType: config.bodyType,
    rawFormat: config.rawFormat || (config.bodyType === 'json' ? 'json' : 'text'),
    multipartFields: config.multipartFields || [],
    multipartFiles: config.multipartFiles || [],
    auth: config.auth,
    preRequestScript: config.preRequestScript || '',
    postResponseScript: config.postResponseScript || '',
    customTimeout: 0,
  }
}

function createWorkspace(): WorkspaceApi {
  const requestStore = useRequestStore()
  const tabsStore = useTabsStore()
  const collectionsStore = useCollectionsStore()
  const responseStore = useResponseStore()
  const message = useMessage()

  // Collapsed state for collections in the sidebar (keyed by collection id).
  const collapsed = reactive<Record<string, boolean>>({})
  function toggle(id: string) {
    collapsed[id] = !collapsed[id]
  }
  /** Ensure a collection (by dbId) is expanded so its contents are visible. */
  function expandCollection(colDbId: number) {
    const c = collectionsStore.findCol(colDbId)
    if (c) collapsed[c.id] = false
  }

  // Guard so our own restore() doesn't get flagged as a user edit.
  let suppressing = false

  function restoreActive() {
    const tab = tabsStore.activeTab
    suppressing = true
    if (tab) requestStore.restore(tab.snapshot)
    else requestStore.reset()
    suppressing = false
    // Response/execution results are global (not per-tab). Clear them on every
    // tab switch so a new/other request does not show a previous request's response.
    responseStore.reset()
  }

  // ── Tab ↔ editor sync ──
  watch(
    () => tabsStore.activeId,
    (newId, oldId) => {
      // Stash the outgoing tab's live state (without flipping dirty).
      if (oldId) tabsStore.updateSnapshot(oldId, requestStore.snapshot(), false)
      restoreActive()
      void newId
    },
    { immediate: true },
  )

  // Mark the active tab dirty on any live edit.
  // flush:'sync' so the callback runs during our own restore() (while
  // `suppressing` is true) and is skipped — otherwise it would fire after
  // suppressing is reset and wrongly flag the restored tab as dirty.
  watch(
    () => [
      requestStore.method, requestStore.url, requestStore.headers, requestStore.queryParams,
      requestStore.body, requestStore.bodyType, requestStore.multipartFields,
      requestStore.multipartFiles, requestStore.auth, requestStore.preRequestScript,
      requestStore.postResponseScript, requestStore.customTimeout,
    ],
    () => {
      if (suppressing) return
      if (!tabsStore.activeId) return
      tabsStore.updateSnapshot(tabsStore.activeId, requestStore.snapshot(), true)
    },
    { deep: true, flush: 'sync' },
  )

  function init() {
    if (tabsStore.tabs.length === 0) tabsStore.newTab()
  }

  function currentConfig(): RequestConfig {
    return snapshotToConfig(requestStore.snapshot())
  }

  function saveActiveRequest() {
    const tab = tabsStore.activeTab
    if (!tab) return
    const config = currentConfig()
    const name = tab.title && tab.title !== 'New Request' ? tab.title : defaultName(config)

    if (tab.savedRequestId && tab.savedColDbId) {
      collectionsStore.updateRequest(tab.savedColDbId, tab.savedRequestId, {
        id: tab.savedRequestId,
        name,
        request: config,
        preRequestScript: config.preRequestScript,
        postResponseScript: config.postResponseScript,
      })
      tabsStore.markSaved(tab.id, {
        savedRequestId: tab.savedRequestId,
        savedColDbId: tab.savedColDbId,
        savedFolderId: tab.savedFolderId ?? null,
        title: name,
      })
      message.success('已保存')
      return
    }

    // Unsaved → open the save modal.
    saveName.value = name
    saveTargetColId.value = collectionsStore.collections[0]?.dbId ?? null
    createNewCollection.value = false
    newCollectionName.value = ''
    saveTargetFolderId.value = null
    showSaveModal.value = true
  }

  async function confirmSave() {
    const tab = tabsStore.activeTab
    if (!tab) { showSaveModal.value = false; return }
    const config = currentConfig()
    const name = saveName.value.trim() || defaultName(config)

    let colDbId: number
    if (createNewCollection.value || saveTargetColId.value == null) {
      const newId = await collectionsStore.createCollection(newCollectionName.value.trim() || 'Default')
      if (!newId) { message.error('保存失败'); return }
      colDbId = newId
    } else {
      colDbId = saveTargetColId.value as number
    }

    const folderId = saveTargetFolderId.value
    const newReqId = uuid()
    await collectionsStore.addRequest(colDbId, folderId, {
      id: newReqId,
      name,
      request: config,
      preRequestScript: config.preRequestScript,
      postResponseScript: config.postResponseScript,
    })
    tabsStore.markSaved(tab.id, {
      savedRequestId: newReqId,
      savedColDbId: colDbId,
      savedFolderId: folderId ?? null,
      title: name,
    })
    expandCollection(colDbId)
    showSaveModal.value = false
    const col = collectionsStore.findCol(colDbId)
    message.success(`已保存到 “${col?.name ?? '集合'}”`)
  }

  function cancelSave() {
    showSaveModal.value = false
  }

  function closeActiveTab() {
    if (tabsStore.activeId) tabsStore.closeTab(tabsStore.activeId)
    if (tabsStore.tabs.length === 0) tabsStore.newTab()
  }

  function openRequestInTab(req: SavedRequest, col: Collection, folderId: string | null) {
    tabsStore.openTab({
      snapshot: buildSnapshotFromRequest(req),
      title: req.name,
      savedRequestId: req.id,
      savedColDbId: col.dbId,
      savedFolderId: folderId,
    })
  }

  function openHistoryInTab(config: RequestConfig) {
    tabsStore.openTab({ snapshot: buildSnapshotFromConfig(config), title: defaultName(config) })
  }

  // ── Save modal reactive state ──
  const showSaveModal = ref(false)
  const saveName = ref('')
  const saveTargetColId = ref<number | null>(null)
  const createNewCollection = ref(false)
  const newCollectionName = ref('')
  const saveTargetFolderId = ref<string | null>(null)

  const saveTargets = computed(() => collectionsStore.collections)

  const folderOptions = computed(() => {
    const col = collectionsStore.collections.find((c) => c.dbId === saveTargetColId.value)
    const flat: { label: string; value: string }[] = [{ label: 'Root', value: '' }]
    if (!col) return flat
    const walk = (folders: Folder[], prefix = '') => {
      for (const f of folders) {
        const label = prefix ? `${prefix} / ${f.name}` : f.name
        flat.push({ label, value: f.id })
        walk(f.folders, label)
      }
    }
    walk(col.folders)
    return flat
  })

  return {
    init,
    saveActiveRequest,
    closeActiveTab,
    openRequestInTab,
    openHistoryInTab,
    collapsed,
    toggle,
    expandCollection,
    showSaveModal,
    saveName,
    saveTargetColId,
    createNewCollection,
    newCollectionName,
    saveTargetFolderId,
    saveTargets,
    folderOptions,
    confirmSave,
    cancelSave,
  }
}

/** Provide the workspace instance (call once in WorkspaceView setup). */
export function provideWorkspace(): WorkspaceApi {
  const api = createWorkspace()
  provide(WorkspaceKey, api)
  return api
}

/** Inject the workspace instance (use in BuilderView / sidebar). */
export function useWorkspace(): WorkspaceApi {
  const api = inject(WorkspaceKey)
  if (!api) throw new Error('useWorkspace must be used within WorkspaceView')
  return api
}
