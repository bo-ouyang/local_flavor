import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const asgi = await readFile(new URL('../../../backend_django/config/asgi.py', import.meta.url), 'utf8')
const settings = await readFile(new URL('../../../backend_django/config/settings.py', import.meta.url), 'utf8')
const wsAuth = await readFile(new URL('../../../backend_django/messaging/ws_auth.py', import.meta.url), 'utf8')

test('WS enabled configuration fails closed and applies an origin validator', () => {
  assert.match(wsAuth, /from channels\.security\.websocket import AllowedHostsOriginValidator/)
  assert.match(wsAuth, /self\.origin_validator = AllowedHostsOriginValidator\(application\)/)
  assert.match(
    asgi,
    /"websocket": WebSocketOriginAuthValidator\(\s*TokenAuthMiddleware\(URLRouter\(websocket_urlpatterns\)\)\s*\)/s,
  )
  assert.doesNotMatch(asgi, /except Exception/)
  assert.doesNotMatch(settings, /except Exception:\s*\n\s*CHAT_ENABLE_WS = False/)
})
