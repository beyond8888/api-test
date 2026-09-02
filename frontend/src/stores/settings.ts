import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { createStorageHelper } from '@/utils/storage'
import { DEFAULT_PROXY_TIMEOUT } from '@/utils/constants'

interface SettingsState {
  /** Default request timeout in seconds, used when a request's own timeout is left at 0. */
  defaultTimeout: number
}

const STORAGE_KEY = 'apitest:settings'
const storage = createStorageHelper<SettingsState>(STORAGE_KEY)

const MIN_TIMEOUT = 1
const MAX_TIMEOUT = 60

function load(): SettingsState {
  const saved = storage.load()
  const timeout = saved?.defaultTimeout
  return {
    defaultTimeout:
      typeof timeout === 'number' && timeout >= MIN_TIMEOUT && timeout <= MAX_TIMEOUT
        ? timeout
        : DEFAULT_PROXY_TIMEOUT,
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const initial = load()
  const defaultTimeout = ref<number>(initial.defaultTimeout)

  watch(defaultTimeout, (v) => {
    storage.save({ defaultTimeout: v })
  })

  return { defaultTimeout, MIN_TIMEOUT, MAX_TIMEOUT }
})
