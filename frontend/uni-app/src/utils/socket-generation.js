export const createSocketGenerationGuard = () => {
  let activeTask = null

  const activate = (task) => {
    activeTask = task
  }

  const current = () => activeTask
  const isCurrent = (task) => activeTask === task
  const release = (task) => {
    if (!isCurrent(task)) return false
    activeTask = null
    return true
  }

  return { activate, current, isCurrent, release }
}
