import type { HttpMethod } from '@/utils/constants'

export interface KV {
  id: string;
  key: string;
  value: string;
  desc?: string;
  enabled: boolean;
}

export interface AuthConfig {
  type: 'none' | 'basic' | 'bearer' | 'api-key';
  username?: string;
  password?: string;
  token?: string;
  key?: string;
  value?: string;
  addTo?: 'header' | 'query';
}

export interface MultipartFile {
  id: string;
  field: string;
  name: string;
  type: string;
  size: number;
  /** data URL, e.g. "data:image/png;base64,....". Optional — stripped from
   *  history snapshots to avoid bloating storage. */
  dataUrl?: string;
}

export interface ScriptTestResult {
  name: string;
  passed: boolean;
  error?: string;
}

export type RawFormat = 'json' | 'text' | 'xml' | 'html' | 'javascript';

export interface RequestConfig {
  method: HttpMethod;
  url: string;
  headers: KV[];
  queryParams: KV[];
  body: string;
  /** Body category. `json` is kept only for backward-compat with older
   *  snapshots/saved requests; at runtime it is treated identically to
   *  `raw` + rawFormat='json' (mirrors Postman's "raw → JSON" design). */
  bodyType: 'json' | 'form' | 'multipart' | 'raw' | 'binary' | 'none';
  /** Sub-format for the `raw` body category (Postman-style dropdown). */
  rawFormat: RawFormat;
  multipartFields: KV[];
  multipartFiles: MultipartFile[];
  auth: AuthConfig;
  preRequestScript?: string;
  postResponseScript?: string;
}

export interface ResponseData {
  status: number;
  statusText: string;
  headers: Record<string, string>;
  body: string;
  bodyType: 'json' | 'html' | 'xml' | 'text';
  size: number;
  timing: number;
}

/** Serializable *editable* editor state for a single workspace tab.
 *  Execution results (response, errors, test results) are intentionally excluded
 *  — they live in `responseStore` and are not part of the tab's editable state. */
export interface EditorSnapshot {
  method: RequestConfig['method'];
  url: string;
  headers: KV[];
  queryParams: KV[];
  body: string;
  bodyType: RequestConfig['bodyType'];
  rawFormat: RawFormat;
  multipartFields: KV[];
  multipartFiles: MultipartFile[];
  auth: AuthConfig;
  preRequestScript: string;
  postResponseScript: string;
  customTimeout: number;
}

export interface ParsedFormField {
  field: string;
  value: string;
}

/**
 * Backend CurlParseService wraps the body in a nested structure:
 *   { type, content, form_fields }
 * `content` is the raw body string (for JSON bodies it's a JSON string),
 * `type` mirrors body_type.
 */
export interface ParsedBody {
  type: string;
  content: string;
  form_fields: ParsedFormField[];
}

export interface ParseResult {
  method: string;
  url: string;
  query_params: Record<string, string>;
  headers: Record<string, string>;
  cookies: Record<string, string>;
  body: ParsedBody | null;
  body_type: string;
}

export interface HistoryEntry {
  id: number;
  request: RequestConfig;
  response: ResponseData | null;
  timestamp: string;
}

export interface SavedRequest {
  id: string;
  name: string;
  request: RequestConfig;
  preRequestScript?: string;
  postResponseScript?: string;
}

export interface Folder {
  id: string;
  name: string;
  requests: SavedRequest[];
  folders: Folder[];
  auth: AuthConfig;
}

export interface Collection {
  /** Frontend-local tree id (uuid). Never used for server calls. */
  id: string;
  /** Server primary key (integer) — MUST be used for every API call. */
  dbId?: number;
  name: string;
  description?: string;
  requests: SavedRequest[];
  folders: Folder[];
  createdAt: number;
  preRequestScript?: string;
  auth?: AuthConfig;
}

export interface Environment {
  id: number;
  name: string;
  is_active?: boolean;
  variables: KV[];
  created_at?: string;
  updated_at?: string;
}

// ── Schedule ──

export interface ScheduleProject {
  id: number;
  name: string;
  color: string;
}

export interface ScheduleAssignment {
  id: number;
  title: string;
  start_date: string;
  end_date: string;
  project: number | null;
  role: string;
  assignee: string;
  created_at: string;
}

/** Assignment sub-object embedded in project detail response */
export interface ProjectAssignment {
  id?: number;
  role: string;
  assignee: string;
  start_date: string;
  end_date: string;
}

/** Full project with inline assignments (used in projects list view) */
export interface ProjectDetail extends ScheduleProject {
  description: string;
  assignments: ProjectAssignment[];
  created_at: string;
}

/** Generic paginated list response */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ── API Response ──
// (Unified response envelope handled by apitester.api_response; type is implicit)

/** Business error codes returned in the unified envelope's `code` field.
 *  Mirrors backend apitester.api_response CODE_* constants. */
export enum ErrorCode {
  Success = 0,
  GenericError = -1,
  Unauthorized = -401,
  Forbidden = -403,
  NotFound = -404,
  RateLimited = -429,
  ServerError = -500,
}
