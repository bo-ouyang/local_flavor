import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const SEVERITIES = Object.freeze(["info", "low", "moderate", "high", "critical"]);
const EXPECTED_COUNT_KEYS = new Set([...SEVERITIES, "total"]);
const EXPECTED_MANIFEST_KEYS = new Set([
  "schemaVersion",
  "createdAt",
  "dcloudRelease",
  "packageLock",
  "vulnerabilities",
]);

function requireObject(value, label) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
  return value;
}

function requireExactKeys(value, expectedKeys, label) {
  for (const key of expectedKeys) {
    if (!Object.hasOwn(value, key)) {
      throw new Error(`${label}.${key} is missing`);
    }
  }
  for (const key of Object.keys(value)) {
    if (!expectedKeys.has(key)) {
      throw new Error(`${label}.${key} is unexpected`);
    }
  }
}

function validateCounts(value, label) {
  const counts = requireObject(value, label);
  requireExactKeys(counts, EXPECTED_COUNT_KEYS, label);

  for (const key of EXPECTED_COUNT_KEYS) {
    if (!Number.isSafeInteger(counts[key]) || counts[key] < 0) {
      throw new Error(`${label}.${key} must be a non-negative integer`);
    }
  }

  const calculatedTotal = SEVERITIES.reduce(
    (sum, severity) => sum + counts[severity],
    0,
  );
  if (counts.total !== calculatedTotal) {
    throw new Error(`${label}.total is ${counts.total}, expected ${calculatedTotal}`);
  }
  return counts;
}

function validateManifest(value) {
  const manifest = requireObject(value, "baseline manifest");
  requireExactKeys(manifest, EXPECTED_MANIFEST_KEYS, "baseline manifest");

  if (manifest.schemaVersion !== 1) {
    throw new Error("baseline manifest.schemaVersion must be 1");
  }
  if (
    typeof manifest.createdAt !== "string" ||
    !/^\d{4}-\d{2}-\d{2}$/.test(manifest.createdAt) ||
    Number.isNaN(Date.parse(`${manifest.createdAt}T00:00:00Z`))
  ) {
    throw new Error("baseline manifest.createdAt must be an ISO date");
  }
  if (
    typeof manifest.dcloudRelease !== "string" ||
    !/^3\.0\.0-\d+$/.test(manifest.dcloudRelease)
  ) {
    throw new Error("baseline manifest.dcloudRelease is invalid");
  }

  const packageLock = requireObject(
    manifest.packageLock,
    "baseline manifest.packageLock",
  );
  requireExactKeys(
    packageLock,
    new Set(["path", "sha256"]),
    "baseline manifest.packageLock",
  );
  if (typeof packageLock.path !== "string" || packageLock.path.length === 0) {
    throw new Error("baseline manifest.packageLock.path must be a non-empty string");
  }
  if (
    typeof packageLock.sha256 !== "string" ||
    !/^[a-f\d]{64}$/i.test(packageLock.sha256)
  ) {
    throw new Error("baseline manifest.packageLock.sha256 must be a SHA-256 digest");
  }

  const vulnerabilities = validateCounts(
    manifest.vulnerabilities,
    "baseline manifest.vulnerabilities",
  );
  if (vulnerabilities.critical !== 0) {
    throw new Error("baseline manifest must not allow critical vulnerabilities");
  }
  return manifest;
}

function sha256(contents) {
  return createHash("sha256").update(contents).digest("hex");
}

export function checkNpmAuditBaseline(report, baselineManifest, lockContents) {
  const root = requireObject(report, "npm audit report");
  const metadata = requireObject(root.metadata, "metadata");
  const counts = validateCounts(
    metadata.vulnerabilities,
    "metadata.vulnerabilities",
  );
  const manifest = validateManifest(baselineManifest);

  const actualLockHash = sha256(lockContents);
  if (actualLockHash !== manifest.packageLock.sha256.toLowerCase()) {
    throw new Error(
      `package-lock SHA-256 mismatch: expected ${manifest.packageLock.sha256}, ` +
        `got ${actualLockHash}`,
    );
  }

  const baseline = manifest.vulnerabilities;
  const regressions = SEVERITIES.filter(
    (severity) => counts[severity] > baseline[severity],
  );
  if (counts.critical > 0 || regressions.length > 0) {
    const details = regressions
      .map(
        (severity) =>
          `${severity}=${counts[severity]} (baseline ${baseline[severity]})`,
      )
      .join(", ");
    throw new Error(`npm audit baseline regressed: ${details}`);
  }

  return counts;
}

function readJson(filePath, label) {
  if (!filePath) {
    throw new Error(`${label} path is required`);
  }
  const raw = readFileSync(filePath, "utf8");
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`${label} is not valid JSON: ${error.message}`);
  }
}

const isCommandLine =
  process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url));

if (isCommandLine) {
  try {
    const [, , reportPath, manifestPath, lockPath] = process.argv;
    if (!reportPath || !manifestPath || !lockPath) {
      throw new Error(
        "usage: node check-npm-audit-baseline.mjs " +
          "<npm-audit.json> <baseline.json> <package-lock.json>",
      );
    }
    const counts = checkNpmAuditBaseline(
      readJson(reportPath, "npm audit report"),
      readJson(manifestPath, "baseline manifest"),
      readFileSync(lockPath),
    );
    console.log(
      `npm audit baseline passed: low=${counts.low}, moderate=${counts.moderate}, ` +
        `high=${counts.high}, critical=${counts.critical}`,
    );
  } catch (error) {
    console.error(`npm audit baseline failed: ${error.message}`);
    process.exitCode = 1;
  }
}
