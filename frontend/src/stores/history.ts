import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  fetchHistory, createHistoryEntry, deleteHistoryEntry, clearHistory,
  type HistoryEntryData,
} from '@/services/data'
import { logger } from '@/utils/logger'
import type { RequestConfig, ResponseData } from '@/types'

export type HistoryEntry = HistoryEntryData

const PAGE_SIZE = 50

export const useHistoryStore = defineStore('history', () => {
  const entries = ref<HistoryEntry[]>([])
  const loading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const hasMore = computed(() => entries.value.length < total.value)

  async function init() {
    loading.value = true
    try {
      page.value = 1
      const { results, count } = await fetchHistory(1, PAGE_SIZE)
      entries.value = results
      total.value = count
    } catch (e) {
      logger.error('[history] Failed to load:', e)
    } finally {
      loading.value = false
    }
  }

  async function loadMore() {
    if (loading.value || !hasMore.value) return
    loading.value = true
    try {
      const next = page.value + 1
      const { results } = await fetchHistory(next, PAGE_SIZE)
      entries.value.push(...results)
      page.value = next
    } catch (e) {
      logger.error('[history] Failed to load more:', e)
    } finally {
      loading.value = false
    }
  }

  async function addEntry(entry: { request: RequestConfig; response?: ResponseData | null }) {
    try {
      const created = await createHistoryEntry(entry.request, entry.response ?? null)
      entries.value.unshift(created)
      total.value += 1
    } catch (e) {
      logger.error('[history] Failed to add entry:', e)
    }
  }

  async function deleteEntry(id: number) {
    try {
      await deleteHistoryEntry(id)
      entries.value = entries.value.filter((e) => e.id !== id)
      total.value = Math.max(0, total.value - 1)
    } catch (e) {
      logger.error('[history] Failed to delete entry:', e)
    }
  }

  async function deleteEntries(ids: number[]) {
    try {
      await Promise.all(ids.map((id) => deleteHistoryEntry(id)))
      entries.value = entries.value.filter((e) => !ids.includes(e.id))
      total.value = Math.max(0, total.value - ids.length)
    } catch (e) {
      logger.error('[history] Failed to delete entries:', e)
    }
  }

  async function clearHistoryStore() {
    try {
      await clearHistory()
      entries.value = []
      total.value = 0
      page.value = 1
    } catch (e) {
      logger.error('[history] Failed to clear:', e)
    }
  }

  /** 仅清空内存中的历史记录（不调后端），供账号切换时避免旧账号数据残留 */
  function resetLocal() {
    entries.value = []
    total.value = 0
    page.value = 1
  }

  return {
    entries,
    loading,
    hasMore,
    total,
    init,
    loadMore,
    addEntry,
    deleteEntry,
    deleteEntries,
    clearHistory: clearHistoryStore,
    resetLocal,
  }
})
