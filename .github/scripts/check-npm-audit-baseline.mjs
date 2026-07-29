import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

export const NPM_AUDIT_BASELINE = Object.freeze({
  info: 0,
  low: 11,
  moderate: 17,
  high: 42,
  critical: 0,
});

const SEVERITIES = Object.keys(NPM_AUDIT_BASELINE);
const EXPECTED_KEYS = new Set([...SEVERITIES, "total"]);

function requireObject(value, label) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
  return value;
}

export function checkNpmAuditBaseline(report) {
  const root = requireObject(report, "npm audit report");
  const metadata = requireObject(root.metadata, "metadata");
  const counts = requireObject(metadata.vulnerabilities, "metadata.vulnerabilities");
  const keys = Object.keys(counts);

  for (const key of EXPECTED_KEYS) {
    if (!Object.hasOwn(counts, key)) {
      throw new Error(`metadata.vulnerabilities.${key} is missing`);
    }
  }
  for (const key of keys) {
    if (!EXPECTED_KEYS.has(key)) {
      throw new Error(`metadata.vulnerabilities.${key} is unexpected`);
    }
  }
  for (const key of EXPECTED_KEYS) {
    if (!Number.isSafeInteger(counts[key]) || counts[key] < 0) {
      throw new Error(`metadata.vulnerabilities.${key} must be a non-negative integer`);
    }
  }

  const calculatedTotal = SEVERITIES.reduce((sum, severity) => sum + counts[severity], 0);
  if (counts.total !== calculatedTotal) {
    throw new Error(
      `metadata.vulnerabilities.total is ${counts.total}, expected ${calculatedTotal}`,
    );
  }

  const regressions = SEVERITIES.filter(
    (severity) => counts[severity] > NPM_AUDIT_BASELINE[severity],
  );
  if (counts.critical > 0 || regressions.length > 0) {
    const details = regressions
      .map(
        (severity) =>
          `${severity}=${counts[severity]} (baseline ${NPM_AUDIT_BASELINE[severity]})`,
      )
      .join(", ");
    throw new Error(`npm audit baseline regressed: ${details}`);
  }

  return counts;
}

function readReport(reportPath) {
  if (!reportPath) {
    throw new Error("usage: node check-npm-audit-baseline.mjs <npm-audit.json>");
  }
  const raw = readFileSync(reportPath, "utf8");
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`npm audit report is not valid JSON: ${error.message}`);
  }
}

const isCommandLine =
  process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url));

if (isCommandLine) {
  try {
    const counts = checkNpmAuditBaseline(readReport(process.argv[2]));
    console.log(
      `npm audit baseline passed: low=${counts.low}, moderate=${counts.moderate}, ` +
        `high=${counts.high}, critical=${counts.critical}`,
    );
  } catch (error) {
    console.error(`npm audit baseline failed: ${error.message}`);
    process.exitCode = 1;
  }
}
