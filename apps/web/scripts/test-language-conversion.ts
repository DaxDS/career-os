/**
 * Regression tests for language test to CLB/NCLC conversion.
 *
 * Run: npx tsx scripts/test-language-conversion.ts
 *
 * Every expectation is read off IRCC's published equivalency charts. These are the
 * source tables, not sanity checks on our own arithmetic — language is the largest
 * CRS factor after age, so an off-by-one band here moves someone's score by tens of
 * points and can flip whether they clear a draw.
 */
import { toClb, convertAll } from "../src/lib/crs/language-conversion";

let passed = 0;
const failures: string[] = [];

function check(desc: string, actual: unknown, expected: unknown) {
  if (actual === expected) passed += 1;
  else failures.push(`${desc}: got ${JSON.stringify(actual)}, expected ${JSON.stringify(expected)}`);
}

// --- IELTS General Training ---------------------------------------------------
// CLB 7 is the floor for TEER 0/1 eligibility, so these boundaries matter most.
check("IELTS speaking 6.0 -> CLB 7", toClb("ielts", "speaking", 6.0), 7);
check("IELTS listening 6.0 -> CLB 7", toClb("ielts", "listening", 6.0), 7);
check("IELTS reading 6.0 -> CLB 7", toClb("ielts", "reading", 6.0), 7);
check("IELTS writing 6.0 -> CLB 7", toClb("ielts", "writing", 6.0), 7);

check("IELTS speaking 6.5 -> CLB 8", toClb("ielts", "speaking", 6.5), 8);
check("IELTS listening 7.5 -> CLB 8", toClb("ielts", "listening", 7.5), 8);
check("IELTS listening 7.0 -> CLB 7", toClb("ielts", "listening", 7.0), 7);

check("IELTS speaking 7.0 -> CLB 9", toClb("ielts", "speaking", 7.0), 9);
check("IELTS listening 8.0 -> CLB 9", toClb("ielts", "listening", 8.0), 9);
check("IELTS reading 7.0 -> CLB 9", toClb("ielts", "reading", 7.0), 9);

check("IELTS speaking 7.5 -> CLB 10", toClb("ielts", "speaking", 7.5), 10);
check("IELTS listening 8.5 -> CLB 10", toClb("ielts", "listening", 8.5), 10);
check("IELTS reading 8.0 -> CLB 10", toClb("ielts", "reading", 8.0), 10);
check("IELTS speaking 9.0 -> CLB 10 (max band still CLB 10)", toClb("ielts", "speaking", 9.0), 10);

check("IELTS reading 3.5 -> CLB 4", toClb("ielts", "reading", 3.5), 4);
check("IELTS reading 3.0 -> 0 (below CLB 4)", toClb("ielts", "reading", 3.0), 0);
check("IELTS speaking 0 -> 0", toClb("ielts", "speaking", 0), 0);

// --- CELPIP: level maps straight to CLB ---------------------------------------
check("CELPIP 9 -> CLB 9", toClb("celpip", "speaking", 9), 9);
check("CELPIP 4 -> CLB 4", toClb("celpip", "reading", 4), 4);
check("CELPIP 12 -> CLB 12", toClb("celpip", "writing", 12), 12);

// --- PTE Core ------------------------------------------------------------------
check("PTE speaking 68 -> CLB 7", toClb("pte", "speaking", 68), 7);
check("PTE listening 60 -> CLB 7", toClb("pte", "listening", 60), 7);
check("PTE speaking 84 -> CLB 9", toClb("pte", "speaking", 84), 9);
check("PTE writing 90 -> CLB 10", toClb("pte", "writing", 90), 10);
check("PTE listening 27 -> 0 (below CLB 4)", toClb("pte", "listening", 27), 0);

// --- TEF Canada ----------------------------------------------------------------
check("TEF speaking 310 -> NCLC 7", toClb("tef", "speaking", 310), 7);
check("TEF listening 249 -> NCLC 7", toClb("tef", "listening", 249), 7);
check("TEF speaking 371 -> NCLC 9", toClb("tef", "speaking", 371), 9);
check("TEF reading 263 -> NCLC 10", toClb("tef", "reading", 263), 10);
check("TEF speaking 180 -> 0 (below NCLC 4)", toClb("tef", "speaking", 180), 0);

// --- TCF Canada ----------------------------------------------------------------
check("TCF speaking 10 -> NCLC 7", toClb("tcf", "speaking", 10), 7);
check("TCF listening 458 -> NCLC 7", toClb("tcf", "listening", 458), 7);
check("TCF speaking 14 -> NCLC 9", toClb("tcf", "speaking", 14), 9);
check("TCF reading 549 -> NCLC 10", toClb("tcf", "reading", 549), 10);
check("TCF speaking 3 -> 0 (below NCLC 4)", toClb("tcf", "speaking", 3), 0);

// --- "none" and direct entry ---------------------------------------------------
check("no French test -> 0", toClb("none", "speaking", 400), 0);
check("direct CLB entry passes through", toClb("clb", "speaking", 9), 9);
check("direct NCLC entry passes through", toClb("nclc", "reading", 7), 7);

// --- convertAll -----------------------------------------------------------------
// The exact profile the CRS engine consumes: a real IELTS report, all four abilities.
const ielts = convertAll("ielts", { reading: 7.0, writing: 7.0, listening: 8.0, speaking: 7.0 });
check("convertAll IELTS reading", ielts.reading, 9);
check("convertAll IELTS writing", ielts.writing, 9);
check("convertAll IELTS listening", ielts.listening, 9);
check("convertAll IELTS speaking", ielts.speaking, 9);

const noFrench = convertAll("none", { reading: 0, writing: 0, listening: 0, speaking: 0 });
check("convertAll none -> all zero", JSON.stringify(noFrench), JSON.stringify({ reading: 0, writing: 0, listening: 0, speaking: 0 }));

for (const f of failures) console.error(`FAIL ${f}`);
console.log(`language conversion: ${passed}/${passed + failures.length} passed`);
if (failures.length) process.exit(1);
