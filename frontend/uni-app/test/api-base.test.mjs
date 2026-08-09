import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

test('every direct-backend API fallback matches the django API prefix used by development and production env files', async () => {
  const files = [
    '../src/utils/request.ts',
    '../src/pages/chat/chat.vue',
    '../src/pages/publish/publish.vue',
    '../src/pages/community/create.vue',
    '../src/pages/community/publish.vue',
    '../.env.development',
    '../.env.production'
  ]
  const sources = await Promise.all(files.map((file) => readFile(new URL(file, import.meta.url), 'utf8')))

  for (const source of sources) {
    assert.match(source, /\/django\/api\/v1/)
  }
})
