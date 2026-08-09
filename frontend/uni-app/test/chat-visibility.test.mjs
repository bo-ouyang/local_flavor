import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import { createChatVisibilityGate } from '../src/utils/chat-visibility.js'

test('a refresh cannot connect chat while hidden but can connect again after show', () => {
  const gate = createChatVisibilityGate()
  let connects = 0

  gate.hide()
  assert.equal(gate.runWhenVisible(() => { connects += 1 }), false)
  gate.show()
  assert.equal(gate.runWhenVisible(() => { connects += 1 }), true)
  assert.equal(connects, 1)
})

test('chat uses the visibility gate around its refresh subscription and lifecycle hooks', async () => {
  const source = await readFile(new URL('../src/pages/chat/chat.vue', import.meta.url), 'utf8')

  assert.match(source, /createChatVisibilityGate/)
  assert.match(source, /visibilityGate\.runWhenVisible/)
  assert.match(source, /onHide\(\(\) => \{\s*visibilityGate\.hide\(\)/s)
  assert.match(source, /onShow\(async \(\) => \{\s*visibilityGate\.show\(\)/s)
})
