import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = await readFile(new URL('../src/utils/request-client.js', import.meta.url), 'utf8')
const requestSource = await readFile(new URL('../src/utils/request.ts', import.meta.url), 'utf8')

test('request envelope detection uses the broadly compatible own-property call form', () => {
  assert.doesNotMatch(source, /Object\.hasOwn\(/)
  assert.match(source, /Object\.prototype\.hasOwnProperty\.call/)
})

test('request module does not retain the deprecated upload-header API', () => {
  assert.doesNotMatch(requestSource, /getUploadAuthorizationHeader/)
})
