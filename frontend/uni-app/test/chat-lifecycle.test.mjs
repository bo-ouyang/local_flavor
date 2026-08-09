import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import { createSocketGenerationGuard } from '../src/utils/socket-generation.js'

test('an old socket close callback cannot release the active successor socket', () => {
  const guard = createSocketGenerationGuard()
  const first = {}
  const second = {}

  guard.activate(first)
  guard.activate(second)

  assert.equal(guard.release(first), false)
  assert.equal(guard.current(), second)
  assert.equal(guard.release(second), true)
  assert.equal(guard.current(), null)
})

test('chat stops polling while hidden and resumes polling when shown', async () => {
  const source = await readFile(new URL('../src/pages/chat/chat.vue', import.meta.url), 'utf8')

  assert.match(source, /createSocketGenerationGuard/)
  assert.match(source, /onHide\(\(\) => \{\s*visibilityGate\.hide\(\)\s*closeSocket\(\)\s*stopPolling\(\)/s)
  assert.match(source, /onShow\(async \(\) => \{[\s\S]*startPolling\(\)/)
})
