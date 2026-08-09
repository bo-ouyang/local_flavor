import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = await readFile(new URL('../src/pages/profile/profile.vue', import.meta.url), 'utf8')

test('session revoke controls require confirmation and expose busy disabled semantics', () => {
  assert.match(source, /uni\.showModal/)
  assert.match(source, /:disabled="sessionState\.actionBusy"/)
})
