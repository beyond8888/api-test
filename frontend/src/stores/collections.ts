import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Collection, Folder, SavedRequest, AuthConfig } from '@/types'
import { uuid } from '@/utils/format'
import {
  fetchCollections, createCollection as apiCreate,
  updateCollection as apiUpdate, deleteCollection as apiDelete,
} from '@/services/data'
import { exportToPostman, exportCollectionsNative, importFromPostman, detectCollectionFormat } from '@/utils/exportImport'
import { logger } from '@/utils/logger'

type DbId = number | string

/** Guard against pathologically deep (or cyclic) collection trees. */
const MAX_TREE_DEPTH = 50

export const useCollectionsStore = defineStore('collections', () => {
  const collections = ref<Collection[]>([])

  async function init() {
    try {
      collections.value = await fetchCollections()
    } catch (e) {
      logger.error('[collections] Failed to load:', e)
    }
  }

  function toDbId(id: DbId): number {
    return typeof id === 'string' ? Number.parseInt(id, 10) : id
  }

  function findCol(id: DbId): Collection | undefined {
    const numId = toDbId(id)
    return collections.value.find((c) => c.dbId === numId)
  }

  async function persist(dbId: DbId) {
    const id = toDbId(dbId)
    const col = findCol(id)
    if (!col) return
    try {
      await apiUpdate(id, { data: col, name: col.name })
    } catch (e) {
      logger.error('[collections] Failed to persist:', e)
    }
  }

  // ─── Collection-level ops ────────────────────────────────────────

  async function createCollection(name: string, _description = ''): Promise<number | undefined> {
    const col = await apiCreate(name, _description)
    collections.value.unshift(col)
    return col.dbId
  }

  async function deleteCollection(dbId: DbId) {
    const id = toDbId(dbId)
    await apiDelete(id)
    collections.value = collections.value.filter((c) => c.dbId !== id)
  }

  async function renameCollection(dbId: DbId, name: string) {
    const col = findCol(dbId)
    if (!col) return
    col.name = name
    await persist(dbId)
  }

  async function setCollectionAuth(dbId: DbId, auth: AuthConfig) {
    const col = findCol(dbId)
    if (!col) return
    col.auth = auth
    await persist(dbId)
  }

  // ─── Recursive helpers ───────────────────────────────────────────

  function findFolder(folders: Folder[], folderId: string, depth = 0): Folder | null {
    if (depth > MAX_TREE_DEPTH) return null
    for (const f of folders) {
      if (f.id === folderId) return f
      const found = findFolder(f.folders, folderId, depth + 1)
      if (found) return found
    }
    return null
  }

  function findFolderPath(folders: Folder[], folderId: string, trail: Folder[] = [], depth = 0): Folder[] | null {
    if (depth > MAX_TREE_DEPTH) return null
    for (const f of folders) {
      const path = [...trail, f]
      if (f.id === folderId) return path
      const found = findFolderPath(f.folders, folderId, path, depth + 1)
      if (found) return found
    }
    return null
  }

  function findRequest(collection: Collection, requestId: string): SavedRequest | null {
    for (const r of collection.requests) {
      if (r.id === requestId) return r
    }
    for (const folder of collection.folders) {
      const found = findRequestInFolder(folder, requestId)
      if (found) return found
    }
    return null
  }

  function findRequestInFolder(folder: Folder, requestId: string, depth = 0): SavedRequest | null {
    if (depth > MAX_TREE_DEPTH) return null
    for (const r of folder.requests) {
      if (r.id === requestId) return r
    }
    for (const sub of folder.folders) {
      const found = findRequestInFolder(sub, requestId, depth + 1)
      if (found) return found
    }
    return null
  }

  function findRequestFolderPath(folders: Folder[], requestId: string, depth = 0): Folder[] | null {
    if (depth > MAX_TREE_DEPTH) return null
    for (const f of folders) {
      if (f.requests.some((r) => r.id === requestId)) return [f]
      const found = findRequestFolderPath(f.folders, requestId, depth + 1)
      if (found) return [f, ...found]
    }
    return null
  }

  /** Find which folder (by id) contains a request, or null if at root */
  function findRequestFolderId(collection: Collection, requestId: string): string | null {
    if (collection.requests.some((r) => r.id === requestId)) return null
    const search = (folders: Folder[], depth = 0): string | null => {
      if (depth > MAX_TREE_DEPTH) return null
      for (const f of folders) {
        if (f.requests.some((r) => r.id === requestId)) return f.id
        const found = search(f.folders, depth + 1)
        if (found) return found
      }
      return null
    }
    return search(collection.folders)
  }

  // ─── Folder ops ──────────────────────────────────────────────────

  async function createFolder(dbId: DbId, parentId: string | null, folderOrName: Folder | string) {
    const col = findCol(dbId)
    if (!col) return
    const folder: Folder = typeof folderOrName === 'string'
      ? { id: uuid(), name: folderOrName, folders: [], requests: [], auth: { type: 'none' } }
      : folderOrName
    if (parentId) {
      const parent = findFolder(col.folders, parentId)
      if (parent) parent.folders.push(folder)
    } else {
      col.folders.push(folder)
    }
    await persist(dbId)
  }

  async function deleteFolder(dbId: DbId, folderId: string) {
    const col = findCol(dbId)
    if (!col) return
    const removeFrom = (folders: Folder[], depth = 0) => {
      if (depth > MAX_TREE_DEPTH) return false
      const idx = folders.findIndex((f) => f.id === folderId)
      if (idx >= 0) { folders.splice(idx, 1); return true }
      for (const f of folders) { if (removeFrom(f.folders, depth + 1)) return true }
      return false
    }
    removeFrom(col.folders)
    await persist(dbId)
  }

  async function renameFolder(dbId: DbId, folderId: string, name: string) {
    const col = findCol(dbId)
    if (!col) return
    const folder = findFolder(col.folders, folderId)
    if (folder) {
      folder.name = name
      await persist(dbId)
    }
  }

  async function setFolderAuth(dbId: DbId, folderId: string, auth: AuthConfig) {
    const col = findCol(dbId)
    if (!col) return
    const folder = findFolder(col.folders, folderId)
    if (folder) {
      folder.auth = auth
      await persist(dbId)
    }
  }

  // ─── Request ops ─────────────────────────────────────────────────

  async function addRequest(dbId: DbId, folderId: string | null, request: SavedRequest) {
    const col = findCol(dbId)
    if (!col) return
    if (folderId) {
      const folder = findFolder(col.folders, folderId)
      if (folder) folder.requests.push(request)
    } else {
      col.requests.push(request)
    }
    await persist(dbId)
  }

  async function deleteRequest(dbId: DbId, requestId: string, folderId?: string | null) {
    const col = findCol(dbId)
    if (!col) return
    const fid = folderId !== undefined ? folderId : findRequestFolderId(col, requestId)
    if (fid) {
      const folder = findFolder(col.folders, fid)
      if (folder) folder.requests = folder.requests.filter((r) => r.id !== requestId)
    } else {
      col.requests = col.requests.filter((r) => r.id !== requestId)
    }
    await persist(dbId)
  }

  /** Alias for deleteRequest — backward compatibility */
  async function removeRequest(dbId: DbId, requestId: string, folderId?: string | null) {
    return deleteRequest(dbId, requestId, folderId)
  }

  async function renameRequest(dbId: DbId, requestId: string, name: string) {
    const col = findCol(dbId)
    if (!col) return
    const req = findRequest(col, requestId)
    if (req) {
      req.name = name
      await persist(dbId)
    }
  }

  /** Fully replace a saved request's contents (used by "Save" on an open tab). */
  async function updateRequest(dbId: DbId, requestId: string, request: SavedRequest) {
    const col = findCol(dbId)
    if (!col) return
    const req = findRequest(col, requestId)
    if (req) {
      req.name = request.name
      req.request = request.request
      req.preRequestScript = request.preRequestScript
      req.postResponseScript = request.postResponseScript
      await persist(dbId)
    }
  }

  async function moveRequest(
    dbId: DbId, requestId: string,
    fromFolderId: string | null, toFolderId?: string | null, toIndex?: number,
  ) {
    const col = findCol(dbId)
    if (!col) return

    // If toFolderId is not provided (old 3-arg call), use it as target folder only
    const targetFolder = toFolderId !== undefined ? toFolderId : fromFolderId
    const targetIndex = toIndex ?? 0

    // Auto-detect source folder if not provided
    const srcFolder = fromFolderId !== null ? fromFolderId : null

    let req: SavedRequest | undefined
    if (srcFolder) {
      const folder = findFolder(col.folders, srcFolder)
      if (folder) {
        req = folder.requests.find((r) => r.id === requestId)
        folder.requests = folder.requests.filter((r) => r.id !== requestId)
      }
    } else {
      req = col.requests.find((r) => r.id === requestId)
      col.requests = col.requests.filter((r) => r.id !== requestId)
    }
    if (!req) return

    if (targetFolder) {
      const folder = findFolder(col.folders, targetFolder)
      if (folder) folder.requests.splice(targetIndex, 0, req)
    } else {
      col.requests.splice(targetIndex, 0, req)
    }
    await persist(dbId)
  }

  async function duplicateRequest(dbId: DbId, requestId: string, folderId?: string | null) {
    const col = findCol(dbId)
    if (!col) return
    const original = findRequest(col, requestId)
    if (!original) return
    const dup: SavedRequest = {
      ...JSON.parse(JSON.stringify(original)),
      id: uuid(),
      name: `${original.name} (copy)`,
    }
    // Use provided folderId or auto-detect
    const fid = folderId !== undefined ? folderId : findRequestFolderId(col, requestId)
    await addRequest(dbId, fid, dup)
  }

  async function setRequestAuth(dbId: DbId, requestId: string, auth: AuthConfig, _folderId?: string | null) {
    const col = findCol(dbId)
    if (!col) return
    const req = findRequest(col, requestId)
    if (req) {
      req.request.auth = auth
      await persist(dbId)
    }
  }

  // ─── Script ops ─────────────────────────────────────────────────

  async function updateCollectionScript(dbId: DbId, scriptType: 'pre' | 'post', script: string) {
    const col = findCol(dbId)
    if (!col) return
    if (scriptType === 'pre') col.preRequestScript = script
    await persist(dbId)
  }

  async function updateRequestScript(dbId: DbId, requestId: string, scriptType: 'pre' | 'post', script: string) {
    const col = findCol(dbId)
    if (!col) return
    const req = findRequest(col, requestId)
    if (req) {
      if (scriptType === 'pre') req.preRequestScript = script
      else req.postResponseScript = script
      await persist(dbId)
    }
  }

  /** Reorder request within same folder/root */
  async function reorderRequest(dbId: DbId, fromIndex: number, toIndex: number, folderId: string | null = null) {
    const col = findCol(dbId)
    if (!col) return
    const list = folderId ? findFolder(col.folders, folderId)?.requests : col.requests
    if (!list) return
    const [item] = list.splice(fromIndex, 1)
    list.splice(toIndex, 0, item)
    await persist(dbId)
  }

  /** Get effective auth by walking up the tree (request → folder → collection) */
  function getEffectiveAuth(collection: Collection, requestId: string): AuthConfig {
    // Check folder chain first
    const folderPath = findRequestFolderPath(collection.folders, requestId)
    if (folderPath) {
      for (const f of folderPath) {
        if (f.auth && f.auth.type !== 'none') return f.auth
      }
    }
    // Then collection-level
    if (collection.auth && collection.auth.type !== 'none') return collection.auth
    return { type: 'none' }
  }

  // ─── Export / Import (delegates to utils/exportImport) ──────────

  function exportCollectionPostman(collection: Collection) {
    return exportToPostman(collection)
  }

  function exportCollectionNative(collection: Collection) {
    return exportCollectionsNative([collection])
  }

  function exportAllNative() {
    return exportCollectionsNative(collections.value)
  }

  /** Persist an array of collections (creating each on the backend). */
  async function importCollections(data: Collection[]) {
    for (const col of data) {
      const tree: Collection = {
        id: col.id || uuid(),
        name: col.name,
        description: col.description,
        requests: col.requests,
        folders: col.folders,
        createdAt: col.createdAt || Date.now(),
        preRequestScript: col.preRequestScript,
        auth: col.auth,
      }
      // Create in a single round-trip (no empty-then-PATCH two-phase).
      const newCol = await apiCreate(col.name, col.description || '', tree)
      collections.value.unshift(newCol)
    }
  }

  /**
   * Import a raw JSON string (Postman v2.1 or native) and persist it as a
   * new collection. Returns true on success.
   */
  async function importCollectionRaw(raw: string): Promise<boolean> {
    const fmt = detectCollectionFormat(raw)
    if (fmt === 'postman') {
      const col = importFromPostman(raw)
      if (!col) return false
      await importCollections([col])
      return true
    }
    if (fmt === 'native') {
      try {
        const parsed = JSON.parse(raw)
        const data: Collection[] = Array.isArray(parsed) ? parsed : [parsed]
        await importCollections(data)
        return true
      } catch {
        return false
      }
    }
    return false
  }

  return {
    collections,
    init,
    findCol,
    createCollection,
    deleteCollection,
    renameCollection,
    setCollectionAuth,
    findFolder,
    findFolderPath,
    findRequest,
    findRequestFolderPath,
    createFolder,
    deleteFolder,
    renameFolder,
    setFolderAuth,
    addRequest,
    deleteRequest,
    removeRequest,
    renameRequest,
    updateRequest,
    moveRequest,
    duplicateRequest,
    setRequestAuth,
    updateCollectionScript,
    updateRequestScript,
    reorderRequest,
    getEffectiveAuth,
    exportCollectionNative,
    exportCollectionPostman,
    exportAllNative,
    importCollections,
    importCollectionRaw,
  }
})
