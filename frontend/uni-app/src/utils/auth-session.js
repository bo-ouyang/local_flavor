export const AUTH_SESSION_STORAGE_KEY = 'auth_session'
export const LEGACY_AUTH_TOKEN_STORAGE_KEY = 'auth_token'
const USER_INFO_STORAGE_KEY = 'user_info'

const isSession = (value) => Boolean(
  value &&
  typeof value === 'object' &&
  typeof value.access_token === 'string' &&
  value.access_token &&
  typeof value.refresh_token === 'string' &&
  value.refresh_token
)

const hasOwn = (value, key) => Object.prototype.hasOwnProperty.call(value, key)

export const createAuthSessionStorage = (storage) => {
  let accountGeneration = 0
  const getSession = () => {
    const value = storage.get(AUTH_SESSION_STORAGE_KEY)
    return isSession(value) ? value : null
  }

  const getAccessToken = () => {
    const session = getSession()
    if (session) return session.access_token
    const legacy = storage.get(LEGACY_AUTH_TOKEN_STORAGE_KEY)
    return typeof legacy === 'string' ? legacy : ''
  }

  const getRefreshToken = () => getSession()?.refresh_token || ''

  const saveSession = (session) => {
    if (!isSession(session)) throw new Error('invalid session credentials')
    storage.set(AUTH_SESSION_STORAGE_KEY, session)
    storage.remove(LEGACY_AUTH_TOKEN_STORAGE_KEY)
    return session
  }

  const saveLoginResult = (result) => {
    if (result && hasOwn(result, 'session')) {
      if (!isSession(result.session)) {
        clear()
        throw new Error('invalid session credentials')
      }
      const saved = saveSession(result.session)
      accountGeneration += 1
      return saved
    }

    const legacy = result?.access_token || result?.token
    if (typeof legacy !== 'string' || !legacy) {
      throw new Error('login response did not include usable credentials')
    }
    storage.remove(AUTH_SESSION_STORAGE_KEY)
    storage.set(LEGACY_AUTH_TOKEN_STORAGE_KEY, legacy)
    accountGeneration += 1
    return null
  }

  const clear = () => {
    accountGeneration += 1
    storage.remove(AUTH_SESSION_STORAGE_KEY)
    storage.remove(LEGACY_AUTH_TOKEN_STORAGE_KEY)
    storage.remove(USER_INFO_STORAGE_KEY)
  }

  return { clear, getAccessToken, getAccountGeneration: () => accountGeneration, getRefreshToken, getSession, saveLoginResult, saveSession }
}
