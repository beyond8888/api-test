/**
 * Export / Import utilities.
 *
 * Supports:
 * - Native JSON export (full fidelity)
 * - Postman Collection v2.1 export
 * - Postman Collection v2.1 import
 * - Native JSON import
 */
import type { Collection, Folder, SavedRequest, RequestConfig, AuthConfig, KV, MultipartFile, RawFormat } from '@/types'
import { uuid } from '@/utils/format'

// ---- Native Format ----

export function exportCollectionsNative(collections: Collection[]): string {
  return JSON.stringify(collections, null, 2)
}

export type CollectionFormat = 'postman' | 'native' | null

/**
 * Detect whether a raw JSON string is a Postman Collection v2.1 export or a
 * native collection export. Postman files may be wrapped as
 * `{ "collection": { "info": ..., "item": [...] } }` *or* a bare
 * `{ "info": ..., "item": [...] }`.
 */
export function detectCollectionFormat(raw: string): CollectionFormat {
  try {
    const parsed = JSON.parse(raw)
    const pm = parsed?.collection || parsed
    if (pm?.info && (pm?.info?.schema?.includes('getpostman.com') || pm?.item)) {
      return 'postman'
    }
    if (Array.isArray(parsed) || parsed?.requests || parsed?.folders || parsed?.name) {
      return 'native'
    }
    return null
  } catch {
    return null
  }
}

// ---- Postman Collection v2.1 Export ----

interface PmHeader { key: string; value: string; disabled?: boolean }
interface PmUrl { raw: string; protocol?: string; host?: string[]; port?: string; path?: string[]; query?: Array<{ key: string; value: string; disabled?: boolean }> }
interface PmBody {
  mode: string
  raw?: string
  urlencoded?: Array<{ key: string; value: string; disabled?: boolean }>
  formdata?: Array<{ key: string; value?: string; type: string; src?: string }>
  options?: Record<string, any>
}
interface PmAuth {
  type: string
  [key: string]: any
}
interface PmScriptEvent {
  listen: 'prerequest' | 'test'
  script: { exec: string[]; type?: string }
}
interface PmItem {
  name: string
  request?: {
    method: string
    url: string | PmUrl
    header?: PmHeader[]
    body?: PmBody
    auth?: PmAuth
  }
  event?: PmScriptEvent[]
  item?: PmItem[]
  auth?: PmAuth
}
interface PmCollection {
  info: {
    name: string
    _postman_id?: string
    description?: string
    schema: string
    _exporter_id?: string
  }
  item: PmItem[]
  auth?: PmAuth
  event?: PmScriptEvent[]
}

export function exportToPostman(collection: Collection): string {
  const pm = collectionToPostman(collection)
  return JSON.stringify({ collection: pm }, null, 2)
}

function collectionToPostman(collection: Collection): PmCollection {
  return {
    info: {
      name: collection.name,
      _postman_id: collection.id,
      schema: 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json',
    },
    item: [
      ...collection.requests.map((r) => requestToPmItem(r)),
      ...collection.folders.map((f) => folderToPmItem(f)),
    ],
  }
}

function folderToPmItem(folder: Folder): PmItem {
  return {
    name: folder.name,
    item: [
      ...folder.requests.map((r) => requestToPmItem(r)),
      ...folder.folders.map((f) => folderToPmItem(f)),
    ],
    auth: authToPmAuth(folder.auth),
  }
}

function requestToPmItem(req: SavedRequest): PmItem {
  const r = req.request
  const item: PmItem = {
    name: req.name || `${r.method} ${r.url}`,
    request: {
      method: r.method,
      url: buildPmUrl(r.url, r.queryParams),
      header: r.headers
        .filter((h) => h.enabled && h.key)
        .map((h) => ({ key: h.key, value: h.value })),
      body: bodyToPmBody(r),
      auth: authToPmAuth(r.auth),
    },
  }

  // Events for pre-request / post-response scripts
  const events: PmScriptEvent[] = []
  const preScript = req.preRequestScript || r.preRequestScript
  const postScript = req.postResponseScript || r.postResponseScript

  if (preScript) {
    events.push({ listen: 'prerequest', script: { exec: preScript.split('\n'), type: 'text/javascript' } })
  }
  if (postScript) {
    events.push({ listen: 'test', script: { exec: postScript.split('\n'), type: 'text/javascript' } })
  }

  if (events.length) {
    item.event = events
  }

  return item
}

function buildPmUrl(rawUrl: string, queryParams: KV[]): PmUrl {
  try {
    const url = new URL(rawUrl)
    const activeParams = queryParams.filter((p) => p.enabled && p.key)
    if (activeParams.length) {
      activeParams.forEach((p) => { url.searchParams.set(p.key, p.value) })
    }
    // Reconstruct raw with params
    const raw = activeParams.length
      ? `${url.origin}${url.pathname}?${url.searchParams.toString()}`
      : rawUrl
    return {
      raw,
      protocol: url.protocol.replace(':', ''),
      host: url.hostname.split('.'),
      port: url.port || undefined,
      path: url.pathname.split('/').filter(Boolean),
      query: activeParams.map((p) => ({ key: p.key, value: p.value })),
    }
  } catch {
    return { raw: rawUrl }
  }
}

function bodyToPmBody(config: RequestConfig): PmBody | undefined {
  switch (config.bodyType) {
    case 'none':
    case 'binary':
      return undefined
    case 'raw':
    case 'json':
      // `json` is treated as `raw` + rawFormat='json' (Postman-style).
      return {
        mode: 'raw',
        raw: config.body,
        options: { raw: { language: config.rawFormat || 'json' } },
      }
    case 'form':
      return { mode: 'urlencoded', urlencoded: parseFormBody(config.body) }
    case 'multipart':
      return {
        mode: 'formdata',
        formdata: [
          ...config.multipartFields
            .filter((f) => f.enabled && f.key)
            .map((f) => ({ key: f.key, value: f.value, type: 'text' })),
          ...config.multipartFiles.map((f) => ({
            key: f.field || f.name,
            type: 'file',
            src: `data:${f.type};base64,${(f.dataUrl || '').split(',')[1] || ''}`,
          })),
        ],
      }
    default:
      return undefined
  }
}

function parseFormBody(body: string): Array<{ key: string; value: string }> {
  try {
    return body.split('&').filter(Boolean).map((pair) => {
      const [key, value] = pair.split('=')
      return { key: decodeURIComponent(key || ''), value: decodeURIComponent(value || '') }
    })
  } catch {
    return []
  }
}

function authToPmAuth(auth: AuthConfig): PmAuth | undefined {
  switch (auth.type) {
    case 'none':
      return undefined
    case 'basic':
      return { type: 'basic', basic: [{ key: 'username', value: auth.username || '', type: 'string' }, { key: 'password', value: auth.password || '', type: 'string' }] }
    case 'bearer':
      return { type: 'bearer', bearer: [{ key: 'token', value: auth.token || '', type: 'string' }] }
    case 'api-key':
      return { type: 'apikey', apikey: [{ key: 'key', value: auth.key || '', type: 'string' }, { key: 'value', value: auth.value || '', type: 'string' }, { key: 'in', value: auth.addTo || 'header', type: 'string' }] }
    default:
      return undefined
  }
}

// ---- Postman Collection v2.1 Import ----

export function importFromPostman(json: string): Collection | null {
  try {
    const parsed = JSON.parse(json)
    const col = parsed.collection || parsed

    if (!col.info || !col.item) {
      throw new Error('Not a valid Postman Collection v2.x')
    }

    const collection: Collection = {
      id: col.info._postman_id || uuid(),
      name: col.info.name || 'Imported Collection',
      requests: [],
      folders: [],
      createdAt: Date.now(),
    }

    for (const item of col.item || []) {
      processPmItem(item, collection)
    }

    return collection
  } catch {
    return null
  }
}

function processPmItem(item: PmItem, collection: Collection, parentFolder?: Folder) {
  if (item.request) {
    // It's a request
    const savedReq = pmItemToSavedRequest(item)
    if (parentFolder) {
      parentFolder.requests.push(savedReq)
    } else {
      collection.requests.push(savedReq)
    }
  } else if (item.item && item.item.length) {
    // It's a folder
    const folder: Folder = {
      id: uuid(),
      name: item.name || 'Folder',
      requests: [],
      folders: [],
      auth: item.auth ? pmAuthToAuth(item.auth) : { type: 'none' },
    }

    for (const child of item.item) {
      processPmItem(child, collection, folder)
    }

    if (parentFolder) {
      parentFolder.folders.push(folder)
    } else {
      collection.folders.push(folder)
    }
  }
}

function pmItemToSavedRequest(item: PmItem): SavedRequest {
  const r = item.request!
  const method = (r.method || 'GET').toUpperCase() as RequestConfig['method']
  const url = typeof r.url === 'string' ? r.url : (r.url?.raw || '')

  // Parse URL for query params
  let rawUrl = url
  const queryParams: KV[] = []
  try {
    const urlObj = new URL(url)
    urlObj.searchParams.forEach((v, k) => {
      queryParams.push({ id: uuid(), key: k, value: v, desc: '', enabled: true })
    })
    rawUrl = `${urlObj.origin}${urlObj.pathname}`
  } catch { /* raw URL, can't parse */ }

  // Parse headers
  const headers: KV[] = (r.header || []).map((h) => ({
    id: uuid(),
    key: h.key,
    value: h.value,
    desc: '',
    enabled: !h.disabled,
  }))

  // Parse body
  let body = ''
  let bodyType: RequestConfig['bodyType'] = 'none'
  let rawFormat: RawFormat = 'json'
  const multipartFields: KV[] = []
  const multipartFiles: MultipartFile[] = []

  if (r.body) {
    switch (r.body.mode) {
      case 'raw':
        body = r.body.raw || ''
        bodyType = 'raw'
        rawFormat = (r.body.options?.raw?.language as RawFormat) || 'json'
        break
      case 'urlencoded':
        bodyType = 'form'
        if (r.body.urlencoded) {
          body = r.body.urlencoded
            .filter((p) => !p.disabled)
            .map((p) => `${encodeURIComponent(p.key)}=${encodeURIComponent(p.value)}`)
            .join('&')
        }
        // Ensure Content-Type is set for urlencoded bodies
        if (!headers.find((h) => h.key.toLowerCase() === 'content-type')) {
          headers.push({ id: uuid(), key: 'Content-Type', value: 'application/x-www-form-urlencoded', desc: '', enabled: true })
        }
        break
      case 'formdata':
        bodyType = 'multipart'
        if (r.body.formdata) {
          for (const fd of r.body.formdata) {
            if (fd.type === 'file') {
              multipartFiles.push({
                id: uuid(),
                field: fd.key,
                name: fd.src?.split('/').pop() || fd.key,
                type: 'application/octet-stream',
                size: 0,
                dataUrl: fd.src || '',
              })
            } else {
              multipartFields.push({
                id: uuid(),
                key: fd.key,
                value: fd.value || '',
                desc: '',
                enabled: true,
              })
            }
          }
        }
        break
      default:
        bodyType = 'none'
    }
  }

  // Parse auth
  const auth = r.auth ? pmAuthToAuth(r.auth) : { type: 'none' as const }

  // Parse scripts
  let preRequestScript: string | undefined
  let postResponseScript: string | undefined

  if (item.event) {
    for (const ev of item.event) {
      if (ev.listen === 'prerequest' && ev.script?.exec) {
        preRequestScript = ev.script.exec.join('\n')
      }
      if (ev.listen === 'test' && ev.script?.exec) {
        postResponseScript = ev.script.exec.join('\n')
      }
    }
  }

  const savedReq: SavedRequest = {
    id: uuid(),
    name: item.name || `${method} ${url}`,
    preRequestScript,
    postResponseScript,
    request: {
      method,
      url: rawUrl,
      headers,
      queryParams,
      body,
      bodyType,
      rawFormat,
      multipartFields,
      multipartFiles,
      auth,
    },
  }

  return savedReq
}

function pmAuthToAuth(pmAuth: PmAuth): AuthConfig {
  switch (pmAuth.type) {
    case 'basic': {
      const b = pmAuth.basic || []
      return { type: 'basic', username: b[0]?.value || '', password: b[1]?.value || '' }
    }
    case 'bearer': {
      const b = pmAuth.bearer || []
      return { type: 'bearer', token: b[0]?.value || '' }
    }
    case 'apikey': {
      const b = pmAuth.apikey || []
      return { type: 'api-key', key: b[0]?.value || '', value: b[1]?.value || '', addTo: (b[2]?.value || 'header') as 'header' | 'query' }
    }
    default:
      return { type: 'none' }
  }
}

// ---- cURL Export ----

/**
 * Convert a RequestConfig into a cURL command string.
 *
 * Variable placeholders like {{baseUrl}} are preserved as literals so the
 * generated command is portable across environments.
 *
 * Multipart file payloads cannot be embedded in a cURL command — file fields
 * are emitted as `-F 'field=@filename'` and the file must exist on disk when
 * the command runs.
 */
export function requestToCurl(config: RequestConfig): string {
  const args: string[] = ['curl']

  // GET is curl's default; only emit -X for other methods
  const method = config.method.toUpperCase()
  if (method !== 'GET') args.push(`-X ${method}`)

  args.push(shellQuote(buildCurlUrl(config)))

  for (const [k, v] of collectCurlHeaders(config)) {
    args.push(`-H ${shellQuote(`${k}: ${v}`)}`)
  }

  if (config.auth.type === 'basic') {
    args.push(`-u ${shellQuote(`${config.auth.username || ''}:${config.auth.password || ''}`)}`)
  }

  switch (config.bodyType) {
    case 'json':
    case 'raw':
      if (config.body) args.push(`--data-raw ${shellQuote(config.body)}`)
      break
    case 'form':
      if (config.body) args.push(`--data ${shellQuote(config.body)}`)
      break
    case 'multipart':
      for (const f of config.multipartFields.filter((f) => f.enabled && f.key)) {
        args.push(`-F ${shellQuote(`${f.key}=${f.value}`)}`)
      }
      for (const f of config.multipartFiles.filter((f) => f.field)) {
        args.push(`-F ${shellQuote(`${f.field}=@${f.name}`)}`)
      }
      break
    case 'none':
    default:
      break
  }

  return args.join(' \\\n  ')
}

/** Build the URL string with query params (and api-key auth in query mode) appended. */
function buildCurlUrl(config: RequestConfig): string {
  const params: Array<[string, string]> = config.queryParams
    .filter((p) => p.enabled && p.key)
    .map((p) => [p.key, p.value])

  if (config.auth.type === 'api-key' && config.auth.addTo === 'query' && config.auth.key) {
    params.push([config.auth.key, config.auth.value || ''])
  }

  if (!params.length) return config.url
  const qs = params.map(([k, v]) => `${k}=${v}`).join('&')
  return config.url.includes('?') ? `${config.url}&${qs}` : `${config.url}?${qs}`
}

/** Collect enabled headers, folding bearer and api-key (header mode) auth into the list. */
function collectCurlHeaders(config: RequestConfig): Array<[string, string]> {
  const headers: Array<[string, string]> = config.headers
    .filter((h) => h.enabled && h.key)
    .map((h) => [h.key, h.value])

  const auth = config.auth
  if (auth.type === 'bearer' && auth.token) {
    headers.push(['Authorization', `Bearer ${auth.token}`])
  } else if (auth.type === 'api-key' && auth.addTo !== 'query' && auth.key) {
    headers.push([auth.key, auth.value || ''])
  }

  return headers
}

/** Wrap a string in single quotes, escaping inner single quotes with the `'\''` sequence. */
function shellQuote(s: string): string {
  return `'${s.replace(/'/g, `'\\''`)}'`
}

// ---- File download helper ----

export function downloadFile(content: string, filename: string, mime = 'application/json') {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
