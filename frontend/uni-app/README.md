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
