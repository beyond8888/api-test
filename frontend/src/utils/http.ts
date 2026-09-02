/**
 * HTTP 请求构建与响应解析的共享工具函数。
 *
 * 之前 useProxyExecutor 维护了一份近乎相同的
 * 逻辑（headers 构建、auth 处理、proxy payload 组装、响应解析），
 * 现统一收口到此处，避免后续改动时两边不同步。
 */
import type { RequestConfig, ResponseData, AuthConfig, KV } from '@/types'
import { applyVariables } from '@/utils/scriptEngine'
import { kvToObject } from '@/utils/format'
import { DEFAULT_PROXY_TIMEOUT } from '@/utils/constants'

// ─── 响应体类型检测 ─────────────────────────────────────────────

/** 根据响应体内容和 Content-Type 推断展示类型（json/html/xml/text） */
export function detectBodyType(body: string, contentType: string): ResponseData['bodyType'] {
  if (contentType.includes('application/json')) return 'json'
  if (contentType.includes('text/html')) return 'html'
  if (contentType.includes('xml')) return 'xml'
  if (body) {
    try { JSON.parse(body); return 'json' } catch { /* not JSON */ }
  }
  return 'text'
}

// ─── 请求头构建 ──────────────────────────────────────────────────

/**
 * 从 RequestConfig.headers 构建请求头对象，应用变量替换。
 * 只保留 enabled 且有 key 的项。
 */
export function buildHeaders(
  headers: KV[],
  vars: Record<string, any>,
): Record<string, string> {
  return kvToObject(headers, (v) => applyVariables(v, vars))
}

// ─── 认证头处理 ──────────────────────────────────────────────────

/**
 * 根据 auth 配置写入 Authorization 或自定义 header。
 * 如果 auth.addTo === 'query'（仅 api-key），则将 key/value 写入 queryParams。
 *
 * @returns 如果有 query 模式的 auth，返回需要追加的 query params
 */
export function applyAuth(
  headers: Record<string, string>,
  auth: AuthConfig,
  vars: Record<string, any>,
): Record<string, string> {
  if (auth.type === 'basic' && auth.username && auth.password) {
    const user = applyVariables(auth.username, vars)
    const pass = applyVariables(auth.password, vars)
    headers.Authorization = `Basic ${btoa(`${user}:${pass}`)}`
  } else if (auth.type === 'bearer' && auth.token) {
    headers.Authorization = `Bearer ${applyVariables(auth.token, vars)}`
  } else if (auth.type === 'api-key' && auth.key && auth.value) {
    if (auth.addTo === 'query') {
      // Return as query params instead of headers
      return { [auth.key]: applyVariables(auth.value, vars) }
    } else {
      headers[auth.key] = applyVariables(auth.value, vars)
    }
  }
  return {}
}

// ─── 代理 payload 构建 ──────────────────────────────────────────

/**
 * 将 RequestConfig 转换为后端代理接口所需的 payload。
 *
 * 处理内容：
 *   - URL / method / headers（含变量替换 + auth）
 *   - 普通请求体 → payload.body
 *   - multipart 请求 → payload.body_type/form_fields/files
 *   - 超时（默认 DEFAULT_PROXY_TIMEOUT）
 *
 * @returns { payload, resolvedUrl, resolvedBody } 同时返回解析后的 URL 和 body，
 *          方便调用方记录"实际发送的请求快照"
 */
export function buildProxyPayload(
  config: RequestConfig,
  vars: Record<string, any>,
  opts?: { timeout?: number },
): {
  payload: Record<string, any>
  resolvedUrl: string
  resolvedBody: string
} {
  // 1. headers + auth
  const headers = buildHeaders(config.headers, vars)
  const authQueryParams = applyAuth(headers, config.auth, vars)

  // 2. URL / body 变量替换
  const resolvedUrl = applyVariables(config.url, vars)
  const resolvedBody = applyVariables(config.body, vars)

  // 3. Query params — filter enabled, apply variable replacement
  const queryParams = kvToObject(config.queryParams, (v) => applyVariables(v, vars))
  // Merge auth query params (api-key with addTo='query')
  Object.assign(queryParams, authQueryParams)

  // 4. 组装 payload
  const payload: Record<string, any> = {
    url: resolvedUrl,
    method: config.method,
    headers,
    query_params: queryParams,
    timeout: opts?.timeout && opts.timeout > 0 ? opts.timeout : DEFAULT_PROXY_TIMEOUT,
  }

  if (config.bodyType === 'multipart') {
    // multipart：删除可能存在的 Content-Type，由后端自动设置 boundary
    delete headers['Content-Type']
    delete headers['content-type']

    const formFields = kvToObject(config.multipartFields, (v) => applyVariables(v, vars))

    payload.body_type = 'multipart'
    payload.form_fields = formFields
    payload.files = config.multipartFiles.map((f) => ({
      field: f.field || f.name,
      name: f.name,
      type: f.type,
      content_base64: (f.dataUrl || '').split(',')[1] || '',
    }))
  } else {
    payload.body = resolvedBody
  }

  return { payload, resolvedUrl, resolvedBody }
}

// ─── 代理响应解析 ────────────────────────────────────────────────

/**
 * 将后端代理接口返回的 data 解析为前端的 ResponseData。
 * 如果上游返回了 error 字段，则抛出包含错误信息。
 */
export function parseProxyResponse(data: Record<string, unknown>): ResponseData {
  if (data.error) {
    throw new ProxyError(data.error as string, data.timing as number | undefined)
  }
  return {
    status: data.status as number,
    statusText: (data.statusText as string) || '',
    headers: (data.headers as Record<string, string>) || {},
    body: (data.body as string) || '',
    bodyType: detectBodyType((data.body as string) || '', (data.headers as Record<string, string>)?.['content-type'] || ''),
    size: (data.size as number) || 0,
    timing: (data.timing as number) || 0,
  }
}

/** 代理接口返回的错误（携带 timing 便于日志） */
export class ProxyError extends Error {
  timing?: number
  constructor(message: string, timing?: number) {
    super(message)
    this.name = 'ProxyError'
    this.timing = timing
  }
}
