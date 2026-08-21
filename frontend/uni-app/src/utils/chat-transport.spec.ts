import { describe, expect, it, vi } from 'vitest'
import { createChatSocketLifecycle, isChatWebSocketSupported, subscribeChatSessionReconnect } from './chat-transport'

describe('chat transport platform policy', () => {
  it('disables websocket transport on H5 because headers cannot authenticate the handshake', () => {
    expect(isChatWebSocketSupported('h5')).toBe(false)
  })

  it('keeps websocket transport available on mini-program and native platforms', () => {
    expect(isChatWebSocketSupported('mp-weixin')).toBe(true)
    expect(isChatWebSocketSupported('app')).toBe(true)
  })

  it('reconnects an active native chat socket when the session publishes successor credentials', () => {
    let listener: ((accessToken: string) => void) | undefined
    const reconnect = vi.fn()
    const unsubscribe = subscribeChatSessionReconnect(
      (nextListener) => {
        listener = nextListener
        return vi.fn()
      },
      () => true,
      reconnect
    )

    listener?.('successor-access')
    unsubscribe()

    expect(reconnect).toHaveBeenCalledTimes(1)
  })

  it('retries websocket after a session update even while polling fallback is active', () => {
    let listener: ((accessToken: string) => void) | undefined
    const reconnect = vi.fn()
    subscribeChatSessionReconnect(
      (nextListener) => {
        listener = nextListener
        return vi.fn()
      },
      () => true,
      reconnect
    )

    listener?.('successor-access')

    expect(reconnect).toHaveBeenCalledTimes(1)
  })

  it('closes the active socket when the auth session is cleared', () => {
    let listener: ((accessToken: string) => void) | undefined
    const close = vi.fn()
    subscribeChatSessionReconnect(
      (nextListener) => {
        listener = nextListener
        return vi.fn()
      },
      () => true,
      vi.fn(),
      close
    )

    listener?.('')

    expect(close).toHaveBeenCalledTimes(1)
  })

  it('ignores a stale socket close after reconnecting', () => {
    const tasks: any[] = []
    const status = vi.fn()
    const lifecycle = createChatSocketLifecycle({
      canConnect: () => true,
      createSocket: () => {
        const task: any = {
          close: vi.fn(),
          onOpen: (callback: () => void) => { task.open = callback },
          onClose: (callback: () => void) => { task.closeHandler = callback },
          onError: (callback: (error: any) => void) => { task.error = callback },
          onMessage: (callback: (message: any) => void) => { task.message = callback }
        }
        tasks.push(task)
        return task
      },
      setStatus: status
    })

    lifecycle.connect()
    const oldTask = tasks[0]
    lifecycle.reconnect()
    const newTask = tasks[1]
    newTask.open()
    oldTask.closeHandler()

    expect(status).toHaveBeenLastCalledWith({ connected: true, connecting: false, unavailable: false })
    expect(lifecycle.isConnected()).toBe(true)
  })
})
