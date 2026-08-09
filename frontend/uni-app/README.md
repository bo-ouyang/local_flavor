# Local Flavor uni-app

## Toolchain

- Node.js `22.23.2` (see `.nvmrc`)
- npm `10.9.8` (bundled with the pinned Node release)
- DCloud Vue 3 stable release `3.0.0-5010520260709002` / compiler 5.15
- Vue `3.4.21`, Vite `5.2.8`, TypeScript `5.4.5`

All direct DCloud compiler packages use the same release number. `@dcloudio/types`
is the documented exception: `@dcloudio/uni-app` declares the independent types
package as an exact `3.4.31` peer dependency.

Version sources:

- [DCloud stable release notes](https://uniapp.dcloud.net.cn/release.html)
- [DCloud package metadata on the official npm registry](https://www.npmjs.com/package/@dcloudio/uni-app/v/3.0.0-5010520260709002)
- [Official Node.js release index](https://nodejs.org/dist/index.json)

## Install and verify

Use the pinned Node release, then install only from the official npm registry:

```bash
npm ci --ignore-scripts --registry=https://registry.npmjs.org/
npm ls --all
npm test
npm run type-check
npm run build:mp-weixin
npm run build:h5
```

The lock file contains only `https://registry.npmjs.org/` resolved URLs. Do not use
`npm audit fix --force` or `--legacy-peer-deps`; DCloud packages must not be resolved
to unrelated historical versions.

## Dependency audit

The machine-readable baseline is stored in
`../../.github/security/npm-audit-baseline.json` and is bound to the SHA-256 of
`package-lock.json`. Validate a generated npm audit report from the repository root:

```bash
node .github/scripts/check-npm-audit-baseline.mjs \
  ci-reports/npm-audit.json \
  .github/security/npm-audit-baseline.json \
  frontend/uni-app/package-lock.json
```

The upgrade baseline is 20 low / 16 moderate / 13 high / 0 critical. Any severity
increase, any critical issue, an invalid report/manifest, or a lock hash mismatch
fails the check.

## Device verification

Static checks and builds do not replace WeChat device testing. Complete
[`docs/2026-07-30_uni-app升级真机回归清单.md`](../../docs/2026-07-30_uni-app升级真机回归清单.md)
before release.

## Authentication sessions (AUTH-01B)

The login client reads opaque credentials from `data.session`. They are persisted once as
`auth_session`; an existing `auth_token` is read only as an access-only migration fallback
until a nested session is received. Never copy either opaque token into logs, URL parameters,
or extra storage keys.

Protected requests attach the opaque access token as `Authorization: Bearer …`. Concurrent
401 responses share one `POST /user/session/refresh`, then retry their own original request
once. A failed refresh clears local state and returns the user to login; 403 responses do not
refresh. Logout always clears local state after making a best-effort
`POST /user/session/logout` call authenticated by the current Bearer access token. The client
may include its refresh token in that request body, but the current server authorizes logout
from the Bearer session and does not use the body token.

The direct-backend fallback is `http://127.0.0.1:8001/django/api/v1`, matching both checked-in
environment files. Deployments behind a reverse proxy may set `VITE_API_BASE_URL` to an absolute
public API URL or, for same-origin H5 deployments, a root-relative API prefix such as
`/api/django/api/v1`.

Image uploads use the same current access-token source and shared refresh flight as protected
REST requests. A 401 upload retries its original file once after refresh; a failed refresh
clears authentication and does not retry again. Tokens are never included in upload URLs.
Django upload responses are accepted only when `code` is exactly `0` and a URL is present.
Relative `/static/...` URLs are resolved from the API origin; absolute upload URLs are accepted
only when they use that same API origin and a `/static/` path.

Relative H5 API prefixes are resolved from the current browser origin for upload responses. App
and mini-program builds must use an absolute HTTP(S) API URL. A missing or invalid browser origin
for a relative H5 prefix fails with a generic message that does not echo configuration or
credentials. WebSocket roots are derived from an absolute API URL origin (`https`→`wss`,
`http`→`ws`), never from the `/django/api/v1` path.

Chat WebSockets send the Bearer token only in `uni.connectSocket({ header })`; the URL query
fallback is closed in this client. A successful refresh reconnects chat with the successor
access token. Platforms that cannot send WebSocket headers use the existing polling path with
a user-visible notice instead of exposing a token in the URL. The server-side legacy query
compatibility remains until AUTH-01C removes it after the client migration window. Chat pauses
polling and ignores refresh-triggered reconnects while hidden; it resumes only when shown.

The device-session panel only displays active records (`revoked_at` is empty). Revocation asks
for confirmation and disables duplicate actions until the server response completes.
