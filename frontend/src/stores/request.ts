import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { KV, AuthConfig, RequestConfig, RawFormat, ParseResult, MultipartFile, EditorSnapshot } from '@/types'
import { uuid } from '@/utils/format'

function makeKV(key: string, value: string, enabled = true): KV {
  return { id: uuid(), key, value, desc: '', enabled }
}

// Postman-style raw sub-format → Content-Type mapping.
const RAW_FORMAT_CONTENT_TYPE: Record<RawFormat, string> = {
  json: 'application/json',
  text: 'text/plain',
  xml: 'application/xml',
  html: 'text/html',
  javascript: 'application/javascript',
}

/**
 * Editor mirror for the *active* tab. Holds only editable request state.
 * Execution results (response, errors, sent snapshot, test results) live in the
 * dedicated `responseStore` so they are not mixed into the tab-snapshot cycle.
 */
export const useRequestStore = defineStore('request', () => {
  const method = ref<RequestConfig['method']>('GET')
  const url = ref('')
  const headers = ref<KV[]>([makeKV('Content-Type', 'application/json')])
  const queryParams = ref<KV[]>([])
  const body = ref('')
  const bodyType = ref<RequestConfig['bodyType']>('raw')
  const rawFormat = ref<RawFormat>('json')
  const multipartFields = ref<KV[]>([])
  const multipartFiles = ref<MultipartFile[]>([])
  const auth = ref<AuthConfig>({ type: 'none' })
  const preRequestScript = ref('')
  const postResponseScript = ref('')
  const customTimeout = ref(0)

  // Tracks the id of the auto-added `Content-Type` header so we only ever remove
  // the one our code added (never a user's manual entry). Applies to `raw` /
  // `json` bodies (mirrors Postman auto-setting Content-Type for raw bodies).
  const autoContentTypeHeaderId = ref<string | null>(null)
  const autoContentTypeValue = ref<string | null>(null)

  function currentAutoContentType(): string | null {
    // `json` body type is treated identically to `raw` + rawFormat='json'.
    if (bodyType.value === 'json') return RAW_FORMAT_CONTENT_TYPE.json
    if (bodyType.value === 'raw') return RAW_FORMAT_CONTENT_TYPE[rawFormat.value]
    return null
  }

  function hasContentType(): boolean {
    return headers.value.some(
      (h) => h.enabled && h.key.trim().toLowerCase() === 'content-type',
    )
  }

  /** Keep autoContentTypeHeaderId in sync with the current body type/format. */
  function syncAutoContentTypeHeader() {
    const expected = currentAutoContentType()
    if (expected) {
      if (autoContentTypeHeaderId.value) {
        // Already tracked — make sure it still exists with the right value.
        const h = headers.value.find((x) => x.id === autoContentTypeHeaderId.value)
        if (!h || h.value !== expected) {
          // Value changed (e.g. raw format switched) — drop old, re-add below.
          if (h && autoContentTypeValue.value && h.value === autoContentTypeValue.value) {
            const idx = headers.value.indexOf(h)
            headers.value.splice(idx, 1)
          }
          autoContentTypeHeaderId.value = null
          autoContentTypeValue.value = null
        }
      }
      if (!autoContentTypeHeaderId.value) {
        const existing = headers.value.find(
          (h) => h.enabled && h.key.trim().toLowerCase() === 'content-type' && h.value === expected,
        )
        if (existing) {
          autoContentTypeHeaderId.value = existing.id
          autoContentTypeValue.value = expected
        } else if (!hasContentType()) {
          const kv = makeKV('Content-Type', expected)
          headers.value.push(kv)
          autoContentTypeHeaderId.value = kv.id
          autoContentTypeValue.value = expected
        }
      }
    } else {
      // Non-raw body — drop the auto-added header if still present.
      if (autoContentTypeHeaderId.value) {
        const idx = headers.value.findIndex((h) => h.id === autoContentTypeHeaderId.value)
        if (idx !== -1 && h_eq(headers.value[idx], autoContentTypeValue.value)) {
          headers.value.splice(idx, 1)
        }
        autoContentTypeHeaderId.value = null
        autoContentTypeValue.value = null
      }
    }
  }

  function h_eq(h: KV, value: string | null): boolean {
    return !!value && h.value === value
  }

  /** Switch body type. `json`/`raw` auto-manage a Content-Type header. */
  function setBodyType(type: RequestConfig['bodyType']) {
    bodyType.value = type
    syncAutoContentTypeHeader()
  }

  /** Switch the raw sub-format (Postman-style dropdown). */
  function setRawFormat(format: RawFormat) {
    rawFormat.value = format
    syncAutoContentTypeHeader()
  }

  function setFromParsed(parsed: ParseResult) {
    // Method - uppercase
    method.value = (parsed.method?.toUpperCase() as RequestConfig['method']) || 'GET'

    // URL
    url.value = parsed.url || ''

    // Headers dict to KV[]
    if (parsed.headers) {
      headers.value = Object.entries(parsed.headers).map(([key, value]) =>
        makeKV(key, value)
      )
    }

    // Query params dict to KV[] — always reset (clear old, set new or empty)
    queryParams.value = parsed.query_params
      ? Object.entries(parsed.query_params).map(([key, value]) => makeKV(key, value))
      : []

    // Body — backend wraps it as { type, content, form_fields }.
    // `content` is the raw body string (a JSON string for json bodies),
    // `type` mirrors body_type.
    const parsedBody = parsed.body
    const bodyTypeLabel = parsed.body_type || parsedBody?.type || ''
    if (parsedBody && parsedBody.content) {
      const bodyContent = parsedBody.content
      if (bodyTypeLabel === 'json') {
        body.value = bodyContent
        setBodyType('raw')
        setRawFormat('json')
      } else if (bodyTypeLabel === 'text') {
        body.value = bodyContent
        setBodyType('raw')
        setRawFormat('text')
      } else if (bodyTypeLabel === 'xml') {
        body.value = bodyContent
        setBodyType('raw')
        setRawFormat('xml')
      } else if (bodyTypeLabel === 'html') {
        body.value = bodyContent
        setBodyType('raw')
        setRawFormat('html')
      } else if (bodyTypeLabel === 'javascript') {
        body.value = bodyContent
        setBodyType('raw')
        setRawFormat('javascript')
      } else if (bodyTypeLabel === 'form') {
        body.value = bodyContent
        setBodyType('form')
      } else if (bodyTypeLabel === 'multipart') {
        // multipart/form-data — fill the multipart fields from form_fields.
        body.value = bodyContent
        setBodyType('multipart')
        if (parsedBody?.form_fields?.length) {
          multipartFields.value = parsedBody.form_fields.map((f: { field: string; value: string }) =>
            makeKV(f.field, f.value)
          )
        }
      } else {
        // Unknown / no specific label → treat as generic raw text.
        body.value = bodyContent
        setBodyType('raw')
        setRawFormat('text')
      }
    } else {
      body.value = ''
      setBodyType('none')
    }

    // Multipart form fields — always reset before populating.
    // Backend nests form_fields inside body; fall back to top-level if present.
    multipartFields.value = []
    const pbf = parsedBody?.form_fields || (parsed as any).form_fields || []
    if (pbf && pbf.length > 0) {
      pbf.forEach((ff: { field: string; value: string }) => {
        multipartFields.value.push(makeKV(ff.field, ff.value))
      })
      setBodyType('multipart')
    }

    // Cookies — convert to Cookie header and add to headers
    if (parsed.cookies && Object.keys(parsed.cookies).length > 0) {
      const cookieStr = Object.entries(parsed.cookies).map(([k, v]) => `${k}=${v}`).join('; ')
      headers.value.push(makeKV('Cookie', cookieStr))
    }

    // Auth config — extract from parsed headers (e.g., Authorization: Bearer xxx)
    const authHeader = parsed.headers.Authorization || parsed.headers.authorization
    if (authHeader?.startsWith('Bearer ')) {
      auth.value = { type: 'bearer', token: authHeader.slice(7) }
    } else if (authHeader?.startsWith('Basic ')) {
      try {
        const decoded = atob(authHeader.slice(6))
        const [user, pass] = decoded.split(':')
        auth.value = { type: 'basic', username: user || '', password: pass || '' }
      } catch {
        auth.value = { type: 'none' }
      }
    } else {
      auth.value = { type: 'none' }
    }
  }

  function reset() {
    method.value = 'GET'
    url.value = ''
    headers.value = [makeKV('Content-Type', 'application/json')]
    queryParams.value = []
    body.value = ''
    bodyType.value = 'raw'
    rawFormat.value = 'json'
    multipartFields.value = []
    multipartFiles.value = []
    auth.value = { type: 'none' }
    preRequestScript.value = ''
    postResponseScript.value = ''
    customTimeout.value = 0
    syncAutoContentTypeHeader()
  }

  /** Serialize the editable editor state into a tab snapshot. */
  function snapshot(): EditorSnapshot {
    return {
      method: method.value,
      url: url.value,
      headers: headers.value,
      queryParams: queryParams.value,
      body: body.value,
      bodyType: bodyType.value,
      rawFormat: rawFormat.value,
      multipartFields: multipartFields.value,
      multipartFiles: multipartFiles.value,
      auth: auth.value,
      preRequestScript: preRequestScript.value,
      postResponseScript: postResponseScript.value,
      customTimeout: customTimeout.value,
    }
  }

  /** Restore a previously saved editor state from a tab snapshot. */
  function restore(s: EditorSnapshot) {
    method.value = s.method
    url.value = s.url
    headers.value = s.headers
    queryParams.value = s.queryParams
    body.value = s.body
    bodyType.value = s.bodyType
    // Backward-compat: older snapshots had no rawFormat; derive from bodyType.
    rawFormat.value = (s as any).rawFormat || (s.bodyType === 'json' ? 'json' : 'text')
    multipartFields.value = s.multipartFields
    multipartFiles.value = s.multipartFiles
    auth.value = s.auth
    preRequestScript.value = s.preRequestScript
    postResponseScript.value = s.postResponseScript
    customTimeout.value = s.customTimeout
    syncAutoContentTypeHeader()
  }

  return {
    method,
    url,
    headers,
    queryParams,
    body,
    bodyType,
    rawFormat,
    multipartFields,
    multipartFiles,
    auth,
    preRequestScript,
    postResponseScript,
    customTimeout,
    snapshot,
    restore,
    setFromParsed,
    setBodyType,
    setRawFormat,
    reset,
  }
})
