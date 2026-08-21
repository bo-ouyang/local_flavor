import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const goLogin = vi.fn()
vi.mock('@/utils/auth-navigation', () => ({ goLogin }))

const storage = new Map<string, any>()
const requestCalls: any[] = []
let responders: Array<(options: any) => void> = []

vi.stubGlobal('uni', {
  getStorageSync: (key: string) => storage.get(key),
  setStorageSync: (key: string, value: any) => storage.set(key, value),
  removeStorageSync: (key: string) => storage.delete(key),
  showToast: vi.fn(),
  request: (options: any) => {
    requestCalls.push(options)
    responders.shift()?.(options)
  }
})

describe('authenticated requests', () => {
  beforeEach(() => {
    vi.resetModules()
    setActivePinia(createPinia())
    storage.clear()
    requestCalls.length = 0
    responders = []
    goLogin.mockReset()
    storage.set('auth_token', 'expired-access-token')
    storage.set('auth_refresh_token', 'refresh-token')
  })

  it('refreshes credentials once after a 401 and retries the original request', async () => {
    responders.push(
      (options) => options.success({ statusCode: 401, data: { message: 'expired' } }),
      (options) => {
        expect(options.url).toContain('/user/session/refresh')
        expect(options.data).toEqual({ refresh_token: 'refresh-token' })
        options.success({
          statusCode: 200,
          data: { code: 0, message: 'session refreshed', data: {
            access_token: 'new-access-token',
            refresh_token: 'new-refresh-token'
          } }
        })
      },
      (options) => {
        expect(options.header.Authorization).toBe('Bearer new-access-token')
        options.success({ statusCode: 200, data: { code: 0, message: 'ok', data: { id: 1 } } })
      }
    )

    const request = (await import('./request')).default
    await expect(request.authGet('/user/me')).resolves.toEqual({ id: 1 })

    expect(requestCalls).toHaveLength(3)
    expect(storage.get('auth_token')).toBe('new-access-token')
    expect(storage.get('auth_refresh_token')).toBe('new-refresh-token')
    expect(goLogin).not.toHaveBeenCalled()
  })

  it('retries a late 401 with credentials refreshed by another request without refreshing again', async () => {
    const { setAuthSession } = await import('./session')
    responders.push(
      (options) => {
        expect(options.header.Authorization).toBe('Bearer expired-access-token')
        setAuthSession({ access_token: 'successor-access-token', refresh_token: 'successor-refresh-token' })
        options.success({ statusCode: 401, data: { message: 'expired' } })
      },
      (options) => {
        expect(options.url).toContain('/user/me')
        expect(options.header.Authorization).toBe('Bearer successor-access-token')
        options.success({ statusCode: 200, data: { code: 0, message: 'ok', data: { id: 1 } } })
      }
    )

    const request = (await import('./request')).default
    await expect(request.authGet('/user/me')).resolves.toEqual({ id: 1 })

    expect(requestCalls).toHaveLength(2)
    expect(requestCalls.some((call) => call.url.includes('/user/session/refresh'))).toBe(false)
  })

  it('does not redirect when an explicit no-refresh request receives a 401', async () => {
    responders.push((options) => options.success({ statusCode: 401, data: { message: 'expired' } }))
    const request = (await import('./request')).default

    await expect(request.authPost('/user/session/logout', undefined, {
      skipAuthRefresh: true,
      skipToast: true
    })).rejects.toMatchObject({ code: 401 })

    expect(goLogin).not.toHaveBeenCalled()
  })

  it('clears in-memory profile coordinates when session refresh fails before another user logs in', async () => {
    responders.push(
      (options) => options.success({ statusCode: 401, data: { message: 'expired' } }),
      (options) => options.success({ statusCode: 401, data: { message: 'refresh expired' } })
    )
    const { useUserStore } = await import('@/stores/user')
    const store = useUserStore()
    store.setUserInfo({ id: 1, nickname: 'First user', latitude: 22.3, longitude: 114.2, city: 'Hong Kong' })
    const request = (await import('./request')).default

    await expect(request.authGet('/user/me')).rejects.toMatchObject({ code: 401 })

    expect(store.userInfo).toMatchObject({ id: 0, nickname: 'Guest', latitude: null, longitude: null, city: '' })
  })
})
