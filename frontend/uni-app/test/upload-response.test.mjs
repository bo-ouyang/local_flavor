import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import { parseUploadResponse, resolveUploadUrl } from '../src/utils/upload-response.js'

test('accepts the Django upload success envelope with code zero and a relative URL', () => {
  assert.equal(
    parseUploadResponse({ data: JSON.stringify({ code: 0, data: { url: '/static/uploads/a.jpg' } }) }),
    '/static/uploads/a.jpg'
  )
})

test('rejects non-zero or incomplete upload envelopes', () => {
  assert.throws(() => parseUploadResponse({ data: JSON.stringify({ code: 1, data: { url: '/static/uploads/a.jpg' } }) }), /upload failed/)
  assert.throws(() => parseUploadResponse({ data: JSON.stringify({ code: 0, data: {} }) }), /upload failed/)
})

test('resolves only same-origin static upload URLs', () => {
  assert.equal(
    resolveUploadUrl('http://127.0.0.1:8001/django/api/v1', '/static/uploads/a.jpg'),
    'http://127.0.0.1:8001/static/uploads/a.jpg'
  )
  assert.equal(
    resolveUploadUrl('http://127.0.0.1:8001/django/api/v1', 'http://127.0.0.1:8001/static/uploads/a.jpg'),
    'http://127.0.0.1:8001/static/uploads/a.jpg'
  )
  assert.throws(() => resolveUploadUrl('http://127.0.0.1:8001/django/api/v1', '//attacker.test/static/a.jpg'), /invalid upload URL/)
  assert.throws(() => resolveUploadUrl('http://127.0.0.1:8001/django/api/v1', 'https://attacker.test/static/a.jpg'), /invalid upload URL/)
  assert.throws(() => resolveUploadUrl('http://127.0.0.1:8001/django/api/v1', '/media/a.jpg'), /invalid upload URL/)
})

test('rejects a non-absolute API base with a friendly non-sensitive error', () => {
  assert.throws(() => resolveUploadUrl('/django/api/v1', '/static/uploads/a.jpg'), /invalid API base/)
})

test('all upload pages delegate response parsing and static URL construction to the shared helper', async () => {
  const pages = [
    '../src/pages/publish/publish.vue',
    '../src/pages/community/create.vue',
    '../src/pages/community/publish.vue'
  ]
  const sources = await Promise.all(pages.map((page) => readFile(new URL(page, import.meta.url), 'utf8')))
  for (const source of sources) {
    assert.match(source, /parseUploadResponse/)
    assert.match(source, /resolveUploadUrl/)
    assert.doesNotMatch(source, /API_ORIGIN/)
  }
})
