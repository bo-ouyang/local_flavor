/**
 * @typedef {{ id: number, current?: boolean, device_label?: string, last_seen_at?: string, created_at?: string, revoked_at?: string | null }} DeviceSession
 */

export const createSessionManager = ({ onCurrentRevoked = () => {}, request }) => {
  /** @type {{ actionBusy: boolean, error: string, loading: boolean, sessions: DeviceSession[] }} */
  const state = {
    actionBusy: false,
    error: '',
    loading: false,
    sessions: []
  }

  const load = async () => {
    state.loading = true
    state.error = ''
    try {
      const sessions = await request.authGet('/user/sessions')
      state.sessions = Array.isArray(sessions) ? sessions.filter((session) => !session.revoked_at) : []
      return state.sessions
    } catch (error) {
      state.error = error?.message || '设备会话加载失败'
      state.sessions = []
      throw error
    } finally {
      state.loading = false
    }
  }

  const revoke = async (sessionId) => {
    if (state.actionBusy) return
    state.actionBusy = true
    const target = state.sessions.find((session) => session.id === sessionId)
    try {
      await request.authPost(`/user/sessions/${sessionId}/revoke`)
      if (target?.current) {
        state.sessions = []
        onCurrentRevoked()
        return
      }
      await load()
    } finally {
      state.actionBusy = false
    }
  }

  const revokeOthers = async () => {
    if (state.actionBusy) return
    state.actionBusy = true
    try {
      await request.authPost('/user/sessions/revoke-others')
      await load()
    } finally {
      state.actionBusy = false
    }
  }

  return { load, revoke, revokeOthers, state }
}
