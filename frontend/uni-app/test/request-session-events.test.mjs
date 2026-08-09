import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import { createSessionRefreshEmitter } from '../src/utils/session-refresh-emitter.js'

test('request refresh subscription path isolates failed listeners and still notifies later subscribers', async () => {
  const emitter = createSessionRefreshEmitter()
  const received = []
  emitter.subscribe(() => { throw new Error('first listener failed') })
  emitter.subscribe(() => Promise.reject(new Error('second listener failed')))
  emitter.subscribe((session) => { received.push(session.access_token) })

  emitter.emit({ access_token: 'rotated-access' })
  await new Promise((resolve) => setImmediate(resolve))

  assert.deepEqual(received, ['rotated-access'])
})

test('request.ts exports its refresh subscription API through the isolated emitter', async () => {
  const requestSource = await readFile(new URL('../src/utils/request.ts', import.meta.url), 'utf8')

  assert.match(requestSource, /import \{ createSessionRefreshEmitter \} from '\.\/session-refresh-emitter\.js'/)
  assert.match(requestSource, /const sessionRefreshEmitter = createSessionRefreshEmitter\(\)/)
  assert.match(requestSource, /onSessionRefreshed:\s*\(session: any\) => \{\s*sessionRefreshEmitter\.emit\(session\)\s*\}/s)
  assert.match(requestSource, /export const onSessionRefreshed = \(listener: \(session: any\) => void\) => sessionRefreshEmitter\.subscribe\(listener\)/)
})
