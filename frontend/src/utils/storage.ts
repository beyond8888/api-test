/** Generic localStorage wrapper with JSON serialization and error handling. */

export interface StorageHelper<T> {
  load: () => T | null
  save: (value: T) => void
  remove: () => void
}

/**
 * Create a typed localStorage helper for a given key.
 * @param key  localStorage key
 * @param migrate  optional migration function applied to loaded data
 */
export function createStorageHelper<T>(key: string, migrate?: (data: T) => T): StorageHelper<T> {
  return {
    load(): T | null {
      try {
        const stored = localStorage.getItem(key)
        if (!stored) return null
        const parsed = JSON.parse(stored) as T
        return migrate ? migrate(parsed) : parsed
      } catch {
        return null
      }
    },

    save(value: T): void {
      try {
        localStorage.setItem(key, JSON.stringify(value))
      } catch (e) {
        // Storage full (QuotaExceededError) or unavailable (private mode)
        console.warn(`[storage] Failed to save "${key}":`, e instanceof Error ? e.message : e)
      }
    },

    remove(): void {
      try {
        localStorage.removeItem(key)
      } catch {
        // ignore
      }
    },
  }
}

const AUTH_KEYS = ['access_token', 'refresh_token', 'user_info']

/** Remove all auth-related entries from localStorage (used by logout paths). */
export function clearAuthStorage(): void {
  AUTH_KEYS.forEach((key) => localStorage.removeItem(key))
}
