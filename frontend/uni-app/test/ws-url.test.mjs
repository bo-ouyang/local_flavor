import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import { getWebSocketRoot, getChatWebSocketUrl } from '../src/utils/ws-url.js'

test('derives websocket roots from the absolute API origin without django path segments', () => {
  assert.equal(getWebSocketRoot('https://host.test/django/api/v1'), 'wss://host.test')
  assert.equal(getWebSocketRoot('http://host.test/django/api/v1'), 'ws://host.test')
  assert.equal(getChatWebSocketUrl('https://host.test/django/api/v1', 42), 'wss://host.test/ws/chat/conversations/42/')
})

test('chat binds websocket URLs through the shared origin helper without token queries', async () => {
  const source = await readFile(new URL('../src/pages/chat/chat.vue', import.meta.url), 'utf8')
  assert.match(source, /getChatWebSocketUrl/)
  assert.doesNotMatch(source, /[?&]token=/)
})
