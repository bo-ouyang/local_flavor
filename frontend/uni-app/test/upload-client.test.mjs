import assert from 'node:assert/strict'
import test from 'node:test'

import { createUploadClient } from '../src/utils/upload-client.js'

test('uploads once with the current opaque access token', async () => {
  const calls = []
  const client = createUploadClient({
    getAccessToken: () => 'access-1',
    refresh: async () => { throw new Error('not expected') },
    upload: async (options) => { calls.push(options); return { statusCode: 200, data: 'ok' } }
  })

  assert.deepEqual(await client.upload({ url: '/upload/', filePath: '/tmp/a.jpg', name: 'file' }), { statusCode: 200, data: 'ok' })
  assert.equal(calls[0].header.Authorization, 'Bearer access-1')
})

test('retries a 401 upload once with the successor access token', async () => {
  let token = 'access-1'
  const headers = []
  const client = createUploadClient({
    getAccessToken: () => token,
    refresh: async () => { token = 'access-2' },
    upload: async (options) => {
      headers.push(options.header.Authorization)
      return headers.length === 1 ? { statusCode: 401, data: 'expired' } : { statusCode: 200, data: 'ok' }
    }
  })

  await client.upload({ url: '/upload/', filePath: '/tmp/a.jpg', name: 'file' })
  assert.deepEqual(headers, ['Bearer access-1', 'Bearer access-2'])
})

test('shares one refresh for concurrent 401 uploads', async () => {
  let token = 'access-1'
  let refreshes = 0
  let releaseRefresh
  const refreshGate = new Promise((resolve) => { releaseRefresh = resolve })
  const client = createUploadClient({
    getAccessToken: () => token,
    refresh: async () => { refreshes += 1; await refreshGate; token = 'access-2' },
    upload: async (options) => options.header.Authorization === 'Bearer access-1'
      ? { statusCode: 401, data: 'expired' }
      : { statusCode: 200, data: 'ok' }
  })

  const first = client.upload({ url: '/upload/', filePath: '/tmp/a.jpg', name: 'file' })
  const second = client.upload({ url: '/upload/', filePath: '/tmp/b.jpg', name: 'file' })
  await Promise.resolve()
  releaseRefresh()
  await Promise.all([first, second])

  assert.equal(refreshes, 1)
})

test('does not retry an upload after refresh failure', async () => {
  let uploads = 0
  const client = createUploadClient({
    getAccessToken: () => 'access-1',
    refresh: async () => { throw new Error('refresh revoked') },
    upload: async () => { uploads += 1; return { statusCode: 401, data: 'expired' } }
  })

  await assert.rejects(client.upload({ url: '/upload/', filePath: '/tmp/a.jpg', name: 'file' }), /refresh revoked/)
  assert.equal(uploads, 1)
})

test('sanitizes upload error payloads that contain authorization credentials', async () => {
  const client = createUploadClient({
    getAccessToken: () => 'access-1',
    refresh: async () => { throw new Error('not expected') },
    upload: async () => ({ statusCode: 500, data: { Authorization: 'Bearer leaked-access', refresh_token: 'leaked-refresh' } })
  })

  await assert.rejects(client.upload({ url: '/upload/', filePath: '/tmp/a.jpg', name: 'file' }), (error) => {
    assert.deepEqual(Object.keys(error).sort(), ['code', 'message'])
    assert.doesNotMatch(JSON.stringify(error), /leaked-(access|refresh)/)
    return true
  })
})
