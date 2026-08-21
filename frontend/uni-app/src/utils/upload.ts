import { goLogin } from '@/utils/auth-navigation'
import { authSession, clearAuthSession, refreshAuthSession } from '@/utils/session'

type AuthUploadOptions = {
  url: string
  filePath: string
  name: string
  formData?: Record<string, any>
  header?: Record<string, string>
}

const parseResponseData = (data: unknown) => {
  if (typeof data !== 'string') return data
  try {
    return JSON.parse(data)
  } catch {
    return data
  }
}

const uploadOnce = (options: AuthUploadOptions, token: string) => new Promise<any>((resolve, reject) => {
  uni.uploadFile({
    ...options,
    header: {
      ...options.header,
      Authorization: `Bearer ${token}`
    },
    success: (res) => {
      const data = parseResponseData(res.data)
      if (res.statusCode >= 200 && res.statusCode < 300) {
        resolve(data)
        return
      }
      reject({ code: res.statusCode, message: (data as any)?.message || `HTTP ${res.statusCode}`, raw: res })
    },
    fail: reject
  })
})

export const authUploadFile = async (options: AuthUploadOptions, hasRetried = false): Promise<any> => {
  const token = authSession.accessToken
  if (!token) {
    goLogin()
    throw { code: 401, message: 'login required', needLogin: true }
  }

  try {
    return await uploadOnce(options, token)
  } catch (error: any) {
    if (error?.code !== 401 || hasRetried) throw error

    if (authSession.accessToken && authSession.accessToken !== token) {
      return authUploadFile(options, true)
    }

    try {
      await refreshAuthSession()
      return authUploadFile(options, true)
    } catch {
      clearAuthSession()
      goLogin()
      throw error
    }
  }
}
