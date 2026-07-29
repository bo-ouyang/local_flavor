import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { after, test } from "node:test";
import { spawnSync } from "node:child_process";

const currentDirectory = dirname(fileURLToPath(import.meta.url));
const checker = join(currentDirectory, "check-npm-audit-baseline.mjs");
const temporaryDirectory = mkdtempSync(join(tmpdir(), "local-flavor-npm-audit-"));

after(() => rmSync(temporaryDirectory, { recursive: true, force: true }));

function report(vulnerabilities) {
  return JSON.stringify({ metadata: { vulnerabilities } });
}

function runCase(name, contents) {
  const reportPath = join(temporaryDirectory, `${name}.json`);
  writeFileSync(reportPath, contents, "utf8");
  return spawnSync(process.execPath, [checker, reportPath], { encoding: "utf8" });
}

test("accepts the exact npm audit baseline", () => {
  const result = runCase(
    "equal",
    report({ info: 0, low: 11, moderate: 17, high: 42, critical: 0, total: 70 }),
  );
  assert.equal(result.status, 0, result.stderr);
});

test("accepts a lower vulnerability count", () => {
  const result = runCase(
    "lower",
    report({ info: 0, low: 10, moderate: 16, high: 41, critical: 0, total: 67 }),
  );
  assert.equal(result.status, 0, result.stderr);
});

test("rejects a severity above the baseline", () => {
  const result = runCase(
    "worse",
    report({ info: 0, low: 12, moderate: 17, high: 42, critical: 0, total: 71 }),
  );
  assert.notEqual(result.status, 0);
});

test("rejects any critical vulnerability", () => {
  const result = runCase(
    "critical",
    report({ info: 0, low: 11, moderate: 17, high: 42, critical: 1, total: 71 }),
  );
  assert.notEqual(result.status, 0);
});

test("rejects invalid JSON", () => {
  const result = runCase("invalid", "not-json");
  assert.notEqual(result.status, 0);
});

test("rejects an invalid report structure", () => {
  const result = runCase("invalid-structure", JSON.stringify({ metadata: {} }));
  assert.notEqual(result.status, 0);
});
