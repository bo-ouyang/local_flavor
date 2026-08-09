const REFRESH_URL = '/user/session/refresh'
const LOGOUT_URL = '/user/session/logout'
const requestAccessTokens = new WeakMap()

const makeError = (code, message = 'Request failed', payload) => ({
  code,
  message,
  ...(typeof payload?.request_id === 'string' ? { request_id: payload.request_id } : {})
})

const makeHttpError = (response) => makeError(
  response.statusCode,
  'Request failed',
  response.data
)

const unwrap = (response) => {
  const payload = response.data
  if (response.statusCode < 200 || response.statusCode >= 300) throw makeHttpError(response)
  if (payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'code') && Object.prototype.hasOwnProperty.call(payload, 'message')) {
    if (payload.code === 0) return payload.data
    throw makeError(payload.code, 'Request failed', payload)
  }
  return payload
}

export const createRequestClient = ({ onAuthFailure = () => {}, onSessionRefreshed = (_session) => {}, request, sessions }) => {
  let refreshPromise = null
  let authFailureReported = false

  const accountGeneration = () => sessions.getAccountGeneration?.() ?? 0
  const reportAuthFailure = (expectedGeneration = accountGeneration()) => {
    if (expectedGeneration !== accountGeneration()) return
    if (authFailureReported) return
    authFailureReported = true
    sessions.clear()
    onAuthFailure()
  }

  const resetAuthFailure = () => {
    authFailureReported = false
  }

  const notifySessionRefreshed = (session) => {
    try {
      Promise.resolve(onSessionRefreshed(session)).catch(() => {})
    } catch (_) {
      // Listener failures must not invalidate a successfully rotated session.
    }
  }

  const send = async (options) => {
    const token = options.skipAuth ? '' : sessions.getAccessToken()
    let response
    try {
      response = await request({
        ...options,
        header: {
          ...options.header,
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      })
    } catch (_) {
      throw makeError(0, 'Network request failed')
    }
    try {
      return unwrap(response)
    } catch (error) {
      if (error && typeof error === 'object') requestAccessTokens.set(error, token)
      throw error
    }
  }

  const refresh = () => {
    if (refreshPromise) return refreshPromise
    const refreshToken = sessions.getRefreshToken()
    const refreshGeneration = accountGeneration()
    if (!refreshToken) {
      reportAuthFailure(refreshGeneration)
      return Promise.reject({ code: 401, message: 'session refresh unavailable', needLogin: true })
    }

    refreshPromise = send({
      url: REFRESH_URL,
      method: 'POST',
      data: { refresh_token: refreshToken },
      skipAuth: true,
      noRefresh: true
    }).then((nextSession) => {
      if (refreshGeneration !== accountGeneration()) throw makeError(401, 'Authentication changed')
      sessions.saveSession(nextSession)
      resetAuthFailure()
      notifySessionRefreshed(nextSession)
      return nextSession
    }).catch((error) => {
      reportAuthFailure(refreshGeneration)
      throw error
    }).finally(() => {
      refreshPromise = null
    })
    return refreshPromise
  }

  const perform = async (options) => {
    const requestGeneration = accountGeneration()
    if (options.authMode === 'required' && !sessions.getAccessToken()) {
      reportAuthFailure(requestGeneration)
      throw { code: 401, message: 'login required', needLogin: true }
    }

    try {
      return await send(options)
    } catch (error) {
      if (requestGeneration !== accountGeneration()) throw makeError(401, 'Authentication changed')
      const canRefresh = error?.code === 401 &&
        options.authMode === 'required' &&
        !options.noRefresh &&
        !options.retried &&
        options.url !== REFRESH_URL &&
        options.url !== LOGOUT_URL
      if (canRefresh) {
        const requestAccessToken = error && typeof error === 'object' ? requestAccessTokens.get(error) : ''
        if (requestAccessToken && requestAccessToken !== sessions.getAccessToken()) {
          return perform({ ...options, retried: true })
        }
        await refresh()
        return perform({ ...options, retried: true })
      }
      if (error?.code === 401 && options.authMode === 'required') reportAuthFailure()
      throw error
    }
  }

  const withAuth = (options) => perform({ ...options, authMode: 'required' })
  const requestWith = (method, url, data, options = {}) => perform({ ...options, url, method, data })
  const authRequestWith = (method, url, data, options = {}) => withAuth({ ...options, url, method, data })

  return {
    get: (url, data, options) => requestWith('GET', url, data, options),
    post: (url, data, options) => requestWith('POST', url, data, options),
    put: (url, data, options) => requestWith('PUT', url, data, options),
    patch: (url, data, options) => requestWith('PATCH', url, data, options),
    delete: (url, data, options) => requestWith('DELETE', url, data, options),
    authGet: (url, data, options) => authRequestWith('GET', url, data, options),
    authPost: (url, data, options) => authRequestWith('POST', url, data, options),
    authPut: (url, data, options) => authRequestWith('PUT', url, data, options),
    authPatch: (url, data, options) => authRequestWith('PATCH', url, data, options),
    authDelete: (url, data, options) => authRequestWith('DELETE', url, data, options),
    refresh,
    resetAuthFailure,
    logout: async () => {
      const refreshToken = sessions.getRefreshToken()
      try {
        if (sessions.getAccessToken()) {
          await send({
            url: LOGOUT_URL,
            method: 'POST',
            data: refreshToken ? { refresh_token: refreshToken } : {},
            noRefresh: true
          })
        }
      } catch (_) {
        // Local clearance is deliberately guaranteed even if revocation cannot reach the server.
      } finally {
        sessions.clear()
      }
    }
  }
}
