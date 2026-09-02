import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useApiClient } from '@/composables/useApiClient'
import { clearAuthStorage } from '@/utils/storage'

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

  async function login(username: string, password: string) {
    const { client } = useApiClient()
    const res = await client.post('/auth/login/', { username, password })
    const data = res.data // { access, refresh }
    token.value = data.access
    refreshToken.value = data.refresh
    localStorage.setItem(TOKEN_KEY, data.access)
    localStorage.setItem(REFRESH_KEY, data.refresh)
    await fetchUser()
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
  }

  return { token, refreshToken, user, isAuthenticated, login, register, fetchUser, logout }
})
