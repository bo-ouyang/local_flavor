import { goLogin } from '@/utils/auth'

const BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://127.0.0.1:8001/api/v1'

type ApiEnvelope<T> = {
  code: number
  message: string
  data: T
  request_id?: string
  errors?: any
}

type AuthMode = 'none' | 'required'

type RequestExtOptions = UniApp.RequestOptions & {
  authMode?: AuthMode
  skipToast?: boolean
}

const clearAuth = () => {
  uni.removeStorageSync('auth_token')
  uni.removeStorageSync('user_info')
}

const request = <T>(options: RequestExtOptions): Promise<T> => {
  const authMode = options.authMode || 'none'
  const token = uni.getStorageSync('auth_token')

  if (authMode === 'required' && !token) {
    goLogin()
    return Promise.reject({ code: 401, message: 'login required', needLogin: true })
  }

  return new Promise((resolve, reject) => {
    uni.request({
      ...options,
      url: BASE_URL + options.url,
      header: {
        ...options.header,
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      success: (res) => {
        const payload = res.data as any

        if (res.statusCode >= 200 && res.statusCode < 300) {
          if (
            payload &&
            typeof payload === 'object' &&
            Object.prototype.hasOwnProperty.call(payload, 'code') &&
            Object.prototype.hasOwnProperty.call(payload, 'message')
          ) {
            const wrapped = payload as ApiEnvelope<T>
            if (wrapped.code === 0) {
              resolve(wrapped.data as T)
              return
            }
            if (!options.skipToast) {
              uni.showToast({ title: wrapped.message || '请求失败', icon: 'none' })
            }
            reject(wrapped)
            return
          }
          resolve(payload as T)
          return
        }

        const message = payload?.message || `HTTP ${res.statusCode}`
        if (res.statusCode === 401 || res.statusCode === 403) {
          clearAuth()
          if (authMode === 'required') {
            goLogin()
          }
        }
        if (!options.skipToast) {
          uni.showToast({ title: message, icon: 'none' })
        }
        reject({ code: res.statusCode, message, raw: res })
      },
      fail: (err) => {
        if (!options.skipToast) {
          uni.showToast({ title: '网络异常', icon: 'none' })
        }
        reject(err)
      }
    })
  })
}

const base = {
  get: <T>(url: string, data?: any, opts?: Partial<RequestExtOptions>) =>
    request<T>({ url, method: 'GET', data, ...(opts || {}) }),
  post: <T>(url: string, data?: any, opts?: Partial<RequestExtOptions>) =>
    request<T>({ url, method: 'POST', data, ...(opts || {}) }),
  put: <T>(url: string, data?: any, opts?: Partial<RequestExtOptions>) =>
    request<T>({ url, method: 'PUT', data, ...(opts || {}) }),
  patch: <T>(url: string, data?: any, opts?: Partial<RequestExtOptions>) =>
    request<T>({ url, method: 'PATCH' as any, data, ...(opts || {}) }),
  delete: <T>(url: string, data?: any, opts?: Partial<RequestExtOptions>) =>
    request<T>({ url, method: 'DELETE', data, ...(opts || {}) })
}

export default {
  ...base,
  authGet: <T>(url: string, data?: any, opts?: Partial<RequestExtOptions>) =>
    base.get<T>(url, data, { ...(opts || {}), authMode: 'required' }),
  authPost: <T>(url: string, data?: any, opts?: Partial<RequestExtOptions>) =>
    base.post<T>(url, data, { ...(opts || {}), authMode: 'required' }),
  authPut: <T>(url: string, data?: any, opts?: Partial<RequestExtOptions>) =>
    base.put<T>(url, data, { ...(opts || {}), authMode: 'required' }),
  authPatch: <T>(url: string, data?: any, opts?: Partial<RequestExtOptions>) =>
    base.patch<T>(url, data, { ...(opts || {}), authMode: 'required' }),
  authDelete: <T>(url: string, data?: any, opts?: Partial<RequestExtOptions>) =>
    base.delete<T>(url, data, { ...(opts || {}), authMode: 'required' })
}
