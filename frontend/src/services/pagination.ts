import type { AxiosInstance } from 'axios'

/**
 * Extract the item array from either a plain array or a Django paginated
 * `{ results: [...] }` envelope. Shared by both single-page and paged calls so
 * we don't keep re-implementing the same branch in every service.
 */
export function extractList(data: unknown): unknown[] {
  if (Array.isArray(data)) return data
  if (
    data &&
    typeof data === 'object' &&
    'results' in data &&
    Array.isArray((data as Record<string, unknown>).results)
  ) {
    return (data as Record<string, unknown>).results as unknown[]
  }
  return []
}

/**
 * Follow Django cursor pagination (`next` URL) until exhausted and return the
 * concatenated items.
 *
 * `initialParams` are only sent on the first request; subsequent pages use the
 * `next` URL which already carries the query string, so we must not re-send
 * params (and overwrite them) on later iterations.
 */
export async function fetchAllPages<T = unknown>(
  client: AxiosInstance,
  initialUrl: string,
  initialParams?: Record<string, unknown>,
): Promise<T[]> {
  const out: T[] = []
  let url: string | null = initialUrl
  let first = true
  while (url) {
    const res = await client.get(url, first ? { params: initialParams } : undefined)
    out.push(...(extractList(res.data) as T[]))
    const page = res.data as { next?: string | null } | unknown[]
    url = Array.isArray(page) ? null : (page.next ?? null)
    first = false
  }
  return out
}
