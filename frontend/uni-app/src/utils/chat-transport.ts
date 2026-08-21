export const isChatWebSocketSupported = (platform: string) => platform !== 'h5'

let currentPlatform = 'native'
// #ifdef H5
currentPlatform = 'h5'
// #endif

export const canUseChatWebSocket = () => isChatWebSocketSupported(currentPlatform)

type SessionSubscriber = (listener: (accessToken: string) => void) => () => void

type SocketTaskLike = {
  close: (options?: any) => void
  onOpen: (listener: () => void) => void
  onClose: (listener: () => void) => void
  onError: (listener: (error: any) => void) => void
  onMessage?: (listener: (message: any) => void) => void
}

type SocketStatus = {
  connected: boolean
  connecting: boolean
  unavailable: boolean
}

type ChatSocketLifecycleOptions = {
  canConnect: () => boolean
  createSocket: () => SocketTaskLike
  setStatus: (status: SocketStatus) => void
  onMessage?: (message: any) => void
  onError?: (error: any) => void
}

export const createChatSocketLifecycle = ({
  canConnect,
  createSocket,
  setStatus,
  onMessage,
  onError
}: ChatSocketLifecycleOptions) => {
  let task: SocketTaskLike | null = null
  let generation = 0
  let connected = false

  const isCurrent = (candidate: number) => candidate === generation
  const update = (status: SocketStatus) => {
    connected = status.connected
    setStatus(status)
  }

  const close = () => {
    const activeTask = task
    task = null
    generation += 1
    update({ connected: false, connecting: false, unavailable: false })
    try {
      activeTask?.close({})
    } catch (error) {
      onError?.(error)
    }
  }

  const connect = () => {
    if (!canConnect() || task) return false

    const taskGeneration = ++generation
    update({ connected: false, connecting: true, unavailable: false })
    try {
      const nextTask = createSocket()
      task = nextTask
      nextTask.onOpen(() => {
        if (!isCurrent(taskGeneration)) return
        update({ connected: true, connecting: false, unavailable: false })
      })
      nextTask.onClose(() => {
        if (!isCurrent(taskGeneration)) return
        task = null
        update({ connected: false, connecting: false, unavailable: true })
      })
      nextTask.onError((error) => {
        if (!isCurrent(taskGeneration)) return
        task = null
        update({ connected: false, connecting: false, unavailable: true })
        onError?.(error)
      })
      nextTask.onMessage?.((message) => {
        if (isCurrent(taskGeneration)) onMessage?.(message)
      })
      return true
    } catch (error) {
      if (isCurrent(taskGeneration)) update({ connected: false, connecting: false, unavailable: true })
      onError?.(error)
      return false
    }
  }

  return {
    connect,
    close,
    reconnect: () => {
      close()
      return connect()
    },
    isConnected: () => connected
  }
}

export const subscribeChatSessionReconnect = (
  subscribe: SessionSubscriber,
  canReconnect: () => boolean,
  reconnect: () => void,
  close?: () => void
) => subscribe((accessToken) => {
  if (!accessToken) {
    close?.()
    return
  }
  if (canReconnect()) reconnect()
})
