import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const packageJson = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'))

test('package declares ESM and exposes the front-end test suite through npm test', () => {
  assert.equal(packageJson.type, 'module')
  assert.match(packageJson.scripts.test, /node --test/)
})
