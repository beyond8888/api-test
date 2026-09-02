/**
 * Script execution engine with a Postman-like pm API.
 *
 * ⚠️ Security note: this is NOT a security sandbox. Scripts run with full
 * page privileges (window, fetch, localStorage, ...) via `new Function`.
 * Only run scripts you authored. Never execute untrusted / third-party
 * scripts (e.g. shared collections) — that is arbitrary code execution in
 * the user's browser (stored XSS / RCE).
 *
 * Pre-request scripts can use:
 *   pm.variables.set/get    – runtime variables (reset per request)
 *   pm.environment.get      – read current environment variables
 *   pm.request              – { method, url, headers, body }
 *
 * Post-response scripts can additionally use:
 *   pm.response             – { status, statusText, headers, body, json(), size, timing }
 *   pm.environment.set      – write back to environment
 *   pm.test(name, fn)
 *   pm.expect(value)        – assertion chain
 */
import type { RequestConfig, ResponseData, ScriptTestResult } from '@/types'
import { kvToObject } from '@/utils/format'
import { logger } from '@/utils/logger'

// ---- Minimal expect / assertion library ----
function createExpect(actual: any) {
  const chain: any = {
    get not() {
      this._not = !this._not
      return this
    },
    _not: false,
    _assert(pred: boolean, msg: string) {
      const ok = this._not ? !pred : pred
      if (!ok) { const sign = this._not ? '(not) ' : ''; throw new Error(`expect ${sign}${msg}`) }
      this._not = false
    },
    toBe(expected: any) { this._assert(actual === expected, `toBe ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`) },
    toEqual(expected: any) { this._assert(deepEqual(actual, expected), `toEqual ${JSON.stringify(expected)}`) },
    toBeTruthy() { this._assert(!!actual, 'toBeTruthy') },
    toBeFalsy() { this._assert(!actual, 'toBeFalsy') },
    toBeNull() { this._assert(actual === null, 'toBeNull') },
    toBeUndefined() { this._assert(actual === undefined, 'toBeUndefined') },
    toBeDefined() { this._assert(actual !== undefined, 'toBeDefined') },
    toBeGreaterThan(n: number) { this._assert(actual > n, `toBeGreaterThan ${n}, got ${actual}`) },
    toBeLessThan(n: number) { this._assert(actual < n, `toBeLessThan ${n}, got ${actual}`) },
    toContain(item: any) {
      const ok = typeof actual === 'string'
        ? actual.includes(item)
        : Array.isArray(actual)
          ? actual.some((v: any) => deepEqual(v, item))
          : false
      this._assert(ok, `toContain ${JSON.stringify(item)}`)
    },
    toMatch(re: RegExp) { this._assert(re.test(String(actual)), `toMatch ${re}`) },
    toHaveProperty(prop: string, val?: any) {
      const has = actual != null && prop in actual
      if (arguments.length < 2) {
        this._assert(has, `toHaveProperty "${prop}"`)
      } else {
        this._assert(has && deepEqual(actual[prop], val), `toHaveProperty "${prop}" = ${JSON.stringify(val)}`)
      }
    },
    toHaveLength(n: number) {
      this._assert(
        actual != null && typeof (actual as any).length === 'number' && (actual as any).length === n,
        `toHaveLength ${n}`
      )
    },
    toBeTypeOf(type: 'string' | 'number' | 'boolean' | 'object' | 'function' | 'undefined' | 'symbol' | 'bigint') {
      // eslint-disable-next-line valid-typeof
      this._assert(typeof actual === type, `toBeTypeOf "${type}", got ${typeof actual}`)
    },
  }
  return chain
}

function deepEqual(a: any, b: any): boolean {
  if (a === b) return true
  if (a == null || b == null) return false
  if (typeof a !== typeof b) return false
  if (typeof a === 'object') {
    const keysA = Object.keys(a)
    const keysB = Object.keys(b)
    if (keysA.length !== keysB.length) return false
    return keysA.every((k) => deepEqual(a[k], b[k]))
  }
  return false
}

// ---- pm API ----
class PmVariables {
  private store: Record<string, any> = {}
  get(key: string): any { return key in this.store ? this.store[key] : undefined }
  set(key: string, value: any) { this.store[key] = value }
  has(key: string): boolean { return key in this.store }
  toObject(): Record<string, any> { return { ...this.store } }
  clear() { this.store = {} }
}

class PmEnvironment {
  constructor(private readVars: Record<string, string>, private writer?: (key: string, value: string) => void) {}
  get(key: string): string | undefined { return this.readVars[key] }
  set(key: string, value: string) {
    if (this.writer) this.writer(key, value)
    else logger.warn('[pm.environment.set] not available in pre-request')
  }
}

function makePmRequest(config: RequestConfig) {
  return {
    method: config.method,
    url: config.url,
    headers: kvToObject(config.headers),
    body: config.body,
    bodyType: config.bodyType,
  }
}

function makePmResponse(response: ResponseData) {
  let parsedBody: any
  return {
    status: response.status,
    statusText: response.statusText,
    headers: { ...response.headers },
    body: response.body,
    size: response.size,
    timing: response.timing,
    json(): any {
      if (parsedBody === undefined) {
        try { parsedBody = JSON.parse(response.body) } catch { parsedBody = null }
      }
      return parsedBody
    },
    text(): string { return response.body },
  }
}

// ---- Main executor ----
export interface PreRequestInput {
  config: RequestConfig
  envVariables: Record<string, string>
}

export interface PostResponseInput {
  config: RequestConfig
  response: ResponseData
  envVariables: Record<string, string>
  envWriter: (key: string, value: string) => void
}

export interface ScriptExecutionResult {
  /** Runtime variables set during pre-request */
  variables: Record<string, any>
  /** Test results from post-response */
  testResults: ScriptTestResult[]
}

function runScript(script: string, sandbox: Record<string, any>): any {
  const keys = Object.keys(sandbox)
  const values = Object.values(sandbox)
  try {
    const fn = new Function(...keys, `"use strict";\n${script}`)
    fn(...values)
  } catch (e: unknown) {
    const err = e instanceof Error ? e : new Error(String(e))
    // Attach the script with line numbers so the UI can show *where* it failed
    // (the raw JS message alone — e.g. "Missing initializer in const declaration"
    // — gives no clue which line/variable is wrong).
    const numbered = script
      .split('\n')
      .map((line, i) => `${String(i + 1).padStart(3, ' ')} | ${line}`)
      .join('\n')
    err.message = `${err.name}: ${err.message}\n\nScript (line numbers):\n${numbered}`
    logger.error('[ScriptEngine]', err.message)
    throw err
  }
}

/**
 * Execute a pre-request script.
 * The script can read/write pm.variables and read pm.environment / pm.request.
 * Returns runtime variables that should be injected into the request.
 */
export function executePreRequestScript(input: PreRequestInput, script?: string): ScriptExecutionResult {
  const result: ScriptExecutionResult = { variables: {}, testResults: [] }
  if (!script || !script.trim()) return result

  const pmVars = new PmVariables()
  // Pre-request 中通过 pm.environment.set(...) 设置的变量，也应参与本次请求的
  // {{var}} 替换（Postman 行为）。这里把 environment 写入同时回灌到 runtime vars，
  // 使其进入 applyVariables 的变量表。
  const pmEnv = new PmEnvironment(input.envVariables, (k, v) => pmVars.set(k, v))
  const pmReq = makePmRequest(input.config)

  const pm = {
    variables: {
      get: (key: string) => pmVars.get(key),
      set: (key: string, value: any) => pmVars.set(key, value),
      has: (key: string) => pmVars.has(key),
    },
    environment: {
      get: (key: string) => pmEnv.get(key),
      set: (key: string, value: string) => pmEnv.set(key, value),
    },
    request: pmReq,
  }

  runScript(script, { pm })

  result.variables = pmVars.toObject()
  return result
}

/**
 * Execute a post-response script.
 * The script can use pm.response, pm.test(), pm.expect(), and pm.variables / pm.environment.
 */
export function executePostResponseScript(input: PostResponseInput, script?: string): ScriptExecutionResult {
  const result: ScriptExecutionResult = { variables: {}, testResults: [] }
  if (!script || !script.trim()) return result

  const pmVars = new PmVariables()
  const pmEnv = new PmEnvironment(input.envVariables, input.envWriter)
  const pmReq = makePmRequest(input.config)
  const pmRes = makePmResponse(input.response)

  const testResults: ScriptTestResult[] = []

  const pm = {
    variables: {
      get: (key: string) => pmVars.get(key),
      set: (key: string, value: any) => pmVars.set(key, value),
      has: (key: string) => pmVars.has(key),
    },
    environment: {
      get: (key: string) => pmEnv.get(key),
      set: (key: string, value: string) => pmEnv.set(key, value),
    },
    request: pmReq,
    response: pmRes,
    test: (name: string, fn: () => void) => {
      try {
        fn()
        testResults.push({ name, passed: true })
      } catch (e: unknown) {
        testResults.push({ name, passed: false, error: e instanceof Error ? e.message : String(e) })
      }
    },
    expect: createExpect,
  }

  runScript(script, { pm })

  result.testResults = testResults
  result.variables = pmVars.toObject()
  return result
}

/**
 * Apply runtime variables to a request config string value.
 * Replaces {{varName}} patterns.
 */
export function applyVariables(value: string, vars: Record<string, any>): string {
  // 变量名支持字母、数字、下划线和连字符（如 {{App-ID}}）
  return value.replace(/\{\{([\w-]+)\}\}/g, (_, key) => {
    return key in vars ? String(vars[key]) : `{{${key}}}`
  })
}
