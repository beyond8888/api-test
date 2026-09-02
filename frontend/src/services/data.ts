/**
 * Data API service — Collections, Environments, History.
 *
 * Maps backend API responses to frontend types.
 * Replaces the old localStorage-based stores.
 */
import { useApiClient } from '@/composables/useApiClient'
import { fetchAllPages } from './pagination'
import type { Collection, KV, RequestConfig, ResponseData } from '@/types'

const { client } = useApiClient()

// ─── Collections ──────────────────────────────────────────────────

/** Backend collection record */
interface CollectionRecord {
  id: number
  name: string
  description: string
  data: Collection
  created_at: string
  updated_at: string
}

/** Fetch all collections — follows pagination, returns Collection[] with dbId set */
export async function fetchCollections(): Promise<Collection[]> {
  const records = await fetchAllPages<CollectionRecord>(client, '/collections/')
  return records.map((r) => ({ ...r.data, dbId: r.id, name: r.data.name || r.name }))
}

/** Fetch a single collection by DB id */
export async function fetchCollection(dbId: number): Promise<Collection> {
  const res = await client.get(`/collections/${dbId}/`)
  const r: CollectionRecord = res.data
  return { ...r.data, dbId: r.id }
}

/** Create a new collection — returns Collection with dbId.
 *
 *  A single POST carries the full tree in `data`, so no follow-up PATCH is
 *  needed (the previous two-phase create could leave an empty collection if
 *  the second request failed). Pass `initialData` to create with content
 *  (e.g. on import) in one round-trip.
 */
export async function createCollection(
  name: string,
  description = '',
  initialData?: Collection,
): Promise<Collection> {
  const treeData: Collection = initialData ?? {
    id: crypto.randomUUID?.() || Date.now().toString(),
    name,
    requests: [],
    folders: [],
    createdAt: Date.now(),
  }
  const res = await client.post('/collections/', {
    name, description, data: treeData,
  })
  const r = res.data
  // The response may be wrapped ({ code, data }) or a raw DRF record.
  // `id` lives at the top level in both cases — guard against undefined.
  const dbId = r?.id ?? r?.data?.id
  if (dbId == null) {
    throw new Error('Server did not return a collection id on create')
  }
  return { ...treeData, dbId }
}

/** Persist collection tree data to backend */
export async function updateCollection(dbId: number, data: Partial<{
  name: string
  description: string
  data: Collection
}>): Promise<void> {
  await client.patch(`/collections/${dbId}/`, data)
}

/** Delete a collection by DB id */
export async function deleteCollection(dbId: number): Promise<void> {
  await client.delete(`/collections/${dbId}/`)
}

// ─── Environments ─────────────────────────────────────────────────

export interface EnvironmentData {
  id: number
  name: string
  is_active: boolean
  variables: KV[]
  created_at: string
  updated_at: string
}

export async function fetchEnvironments(): Promise<EnvironmentData[]> {
  return fetchAllPages<EnvironmentData>(client, '/environments/')
}

export async function createEnvironment(name: string): Promise<EnvironmentData> {
  const res = await client.post('/environments/', { name, variables: [] })
  return res.data
}

export async function updateEnvironment(id: number, data: Partial<EnvironmentData>): Promise<void> {
  await client.patch(`/environments/${id}/`, data)
}

export async function deleteEnvironment(id: number): Promise<void> {
  await client.delete(`/environments/${id}/`)
}

export async function activateEnvironment(id: number): Promise<void> {
  await client.post(`/environments/${id}/activate/`)
}

// ─── History ──────────────────────────────────────────────────────

export interface HistoryEntryData {
  id: number
  request: RequestConfig
  response: ResponseData | null
  timestamp: string
}

export interface PaginatedHistory {
  results: HistoryEntryData[]
  count: number
  next: string | null
}

export async function fetchHistory(page = 1, pageSize = 50): Promise<PaginatedHistory> {
  const res = await client.get('/history/', { params: { page, page_size: pageSize } })
  const data = res.data
  // HistoryViewSet is paginated → {count, next, previous, results}.
  if (Array.isArray(data)) {
    return { results: data, count: data.length, next: null }
  }
  const d = data as Record<string, unknown>
  return {
    results: (d.results as HistoryEntryData[]) ?? [],
    count: (d.count as number) ?? 0,
    next: (d.next as string | null) ?? null,
  }
}

/**
 * Strip heavy base64 file payloads from a request config before persisting it
 * to history — keep only file metadata to avoid bloating storage / transfer.
 */
function stripFilePayloads(request: RequestConfig): RequestConfig {
  if (!request || !Array.isArray(request.multipartFiles)) {
    return request
  }
  return {
    ...request,
    multipartFiles: request.multipartFiles.map((f) => {
      const { dataUrl, ...rest } = f
      return rest
    }),
  }
}

export async function createHistoryEntry(
  request: RequestConfig,
  response: ResponseData | null,
): Promise<HistoryEntryData> {
  const res = await client.post('/history/', { request: stripFilePayloads(request), response })
  return res.data
}

export async function deleteHistoryEntry(id: number): Promise<void> {
  await client.delete(`/history/${id}/`)
}

export async function clearHistory(): Promise<void> {
  await client.delete('/history/clear/')
}
