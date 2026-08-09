export const createSessionRefreshEmitter = () => {
  const listeners = new Set()

  return {
    emit(session) {
      listeners.forEach((listener) => {
        try {
          Promise.resolve(listener(session)).catch(() => {})
        } catch (_) {
          // A subscriber must not stop token rotation or its peers.
        }
      })
    },
    subscribe(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    }
  }
}
