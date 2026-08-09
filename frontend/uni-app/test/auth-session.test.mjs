import assert from 'node:assert/strict'
import test from 'node:test'

import {
  AUTH_SESSION_STORAGE_KEY,
  LEGACY_AUTH_TOKEN_STORAGE_KEY,
  createAuthSessionStorage
} from '../src/utils/auth-session.js'

const createStorage = (initial = {}) => {
  const values = new Map(Object.entries(initial))
  return {
    get: (key) => values.get(key),
    remove: (key) => values.delete(key),
    set: (key, value) => values.set(key, value),
    values
  }
}

test('prefers the nested opaque session from a login response over legacy fields', () => {
  const storage = createStorage()
  const sessions = createAuthSessionStorage(storage)

  const session = sessions.saveLoginResult({
    access_token: 'legacy-access',
    token: 'legacy-token',
    session: {
      access_token: 'opaque-access',
      refresh_token: 'opaque-refresh',
      session_id: 42,
      expires_in: 900,
      access_expires_at: '2026-08-09T12:00:00Z',
      refresh_expires_at: '2026-09-09T12:00:00Z'
    }
  })

  assert.equal(session.access_token, 'opaque-access')
  assert.equal(sessions.getAccessToken(), 'opaque-access')
  assert.deepEqual(storage.values.get(AUTH_SESSION_STORAGE_KEY), session)
  assert.equal(storage.values.has(LEGACY_AUTH_TOKEN_STORAGE_KEY), false)
})

test('migrates a legacy auth token into an access-only compatibility session', () => {
  const storage = createStorage({ auth_token: 'legacy-access' })
  const sessions = createAuthSessionStorage(storage)

  assert.equal(sessions.getAccessToken(), 'legacy-access')
  assert.equal(sessions.getRefreshToken(), '')
  assert.equal(sessions.getSession(), null)

  sessions.saveLoginResult({ access_token: 'new-legacy-access' })
  assert.equal(sessions.getAccessToken(), 'new-legacy-access')
  assert.equal(storage.values.has(AUTH_SESSION_STORAGE_KEY), false)
})

test('rejects a malformed nested session instead of falling back to legacy credentials', () => {
  const storage = createStorage({ auth_token: 'old-legacy-access' })
  const sessions = createAuthSessionStorage(storage)

  assert.throws(
    () => sessions.saveLoginResult({ access_token: 'legacy-access', session: { access_token: 'incomplete' } }),
    /invalid session credentials/
  )
  assert.equal(sessions.getAccessToken(), '')
  assert.equal(storage.values.has(AUTH_SESSION_STORAGE_KEY), false)
  assert.equal(storage.values.has(LEGACY_AUTH_TOKEN_STORAGE_KEY), false)
})

test('clearing authentication removes session and legacy token atomically', () => {
  const storage = createStorage({
    [AUTH_SESSION_STORAGE_KEY]: { access_token: 'opaque-access', refresh_token: 'opaque-refresh' },
    [LEGACY_AUTH_TOKEN_STORAGE_KEY]: 'legacy-access',
    user_info: { id: 1 }
  })
  const sessions = createAuthSessionStorage(storage)

  sessions.clear()

  assert.equal(storage.values.has(AUTH_SESSION_STORAGE_KEY), false)
  assert.equal(storage.values.has(LEGACY_AUTH_TOKEN_STORAGE_KEY), false)
  assert.equal(storage.values.has('user_info'), false)
})
