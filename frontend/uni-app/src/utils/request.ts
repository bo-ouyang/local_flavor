import { createAuthSessionStorage } from './auth-session.js'
import { createRequestClient } from './request-client.js'
import { createSessionRefreshEmitter } from './session-refresh-emitter.js'
import { createUploadClient } from './upload-client.js'

const BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://127.0.0.1:8001/django/api/v1'

type RequestOptions = {
  header?: Record<string, string>
  skipToast?: boolean
  [key: string]: any
}

const sessions = createAuthSessionStorage({
  get: (key: string) => uni.getStorageSync(key),
  remove: (key: string) => uni.removeStorageSync(key),
  set: (key: string, value: any) => uni.setStorageSync(key, value)
})
const readAccessToken = () => sessions.getAccessToken()

let authFailureHandler = () => {}
const sessionRefreshEmitter = createSessionRefreshEmitter()

const client = createRequestClient({
  sessions,
  onAuthFailure: () => {
    authFailureHandler()
  },
  onSessionRefreshed: (session: any) => {
    sessionRefreshEmitter.emit(session)
  },
  request: ({ url, method, data, header }: any) => new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + url,
      method,
      data,
      header,
      success: resolve,
      fail: reject
    })
  })
})

const uploadClient = createUploadClient({
  getAccessToken: readAccessToken,
  refresh: () => client.refresh(),
  upload: (options: any) => new Promise((resolve, reject) => {
    uni.uploadFile({
      ...options,
      success: resolve,
      fail: reject
    })
  })
})

const toastForError = (error: any, options?: RequestOptions) => {
  if (options?.skipToast || error?.needLogin) return
  uni.showToast({ title: error?.message || '请求失败', icon: 'none' })
}

const invoke = <T>(operation: () => Promise<T>, options?: RequestOptions) =>
  operation().catch((error) => {
    toastForError(error, options)
    throw error
  })

const withOptions = <T>(operation: (opts?: RequestOptions) => Promise<T>, options?: RequestOptions) =>
  invoke(() => operation(options), options)

export const getSession = () => sessions.getSession()
export const getAccessToken = readAccessToken
export const uploadWithAuth = (options: any) => uploadClient.upload(options)
export const saveLoginResult = (result: any) => {
  const session = sessions.saveLoginResult(result)
  client.resetAuthFailure()
  return session
}
export const clearLocalAuth = () => sessions.clear()
export const setAuthFailureHandler = (handler: () => void) => { authFailureHandler = handler }
export const onSessionRefreshed = (listener: (session: any) => void) => sessionRefreshEmitter.subscribe(listener)

export default {
  get: <T>(url: string, data?: any, options?: RequestOptions) => withOptions((opts) => client.get(url, data, opts), options),
  post: <T>(url: string, data?: any, options?: RequestOptions) => withOptions((opts) => client.post(url, data, opts), options),
  put: <T>(url: string, data?: any, options?: RequestOptions) => withOptions((opts) => client.put(url, data, opts), options),
  patch: <T>(url: string, data?: any, options?: RequestOptions) => withOptions((opts) => client.patch(url, data, opts), options),
  delete: <T>(url: string, data?: any, options?: RequestOptions) => withOptions((opts) => client.delete(url, data, opts), options),
  authGet: <T>(url: string, data?: any, options?: RequestOptions) => withOptions((opts) => client.authGet(url, data, opts), options),
  authPost: <T>(url: string, data?: any, options?: RequestOptions) => withOptions((opts) => client.authPost(url, data, opts), options),
  authPut: <T>(url: string, data?: any, options?: RequestOptions) => withOptions((opts) => client.authPut(url, data, opts), options),
  authPatch: <T>(url: string, data?: any, options?: RequestOptions) => withOptions((opts) => client.authPatch(url, data, opts), options),
  authDelete: <T>(url: string, data?: any, options?: RequestOptions) => withOptions((opts) => client.authDelete(url, data, opts), options),
  logout: () => client.logout()
}
