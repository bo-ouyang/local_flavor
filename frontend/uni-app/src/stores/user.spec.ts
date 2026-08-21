import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const post = vi.fn()
vi.mock('@/utils/request', () => ({ default: { post } }))

const storage = new Map<string, any>()
vi.stubGlobal('uni', {
  getStorageSync: (key: string) => storage.get(key),
  setStorageSync: (key: string, value: any) => storage.set(key, value),
  removeStorageSync: (key: string) => storage.delete(key)
})

describe('user session store', () => {
  beforeEach(() => {
    vi.resetModules()
    setActivePinia(createPinia())
    storage.clear()
    post.mockReset()
  })

  it('uses the opaque session returned by login and persists both credentials', async () => {
    const { useUserStore } = await import('./user')
    const store = useUserStore()

    store.applyLoginResult({
      access_token: 'legacy-token',
      session: { access_token: 'session-access', refresh_token: 'session-refresh', session_id: 9 },
      user: { id: 1, nickname: 'Tester' }
    })

    expect(store.token).toBe('session-access')
    expect(storage.get('auth_token')).toBe('session-access')
    expect(storage.get('auth_refresh_token')).toBe('session-refresh')
    expect(storage.get('auth_session_id')).toBe(9)
  })

  it('falls back to a legacy login token without retaining a prior opaque session', async () => {
    const { useUserStore } = await import('./user')
    const store = useUserStore()
    storage.set('auth_refresh_token', 'old-refresh')
    storage.set('auth_session_id', 9)

    store.applyLoginResult({ access_token: 'legacy-token' })

    expect(store.token).toBe('legacy-token')
    expect(storage.get('auth_refresh_token')).toBeUndefined()
    expect(storage.get('auth_session_id')).toBeUndefined()
  })

  it('revokes the server session before clearing local credentials', async () => {
    const { useUserStore } = await import('./user')
    const store = useUserStore()
    store.applyLoginResult({
      access_token: 'session-access'
    })
    post.mockResolvedValue({ session_id: 9 })

    await store.logout()

    expect(post).toHaveBeenCalledWith('/user/session/logout', undefined, {
      authMode: 'required',
      skipToast: true
    })
    expect(storage.get('auth_token')).toBeUndefined()
    expect(storage.get('auth_refresh_token')).toBeUndefined()
  })
})
