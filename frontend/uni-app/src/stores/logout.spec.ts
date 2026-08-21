import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/utils/auth', () => ({ goLogin: vi.fn() }))

const storage = new Map<string, any>()
const calls: any[] = []
let responders: Array<(options: any) => void> = []

vi.stubGlobal('uni', {
  getStorageSync: (key: string) => storage.get(key),
  setStorageSync: (key: string, value: any) => storage.set(key, value),
  removeStorageSync: (key: string) => storage.delete(key),
  showToast: vi.fn(),
  request: (options: any) => {
    calls.push(options)
    responders.shift()?.(options)
  }
})

describe('logout', () => {
  beforeEach(() => {
    vi.resetModules()
    setActivePinia(createPinia())
    storage.clear()
    calls.length = 0
    responders = []
  })

  it('lets the authenticated logout request refresh once and then revoke the session', async () => {
    responders.push(
      (options) => {
        expect(options.url).toContain('/user/session/logout')
        expect(options.header.Authorization).toBe('Bearer expired-access')
        options.success({ statusCode: 401, data: { message: 'expired' } })
      },
      (options) => {
        expect(options.url).toContain('/user/session/refresh')
        expect(options.data).toEqual({ refresh_token: 'refresh-token' })
        options.success({
          statusCode: 200,
          data: { code: 0, data: { access_token: 'successor-access', refresh_token: 'successor-refresh' } }
        })
      },
      (options) => {
        expect(options.url).toContain('/user/session/logout')
        expect(options.header.Authorization).toBe('Bearer successor-access')
        options.success({ statusCode: 200, data: { code: 0, data: { session_id: 9 } } })
      }
    )

    const { useUserStore } = await import('./user')
    const store = useUserStore()
    store.applyLoginResult({
      session: { access_token: 'expired-access', refresh_token: 'refresh-token', session_id: 9 }
    })

    await store.logout()

    expect(calls).toHaveLength(3)
    expect(storage.get('auth_token')).toBeUndefined()
    expect(storage.get('auth_refresh_token')).toBeUndefined()
  })
})
