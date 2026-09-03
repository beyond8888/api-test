import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useApiClient } from '@/composables/useApiClient'
import { clearAuthStorage } from '@/utils/storage'
import { useTabsStore } from '@/stores/tabs'
import { useRequestStore } from '@/stores/request'
import { useResponseStore } from '@/stores/response'
import { useHistoryStore } from '@/stores/history'
import { useCollectionsStore } from '@/stores/collections'

const TOKEN_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'
const USER_KEY = 'user_info'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const refreshToken = ref<string | null>(localStorage.getItem(REFRESH_KEY))
  const user = ref<{ id: number; username: string } | null>(
    (() => {
      try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null') } catch { return null }
    })()
  )

  const isAuthenticated = computed(() => !!token.value)

  /**
   * 清空所有用户维度的内存状态（tab 快照、请求/响应、历史记录、集合）。
   * 账号切换（登出 / 登录 / 注册新账号后自动登录）时调用，防止新用户看到
   * 上一个账号残留的请求 tab、响应结果与历史记录。
   */
  function resetUserData(): void {
    const tabsStore = useTabsStore()
    const requestStore = useRequestStore()
    const responseStore = useResponseStore()
    const historyStore = useHistoryStore()
    const collectionsStore = useCollectionsStore()

    tabsStore.tabs = []
    tabsStore.activeId = null
    requestStore.reset()
    responseStore.reset()
    historyStore.resetLocal()
    collectionsStore.collections = []
  }

  async function login(username: string, password: string) {
    const { client } = useApiClient()
    const res = await client.post('/auth/login/', { username, password })
    const data = res.data // { access, refresh }
    token.value = data.access
    refreshToken.value = data.refresh
    localStorage.setItem(TOKEN_KEY, data.access)
    localStorage.setItem(REFRESH_KEY, data.refresh)
    await fetchUser()
    // 登录成功后清掉上一个账号残留的页面状态（注册后自动登录同样生效）
    resetUserData()
  }

  async function register(username: string, password: string) {
    const { client } = useApiClient()
    await client.post('/auth/register/', { username, password })
    // Auto-login after registration
    await login(username, password)
  }

  async function fetchUser() {
    const { client } = useApiClient()
    const res = await client.get('/auth/me/')
    user.value = res.data
    localStorage.setItem(USER_KEY, JSON.stringify(res.data))
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    user.value = null
    clearAuthStorage()
    resetUserData()
  }

  return { token, refreshToken, user, isAuthenticated, login, register, fetchUser, logout, resetUserData }
})
