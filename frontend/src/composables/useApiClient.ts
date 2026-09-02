import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { clearAuthStorage } from '@/utils/storage'

const TOKEN_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

let _client: AxiosInstance | null = null
let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

function forceLogout() {
  clearAuthStorage()
  if (!window.location.pathname.startsWith('/login')) {
    window.location.href = '/login'
  }
}

async function doRefresh(): Promise<string> {
  const refreshToken = localStorage.getItem(REFRESH_KEY)
  if (!refreshToken) {
    throw new Error('No refresh token available')
  }

  const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  const res = await axios.post(`${baseURL}/auth/refresh/`, {
    refresh: refreshToken,
  })

  const newAccessToken: string = res.data?.data?.access ?? res.data?.access
  if (!newAccessToken) {
    throw new Error('Refresh response did not contain access token')
  }

  localStorage.setItem(TOKEN_KEY, newAccessToken)
  return newAccessToken
}

function createClient(): AxiosInstance {
  const instance = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
    headers: { 'Content-Type': 'application/json' },
  })

  // ── Request interceptor: attach JWT token ──
  instance.interceptors.request.use((config) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  // ── Response interceptor: unwrap envelope + handle 401 ──
  instance.interceptors.response.use(
    (response) => {
      const data = response.data
      if (data && typeof data === 'object' && !Array.isArray(data) && 'code' in data) {
        if (data.code === 0) {
          response.data = data.data
        } else {
          const msg = data.message || 'Unknown error'
          return Promise.reject(new Error(msg))
        }
      }
      return response
    },
    async (error: AxiosError) => {
      const originalRequest = error.config as RetryableRequestConfig | undefined

      // Never auto-refresh on the auth endpoints themselves (login/refresh),
      // otherwise a failed login would be misread as an expired token and
      // trigger forceLogout, hiding the real "wrong password" error.
      const reqUrl = (originalRequest?.url as string) || ''
      const isAuthPath =
        reqUrl.includes('/auth/login') || reqUrl.includes('/auth/refresh')

      // 401 → try to refresh the access token once
      if (
        error?.response?.status === 401
        && originalRequest
        && !originalRequest._retry
        && !isAuthPath
      ) {
        if (isRefreshing) {
          return new Promise((resolve) => {
            subscribeTokenRefresh((token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`
              resolve(instance(originalRequest))
            })
          })
        }

        originalRequest._retry = true
        isRefreshing = true

        try {
          const newToken = await doRefresh()
          onRefreshed(newToken)
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return instance(originalRequest)
        } catch (refreshError) {
          forceLogout()
          return Promise.reject(refreshError)
        } finally {
          isRefreshing = false
        }
      }

      // Any other 401 (or refresh failed) → logout, except on auth endpoints
      if (error?.response?.status === 401 && !isAuthPath) {
        forceLogout()
      }

      // Log to console — UI feedback handled by calling component
      const respData = error?.response?.data as Record<string, unknown> | undefined
      if (respData && typeof respData === 'object' && 'message' in respData) {
        console.error('[API]', respData.message)
      } else if (error.message && error.message !== 'canceled') {
        console.error('[API]', error.message)
      }
      return Promise.reject(error)
    },
  )

  return instance
}

export function useApiClient() {
  if (!_client) {
    _client = createClient()
  }
  return { client: _client }
}
