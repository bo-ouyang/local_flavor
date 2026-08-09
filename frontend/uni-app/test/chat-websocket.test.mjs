import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const chatSource = await readFile(new URL('../src/pages/chat/chat.vue', import.meta.url), 'utf8')

test('chat websocket authenticates only with an Authorization header and never a token query string', () => {
  assert.match(chatSource, /header:\s*\{\s*Authorization:\s*`Bearer \$\{accessToken\}`/s)
  assert.doesNotMatch(chatSource, /[?&]token=/)
})

test('chat logs fixed diagnostics without raw error objects', () => {
  assert.match(chatSource, /task\.onError\(\(\) => \{\s*if \(!socketGuard\.release\(task\)\) return\s*console\.warn\('chat socket unavailable'\)/s)
  assert.doesNotMatch(chatSource, /task\.onError\(\s*\(?\s*(?:err|error|e)\s*\)?\s*=>[\s\S]*?console\.(?:error|warn|log)\([^\n]*\b(?:err|error|e)\b/)
  assert.doesNotMatch(chatSource, /console\.(?:error|warn|log)\([^\n]*,\s*(?:err|error|e)\s*\)/)
})

test('chat reports a safe fallback when this platform cannot send websocket headers', () => {
  assert.match(chatSource, /不支持带认证头的聊天连接/)
  assert.match(chatSource, /onSessionRefreshed/)
})
