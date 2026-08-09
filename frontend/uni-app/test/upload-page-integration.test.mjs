import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

test('every upload page uses the shared authenticated upload client', async () => {
  const pages = [
    '../src/pages/publish/publish.vue',
    '../src/pages/community/create.vue',
    '../src/pages/community/publish.vue'
  ]
  const sources = await Promise.all(pages.map((page) => readFile(new URL(page, import.meta.url), 'utf8')))

  for (const source of sources) {
    assert.match(source, /uploadWithAuth/)
    assert.doesNotMatch(source, /uni\.uploadFile/)
  }
})
