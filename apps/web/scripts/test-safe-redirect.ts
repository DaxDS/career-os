/**
 * Regression tests for safeRedirect.
 *
 * Run: npm run test:redirect  (from apps/web)
 *
 * Guards an open-redirect fix on the login page. The hyphen and punctuation cases are
 * not padding — a first attempt at this used the character class [ -], which is a
 * range that silently also matches a literal hyphen and would have rejected
 * /onboarding/work-history, sending every user to the dashboard instead.
 */
import { safeRedirect } from "../src/lib/safe-redirect";

const BS = String.fromCharCode(92);
const TAB = String.fromCharCode(9);
const NUL = String.fromCharCode(0);

const cases: Array<[string | null, string, string]> = [
  // Legitimate same-origin paths must pass through untouched.
  ["/dashboard", "/dashboard", "plain path"],
  ["/onboarding/work-history", "/onboarding/work-history", "path with hyphen"],
  ["/a-b_c.d~e", "/a-b_c.d~e", "punctuation in path"],
  ["/pathways?tab=routes", "/pathways?tab=routes", "path with query string"],
  ["/evil.com", "/evil.com", "single-slash path is same-origin"],

  // Fallbacks.
  [null, "/dashboard", "null"],
  ["", "/dashboard", "empty string"],
  ["dashboard", "/dashboard", "missing leading slash"],

  // Open-redirect vectors.
  ["https://evil.com", "/dashboard", "absolute https"],
  ["http://evil.com", "/dashboard", "absolute http"],
  ["//evil.com", "/dashboard", "protocol-relative"],
  ["/" + BS + "evil.com", "/dashboard", "backslash protocol-relative"],
  ["/%2f%2fevil.com", "/dashboard", "encoded protocol-relative"],
  ["/%5C%5Cevil.com", "/dashboard", "encoded double backslash"],
  ["javascript:alert(1)", "/dashboard", "javascript scheme"],
  ["/javascript:alert(1)", "/dashboard", "scheme after slash"],
  ["data:text/html,x", "/dashboard", "data uri"],

  // Malformed / control characters.
  ["/path with space", "/dashboard", "whitespace"],
  ["/" + TAB + "x", "/dashboard", "tab"],
  ["/" + NUL + "x", "/dashboard", "null byte"],
  ["/%ZZ", "/dashboard", "malformed percent-encoding"],
];

let passed = 0;
const failures: string[] = [];

for (const [input, expected, description] of cases) {
  const actual = safeRedirect(input);
  if (actual === expected) {
    passed += 1;
  } else {
    failures.push(
      `${description}: safeRedirect(${JSON.stringify(input)}) = ${JSON.stringify(actual)}, expected ${JSON.stringify(expected)}`
    );
  }
}

for (const failure of failures) console.error(`FAIL ${failure}`);
console.log(`safeRedirect: ${passed}/${cases.length} passed`);
if (failures.length > 0) process.exit(1);
