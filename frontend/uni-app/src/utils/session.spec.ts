import { beforeEach, describe, expect, it, vi } from 'vitest'

const storage = new Map<string, any>()
let responder: ((options: any) => void) | undefined

vi.stubGlobal('uni', {
  getStorageSync: (key: string) => storage.get(key),
  setStorageSync: (key: string, value: any) => storage.set(key, value),
  removeStorageSync: (key: string) => storage.delete(key),
  request: (options: any) => responder?.(options)
})

describe('session updates', () => {
  beforeEach(() => {
    vi.resetModules()
    storage.clear()
    responder = undefined
    storage.set('auth_token', 'old-access')
    storage.set('auth_refresh_token', 'old-refresh')
  })

  it('publishes successor credentials after a shared refresh', async () => {
    responder = (options) => {
      expect(options.url).toContain('/user/session/refresh')
      options.success({
        statusCode: 200,
        data: { code: 0, data: { access_token: 'new-access', refresh_token: 'new-refresh' } }
      })
    }

    const session: any = await import('./session')
    const received: string[] = []
    const unsubscribe = session.subscribeToAuthSession((accessToken: string) => received.push(accessToken))

    await session.refreshAuthSession()
    unsubscribe()

    expect(received).toEqual(['new-access'])
  })

  it('does not fail a successful refresh when a session listener throws', async () => {
    responder = (options) => options.success({
      statusCode: 200,
      data: { code: 0, data: { access_token: 'new-access', refresh_token: 'new-refresh' } }
    })

    const session: any = await import('./session')
    session.subscribeToAuthSession(() => { throw new Error('socket cleanup failed') })

    await expect(session.refreshAuthSession()).resolves.toBeUndefined()
    expect(session.authSession.accessToken).toBe('new-access')
  })

  it('notifies listeners immediately when credentials are cleared', async () => {
    const session: any = await import('./session')
    const received: string[] = []
    session.subscribeToAuthSession((accessToken: string) => received.push(accessToken))

    session.clearAuthSession()

    expect(received).toEqual([''])
  })
})
