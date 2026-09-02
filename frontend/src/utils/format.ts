/** Shared formatting utilities. */
import type { KV } from '@/types'

/**
 * Convert a list of key-value rows into a plain object, skipping rows that are
 * disabled or have an empty key. An optional `transform` is applied to each
 * value (e.g. variable substitution) before insertion.
 */
export function kvToObject(
  rows: KV[],
  transform?: (value: string) => string,
): Record<string, string> {
  const result: Record<string, string> = {}
  for (const row of rows) {
    if (!row.enabled || !row.key) continue
    result[row.key] = transform ? transform(row.value) : row.value
  }
  return result
}

/**
 * Format an ISO date string as `YYYY-MM-DD` (local time).
 * Returns '' for empty/invalid input.
 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/**
 * Format an ISO date string as `YYYY-MM-DD HH:mm` (local time).
 * Returns '' for empty/invalid input.
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${hh}:${mm}`
}

/**
 * Format bytes into human-readable size string.
 */
export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/**
 * Generate a UUID v4 string.
 *
 * Uses crypto.randomUUID() when available (HTTPS / localhost),
 * falls back to a polyfill for non-secure HTTP contexts (e.g. LAN IP access).
 */
export function uuid(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  // RFC4122 v4 fallback — works in non-secure contexts (http://192.168.x.x)
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * Copy text to the clipboard.
 *
 * Uses navigator.clipboard.writeText when available (HTTPS / localhost),
 * falls back to a hidden-textarea + document.execCommand('copy') approach
 * for non-secure HTTP contexts (e.g. LAN IP access).
 *
 * Returns true on success, false on failure.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // fall through to legacy approach
    }
  }
  // Legacy fallback for non-secure contexts (http://192.168.x.x)
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'fixed'
    textarea.style.top = '0'
    textarea.style.left = '0'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)
    return ok
  } catch {
    return false
  }
}
