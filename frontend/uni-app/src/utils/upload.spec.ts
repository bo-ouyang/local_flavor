import { beforeEach, describe, expect, it, vi } from 'vitest'

const storage = new Map<string, any>()
const uploadCalls: any[] = []
let uploadResponders: Array<(options: any) => void> = []
let requestResponders: Array<(options: any) => void> = []

vi.stubGlobal('uni', {
  getStorageSync: (key: string) => storage.get(key),
  setStorageSync: (key: string, value: any) => storage.set(key, value),
  removeStorageSync: (key: string) => storage.delete(key),
  request: (options: any) => requestResponders.shift()?.(options),
  uploadFile: (options: any) => {
    uploadCalls.push(options)
    uploadResponders.shift()?.(options)
  }
})

describe('authenticated uploads', () => {
  beforeEach(() => {
    vi.resetModules()
    storage.clear()
    uploadCalls.length = 0
    uploadResponders = []
    requestResponders = []
    storage.set('auth_token', 'expired-access-token')
    storage.set('auth_refresh_token', 'refresh-token')
  })

  it('refreshes once after a 401 then retries the upload with the successor access token', async () => {
    uploadResponders.push(
      (options) => {
        expect(options.header.Authorization).toBe('Bearer expired-access-token')
        expect(options.url).not.toContain('token=')
        options.success({ statusCode: 401, data: JSON.stringify({ message: 'expired' }) })
      },
      (options) => {
        expect(options.header.Authorization).toBe('Bearer successor-access-token')
        options.success({ statusCode: 200, data: JSON.stringify({ code: 0, data: { url: '/uploads/photo.jpg' } }) })
      }
    )
    requestResponders.push((options) => {
      expect(options.url).toContain('/user/session/refresh')
      expect(options.data).toEqual({ refresh_token: 'refresh-token' })
      options.success({
        statusCode: 200,
        data: {
          code: 0,
          data: { access_token: 'successor-access-token', refresh_token: 'successor-refresh-token' }
        }
      })
    })

    const { authUploadFile } = await import('./upload')
    await expect(authUploadFile({
      url: 'http://127.0.0.1:8001/api/v1/upload/',
      filePath: '/tmp/photo.jpg',
      name: 'file'
    })).resolves.toEqual({ code: 0, data: { url: '/uploads/photo.jpg' } })

    expect(uploadCalls).toHaveLength(2)
  })
})
