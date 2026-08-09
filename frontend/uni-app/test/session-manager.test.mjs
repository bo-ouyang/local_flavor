import assert from 'node:assert/strict'
import test from 'node:test'

import { createSessionManager } from '../src/utils/session-manager.js'

test('loads owned device sessions and exposes an empty state', async () => {
  const manager = createSessionManager({
    request: { authGet: async () => [] }
  })

  await manager.load()

  assert.equal(manager.state.loading, false)
  assert.equal(manager.state.error, '')
  assert.deepEqual(manager.state.sessions, [])
})

test('reports a clear UTF-8 Chinese loading error when session loading fails', async () => {
  const manager = createSessionManager({
    request: { authGet: async () => { throw {} } }
  })

  await assert.rejects(manager.load())
  assert.equal(manager.state.error, '设备会话加载失败')
})

test('shows only active sessions because the API includes revoked_at history records', async () => {
  const manager = createSessionManager({
    request: {
      authGet: async () => [
        { id: 7, current: true, revoked_at: null },
        { id: 8, current: false, revoked_at: '2026-08-09T10:00:00Z' }
      ]
    }
  })

  await manager.load()

  assert.deepEqual(manager.state.sessions, [{ id: 7, current: true, revoked_at: null }])
})

test('prevents a second revoke while the first revocation is in progress', async () => {
  let release
  let calls = 0
  const gate = new Promise((resolve) => { release = resolve })
  const manager = createSessionManager({
    request: {
      authGet: async () => [{ id: 8, current: false, revoked_at: null }],
      authPost: async () => { calls += 1; await gate; return { session_id: 8 } }
    }
  })
  await manager.load()

  const first = manager.revoke(8)
  const second = manager.revoke(8)
  assert.equal(manager.state.actionBusy, true)
  assert.equal(await second, undefined)
  release()
  await first
  assert.equal(calls, 1)
  assert.equal(manager.state.actionBusy, false)
})

test('revoking the current owned session clears state and requests local logout', async () => {
  let currentRevoked = 0
  const calls = []
  const manager = createSessionManager({
    onCurrentRevoked: () => { currentRevoked += 1 },
    request: {
      authGet: async () => [{ id: 7, current: true, device_label: '我的手机' }],
      authPost: async (url) => { calls.push(url); return { session_id: 7 } }
    }
  })
  await manager.load()

  await manager.revoke(7)

  assert.deepEqual(calls, ['/user/sessions/7/revoke'])
  assert.equal(currentRevoked, 1)
  assert.deepEqual(manager.state.sessions, [])
})

test('revoking other devices refreshes the session list', async () => {
  let loads = 0
  const manager = createSessionManager({
    request: {
      authGet: async () => {
        loads += 1
        return loads === 1 ? [{ id: 7, current: true }, { id: 8, current: false }] : [{ id: 7, current: true }]
      },
      authPost: async () => ({ revoked_count: 1 })
    }
  })
  await manager.load()

  await manager.revokeOthers()

  assert.equal(loads, 2)
  assert.deepEqual(manager.state.sessions, [{ id: 7, current: true }])
})
