/** Shared constants used across the app. */

/** Supported HTTP methods for request building. */
export const HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'] as const

export type HttpMethod = (typeof HTTP_METHODS)[number]

/** Naive-UI select options format. */
export const HTTP_METHOD_OPTIONS = HTTP_METHODS.map(v => ({ label: v, value: v }))

/** Default proxy request timeout in seconds (must match backend). */
export const DEFAULT_PROXY_TIMEOUT = 30

/** Default page size for paginated list views. Matches backend StandardResultsSetPagination.page_size. */
export const DEFAULT_PAGE_SIZE = 20

// ── API paths ──────────────────────────────────────────

export const API_SCHEDULE_PROJECTS   = '/schedule/projects/'
export const API_SCHEDULE_ASSIGNMENTS = '/schedule/assignments/'
export const API_SCHEDULE_HOLIDAYS   = '/schedule/holidays/'
export const API_SCHEDULE_ASSIGNEES  = '/schedule/assignees/'
export const API_PROXY               = '/proxy/'
export const API_PARSE_CURL          = '/parse-curl/'
export const API_KAFKA_SEND          = '/kafka/send/'
export const API_ROCKETMQ_SEND       = '/rocketmq/send/'

// ── Time constants (milliseconds) ──────────────────────

export const MS_PER_DAY    = 86_400_000

// ── Calendar ───────────────────────────────────────────

/** Number of cells in a calendar grid (6 rows × 7 columns). */
export const CALENDAR_GRID_CELLS = 42
export const DAYS_PER_WEEK = 7
