import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const readme = await readFile(new URL('../README.md', import.meta.url), 'utf8')

test('upload documentation says absolute URLs must use the API origin', () => {
  assert.match(readme, /absolute upload URLs are accepted\s+only when they use that same API origin/i)
  assert.match(readme, /relative H5 API prefixes are resolved from the current browser origin/i)
  assert.doesNotMatch(readme, /absolute backend URLs remain\s+unchanged/i)
})
