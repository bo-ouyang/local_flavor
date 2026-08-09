export const createChatVisibilityGate = () => {
  let visible = true

  return {
    hide: () => { visible = false },
    show: () => { visible = true },
    runWhenVisible: (operation) => {
      if (!visible) return false
      operation()
      return true
    }
  }
}
