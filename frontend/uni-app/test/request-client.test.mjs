import assert from 'node:assert/strict'
import test from 'node:test'

import { createRequestClient } from '../src/utils/request-client.js'

const session = {
  access_token: 'access-1',
  refresh_token: 'refresh-1',
  session_id: 7,
  expires_in: 900,
  access_expires_at: '2026-08-09T12:00:00Z',
  refresh_expires_at: '2026-09-09T12:00:00Z'
}

const createSessions = (value = session) => ({
  current: value,
  generation: 0,
  cleared: 0,
  getAccessToken() { return this.current?.access_token || '' },
  getAccountGeneration() { return this.generation },
  getRefreshToken() { return this.current?.refresh_token || '' },
  saveSession(next) { this.current = next },
  clear() { this.current = null; this.cleared += 1; this.generation += 1 },
  login(next) { this.current = next; this.generation += 1 }
})

test('coalesces concurrent 401 responses into one refresh and retries each original request once', async () => {
  const sessions = createSessions()
  const store = { token: 'access-1' }
  const calls = []
  let releaseRefresh
  const refreshGate = new Promise((resolve) => { releaseRefresh = resolve })
  const client = createRequestClient({
    sessions,
    onSessionRefreshed: (nextSession) => { store.token = nextSession.access_token },
    request: async (options) => {
      calls.push(options)
      if (options.url === '/user/session/refresh') {
        await refreshGate
        return { statusCode: 200, data: { code: 0, message: 'ok', data: { ...session, access_token: 'access-2', refresh_token: 'refresh-2' } } }
      }
      if (options.header.Authorization === 'Bearer access-1') {
        return { statusCode: 401, data: { message: 'expired' } }
      }
      return { statusCode: 200, data: { code: 0, message: 'ok', data: options.url } }
    }
  })

  const first = client.authGet('/first')
  const second = client.authGet('/second')
  await Promise.resolve()
  releaseRefresh()

  assert.deepEqual(await Promise.all([first, second]), ['/first', '/second'])
  assert.equal(calls.filter((call) => call.url === '/user/session/refresh').length, 1)
  assert.equal(calls.filter((call) => call.url === '/first').length, 2)
  assert.equal(calls.filter((call) => call.url === '/second').length, 2)
  assert.equal(store.token, 'access-2')
})

test('retries a late old-token 401 with the successor without a second refresh', async () => {
  const sessions = createSessions()
  const calls = []
  let releaseLate
  const lateResponse = new Promise((resolve) => { releaseLate = resolve })
  let refreshes = 0
  const client = createRequestClient({
    sessions,
    request: async (options) => {
      calls.push({ url: options.url, authorization: options.header.Authorization })
      if (options.url === '/user/session/refresh') {
        refreshes += 1
        return { statusCode: 200, data: { code: 0, message: 'ok', data: { ...session, access_token: 'access-2', refresh_token: 'refresh-2' } } }
      }
      if (options.url === '/late' && options.header.Authorization === 'Bearer access-1') return lateResponse
      if (options.header.Authorization === 'Bearer access-1') return { statusCode: 401, data: { message: 'expired' } }
      return { statusCode: 200, data: { code: 0, message: 'ok', data: options.url } }
    }
  })

  const late = client.authGet('/late')
  const first = await client.authGet('/first')
  releaseLate({ statusCode: 401, data: { message: 'late expired' } })

  assert.equal(first, '/first')
  assert.equal(await late, '/late')
  assert.equal(refreshes, 1)
  assert.deepEqual(calls.filter((call) => call.url === '/late').map((call) => call.authorization), ['Bearer access-1', 'Bearer access-2'])
})

test('does not let an old account refresh overwrite a newer login', async () => {
  const sessions = createSessions()
  let releaseRefresh
  const refreshGate = new Promise((resolve) => { releaseRefresh = resolve })
  const client = createRequestClient({
    sessions,
    request: async (options) => {
      if (options.url === '/user/session/refresh') return refreshGate
      return { statusCode: 401, data: { message: 'expired' } }
    }
  })

  const oldRequest = client.authGet('/old-account')
  await Promise.resolve()
  sessions.login({ ...session, access_token: 'account-b-access', refresh_token: 'account-b-refresh' })
  releaseRefresh({ statusCode: 200, data: { code: 0, message: 'ok', data: { ...session, access_token: 'old-successor', refresh_token: 'old-refresh' } } })

  await assert.rejects(oldRequest, { code: 401 })
  assert.equal(sessions.getAccessToken(), 'account-b-access')
  assert.equal(sessions.cleared, 0)
})

test('does not clear a newer login when an old account refresh fails', async () => {
  const sessions = createSessions()
  let releaseRefresh
  const refreshGate = new Promise((resolve) => { releaseRefresh = resolve })
  const client = createRequestClient({
    sessions,
    request: async (options) => options.url === '/user/session/refresh'
      ? refreshGate
      : { statusCode: 401, data: { message: 'expired' } }
  })

  const oldRequest = client.authGet('/old-account')
  await Promise.resolve()
  sessions.login({ ...session, access_token: 'account-b-access', refresh_token: 'account-b-refresh' })
  releaseRefresh({ statusCode: 401, data: { message: 'replayed' } })

  await assert.rejects(oldRequest, { code: 401 })
  assert.equal(sessions.getAccessToken(), 'account-b-access')
  assert.equal(sessions.cleared, 0)
})

test('does not propagate access-token snapshots through 403 or 5xx errors', async () => {
  for (const statusCode of [403, 500]) {
    const client = createRequestClient({
      sessions: createSessions(),
      request: async () => ({ statusCode, data: { message: 'failed' } })
    })

    await assert.rejects(client.authGet(`/status-${statusCode}`), (error) => {
      assert.doesNotMatch(JSON.stringify(error), /access-1/)
      assert.equal(Object.prototype.hasOwnProperty.call(error, 'requestAccessToken'), false)
      return true
    })
  }
})

test('sanitizes response bodies that contain bearer or refresh credentials', async () => {
  const client = createRequestClient({
    sessions: createSessions(),
    request: async () => ({ statusCode: 500, data: { message: 'failed', request_id: 'req-123', Authorization: 'Bearer leaked-access', refresh_token: 'leaked-refresh' } })
  })

  await assert.rejects(client.authGet('/sensitive-error'), (error) => {
    assert.deepEqual(Object.keys(error).sort(), ['code', 'message', 'request_id'])
    assert.equal(error.request_id, 'req-123')
    assert.doesNotMatch(JSON.stringify(error), /leaked-(access|refresh)/)
    return true
  })
})

test('never adopts server or transport error messages that contain credentials', async () => {
  const serverClient = createRequestClient({
    sessions: createSessions(),
    request: async () => ({ statusCode: 500, data: { message: 'Bearer leaked-access leaked-refresh' } })
  })
  const transportClient = createRequestClient({
    sessions: createSessions(),
    request: async () => Promise.reject({ header: { Authorization: 'Bearer leaked-access' }, body: { refresh_token: 'leaked-refresh' } })
  })
  for (const client of [serverClient, transportClient]) {
    await assert.rejects(client.authGet('/sensitive'), (error) => {
      assert.doesNotMatch(JSON.stringify(error), /leaked-(access|refresh)/)
      assert.match(error.message, /^(Request failed|Network request failed)$/)
      return true
    })
  }
})

test('clears and redirects exactly once when refresh fails without recursively refreshing', async () => {
  const sessions = createSessions()
  let redirects = 0
  let calls = 0
  const client = createRequestClient({
    sessions,
    onAuthFailure: () => { redirects += 1 },
    request: async (options) => {
      calls += 1
      if (options.url === '/user/session/refresh') return { statusCode: 401, data: { message: 'replayed' } }
      return { statusCode: 401, data: { message: 'expired' } }
    }
  })

  await assert.rejects(client.authGet('/private'), { code: 401 })
  assert.equal(calls, 2)
  assert.equal(sessions.cleared, 1)
  assert.equal(redirects, 1)
})

test('reports a later auth failure after a new login resets the failure guard', async () => {
  const sessions = createSessions()
  let redirects = 0
  const client = createRequestClient({
    sessions,
    onAuthFailure: () => { redirects += 1 },
    request: async (options) => ({
      statusCode: 401,
      data: { message: options.url === '/user/session/refresh' ? 'replayed' : 'expired' }
    })
  })

  await assert.rejects(client.authGet('/before-login'), { code: 401 })
  sessions.current = { ...session, access_token: 'access-after-login', refresh_token: 'refresh-after-login' }
  client.resetAuthFailure()
  await assert.rejects(client.authGet('/after-login'), { code: 401 })

  assert.equal(sessions.cleared, 2)
  assert.equal(redirects, 2)
})

test('isolates synchronous and asynchronous refresh listeners from successful session rotation', async () => {
  const sessions = createSessions()
  let listenerCalls = 0
  const client = createRequestClient({
    sessions,
    onSessionRefreshed: () => {
      listenerCalls += 1
      throw new Error('listener failure')
    },
    request: async (options) => {
      if (options.url === '/user/session/refresh') {
        return { statusCode: 200, data: { code: 0, message: 'ok', data: { ...session, access_token: 'access-2', refresh_token: 'refresh-2' } } }
      }
      if (options.header.Authorization === 'Bearer access-1') return { statusCode: 401, data: { message: 'expired' } }
      return { statusCode: 200, data: { code: 0, message: 'ok', data: 'successor request' } }
    }
  })

  assert.equal(await client.authGet('/after-listener-failure'), 'successor request')
  assert.equal(sessions.getAccessToken(), 'access-2')
  assert.equal(listenerCalls, 1)
})

test('does not refresh on 403', async () => {
  const sessions = createSessions()
  const calls = []
  const client = createRequestClient({
    sessions,
    request: async (options) => {
      calls.push(options.url)
      return { statusCode: 403, data: { message: 'forbidden' } }
    }
  })

  await assert.rejects(client.authGet('/private'), { code: 403 })
  assert.deepEqual(calls, ['/private'])
})

test('logout uses the current bearer session and clears locally even if server revocation fails', async () => {
  const sessions = createSessions()
  let logoutPayload
  const client = createRequestClient({
    sessions,
    request: async (options) => {
      logoutPayload = options.data
      return { statusCode: 0, data: {} }
    }
  })

  await client.logout()
  assert.equal(logoutPayload.refresh_token, 'refresh-1')
  assert.equal(sessions.cleared, 1)
})
