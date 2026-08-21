import { reactive } from 'vue'

const BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://127.0.0.1:8001/api/v1'

type SessionCredentials = {
  access_token: string
  refresh_token?: string
  session_id?: number
  access_expires_at?: string
  refresh_expires_at?: string
}

export const authSession = reactive({
  accessToken: uni.getStorageSync('auth_token') || '',
  refreshToken: uni.getStorageSync('auth_refresh_token') || '',
  sessionId: uni.getStorageSync('auth_session_id') || null as number | null,
  accessExpiresAt: uni.getStorageSync('auth_access_expires_at') || '',
  refreshExpiresAt: uni.getStorageSync('auth_refresh_expires_at') || ''
})

const sessionListeners = new Set<(accessToken: string) => void>()
let refreshPromise: Promise<void> | null = null

export const subscribeToAuthSession = (listener: (accessToken: string) => void) => {
  sessionListeners.add(listener)
  return () => sessionListeners.delete(listener)
}

const notifySessionListeners = () => {
  sessionListeners.forEach((listener) => {
    try {
      listener(authSession.accessToken)
    } catch {
      // Auth state has already changed; an observer must not roll it back.
    }
  })
}

export const setAuthSession = (session: SessionCredentials) => {
  const previousAccessToken = authSession.accessToken
  authSession.accessToken = session.access_token || ''
  authSession.refreshToken = session.refresh_token || ''
  uni.setStorageSync('auth_token', authSession.accessToken)

  if (!authSession.refreshToken) {
    clearSessionDetails()
    if (authSession.accessToken !== previousAccessToken) notifySessionListeners()
    return
  }

  authSession.sessionId = session.session_id ?? authSession.sessionId
  authSession.accessExpiresAt = session.access_expires_at || ''
  authSession.refreshExpiresAt = session.refresh_expires_at || ''
  uni.setStorageSync('auth_refresh_token', authSession.refreshToken)
  if (authSession.sessionId !== null) uni.setStorageSync('auth_session_id', authSession.sessionId)
  if (authSession.accessExpiresAt) uni.setStorageSync('auth_access_expires_at', authSession.accessExpiresAt)
  else uni.removeStorageSync('auth_access_expires_at')
  if (authSession.refreshExpiresAt) uni.setStorageSync('auth_refresh_expires_at', authSession.refreshExpiresAt)
  else uni.removeStorageSync('auth_refresh_expires_at')
  if (authSession.accessToken !== previousAccessToken) notifySessionListeners()
}

const clearSessionDetails = () => {
  authSession.refreshToken = ''
  authSession.sessionId = null
  authSession.accessExpiresAt = ''
  authSession.refreshExpiresAt = ''
  uni.removeStorageSync('auth_refresh_token')
  uni.removeStorageSync('auth_session_id')
  uni.removeStorageSync('auth_access_expires_at')
  uni.removeStorageSync('auth_refresh_expires_at')
}

export const clearAuthSession = () => {
  authSession.accessToken = ''
  uni.removeStorageSync('auth_token')
  clearSessionDetails()
  notifySessionListeners()
}

export const refreshAuthSession = (): Promise<void> => {
  if (refreshPromise) return refreshPromise

  const refreshToken = authSession.refreshToken
  if (!refreshToken) return Promise.reject(new Error('refresh token missing'))

  refreshPromise = new Promise<void>((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}/user/session/refresh`,
      method: 'POST',
      data: { refresh_token: refreshToken },
      success: (res) => {
        const payload = res.data as any
        const session = payload?.code === 0 ? payload.data : null
        if (
          res.statusCode >= 200 && res.statusCode < 300 &&
          session?.access_token && session?.refresh_token
        ) {
          setAuthSession(session)
          resolve()
          return
        }
        reject(payload || { code: res.statusCode, message: 'session refresh failed' })
      },
      fail: reject
    })
  }).finally(() => {
    refreshPromise = null
  })
  return refreshPromise
}
