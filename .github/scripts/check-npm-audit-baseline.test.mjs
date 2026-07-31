import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { after, test } from "node:test";
import { spawnSync } from "node:child_process";

const currentDirectory = dirname(fileURLToPath(import.meta.url));
const checker = join(currentDirectory, "check-npm-audit-baseline.mjs");
const temporaryDirectory = mkdtempSync(join(tmpdir(), "local-flavor-npm-audit-"));
const baselineCounts = Object.freeze({
  info: 0,
  low: 20,
  moderate: 16,
  high: 13,
  critical: 0,
  total: 49,
});

after(() => rmSync(temporaryDirectory, { recursive: true, force: true }));

function report(vulnerabilities) {
  return JSON.stringify({ metadata: { vulnerabilities } });
}

function sha256(contents) {
  return createHash("sha256").update(contents).digest("hex");
}

function manifest(lockContents, overrides = {}) {
  return JSON.stringify({
    schemaVersion: 1,
    createdAt: "2026-07-30",
    dcloudRelease: "3.0.0-5010520260709002",
    packageLock: {
      path: "frontend/uni-app/package-lock.json",
      sha256: sha256(lockContents),
    },
    vulnerabilities: baselineCounts,
    ...overrides,
  });
}

function runCase(
  name,
  {
    reportContents = report(baselineCounts),
    lockContents = '{"lockfileVersion":3}',
    manifestContents,
  } = {},
) {
  const reportPath = join(temporaryDirectory, `${name}-report.json`);
  const manifestPath = join(temporaryDirectory, `${name}-baseline.json`);
  const lockPath = join(temporaryDirectory, `${name}-package-lock.json`);
  writeFileSync(reportPath, reportContents, "utf8");
  writeFileSync(lockPath, lockContents, "utf8");
  writeFileSync(
    manifestPath,
    manifestContents ?? manifest(lockContents),
    "utf8",
  );
  return spawnSync(
    process.execPath,
    [checker, reportPath, manifestPath, lockPath],
    { encoding: "utf8" },
  );
}

test("accepts the manifest baseline", () => {
  const result = runCase("equal");
  assert.equal(result.status, 0, result.stderr);
});

test("accepts lower vulnerability counts", () => {
  const result = runCase("lower", {
    reportContents: report({
      info: 0,
      low: 19,
      moderate: 15,
      high: 12,
      critical: 0,
      total: 46,
    }),
  });
  assert.equal(result.status, 0, result.stderr);
});

test("rejects a severity above the manifest baseline", () => {
  const result = runCase("worse", {
    reportContents: report({ ...baselineCounts, low: 21, total: 50 }),
  });
  assert.notEqual(result.status, 0);
});

test("rejects any critical vulnerability", () => {
  const result = runCase("critical", {
    reportContents: report({ ...baselineCounts, critical: 1, total: 50 }),
  });
  assert.notEqual(result.status, 0);
});

test("rejects invalid report JSON", () => {
  const result = runCase("invalid-report", { reportContents: "not-json" });
  assert.notEqual(result.status, 0);
});

test("rejects an invalid manifest", () => {
  const result = runCase("invalid-manifest", {
    manifestContents: JSON.stringify({ schemaVersion: 1 }),
  });
  assert.notEqual(result.status, 0);
});

test("rejects a package-lock hash mismatch", () => {
  const lockContents = '{"lockfileVersion":3}';
  const result = runCase("hash-mismatch", {
    lockContents,
    manifestContents: manifest('{"lockfileVersion":2}'),
  });
  assert.notEqual(result.status, 0);
});
