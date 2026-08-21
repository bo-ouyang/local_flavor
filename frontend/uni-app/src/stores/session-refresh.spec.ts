import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/utils/auth', () => ({ goLogin: vi.fn() }))

const storage = new Map<string, any>()
let responders: Array<(options: any) => void> = []
vi.stubGlobal('uni', {
  getStorageSync: (key: string) => storage.get(key),
  setStorageSync: (key: string, value: any) => storage.set(key, value),
  removeStorageSync: (key: string) => storage.delete(key),
  showToast: vi.fn(),
  request: (options: any) => responders.shift()?.(options)
})

describe('session refresh state', () => {
  beforeEach(() => {
    vi.resetModules()
    setActivePinia(createPinia())
    storage.clear()
    responders = []
    storage.set('auth_token', 'expired-access-token')
    storage.set('auth_refresh_token', 'refresh-token')
  })

  it('updates the store access token after a request refreshes the session', async () => {
    responders.push(
      (options) => options.success({ statusCode: 401, data: { message: 'expired' } }),
      (options) => options.success({
        statusCode: 200,
        data: { code: 0, message: 'refreshed', data: {
          access_token: 'new-access-token', refresh_token: 'new-refresh-token'
        } }
      }),
      (options) => options.success({ statusCode: 200, data: { code: 0, message: 'ok', data: {} } })
    )

    const { useUserStore } = await import('./user')
    const request = (await import('@/utils/request')).default
    const store = useUserStore()

    await request.authGet('/user/me')

    expect(store.token).toBe('new-access-token')
  })
})
