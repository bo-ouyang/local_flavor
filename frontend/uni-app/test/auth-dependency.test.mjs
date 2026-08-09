import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const requestSource = await readFile(new URL('../src/utils/request.ts', import.meta.url), 'utf8')

test('request transport does not import the user store or navigation helper', () => {
  assert.doesNotMatch(requestSource, /from ['"]@\/stores\/user['"]/)
  assert.doesNotMatch(requestSource, /from ['"]@\/utils\/auth['"]/)
})
