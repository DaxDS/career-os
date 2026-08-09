/**
 * Regression tests for province and stream matching.
 *
 * Run: npx tsx scripts/test-provinces.ts
 *
 * The failure this suite exists to prevent is confident wrong advice: telling someone
 * to chase a stream that closed, a sector that is not being invited, or a province
 * whose rules we never actually read. Several assertions therefore check that we stay
 * SILENT rather than that we say something.
 */
import { provincialOutlook, sectorsFor, type ProvinceInput } from "../src/lib/crs/provinces";

let passed = 0;
const failures: string[] = [];

function check(desc: string, actual: unknown, expected: unknown) {
  if (actual === expected) passed += 1;
  else failures.push(`${desc}: got ${JSON.stringify(actual)}, expected ${JSON.stringify(expected)}`);
}

function ok(desc: string, condition: boolean) {
  check(desc, condition, true);
}

function profile(over: Partial<ProvinceInput> = {}): ProvinceInput {
  return {
    noc: "21231",
    teer: 1,
    minClb: 9,
    canadianMonths: 24,
    currentProvince: "ON",
    hasNomination: false,
    ...over,
  };
}

// --- Sector classification -------------------------------------------------------
check("software dev -> technology", sectorsFor("21231").has("technology"), true);
check("registered nurse -> health", sectorsFor("31301").has("health"), true);
check("carpenter -> construction", sectorsFor("72310").has("construction"), true);
check("ECE -> childcare", sectorsFor("42202").has("childcare"), true);
check("teacher -> education", sectorsFor("41221").has("education"), true);
check("veterinarian -> veterinary", sectorsFor("31103").has("veterinary"), true);

// Narrow rules must win over the broad prefix they sit inside, or a vet gets told
// they match BC's "Care — health" invitations, which is a different sector entirely.
check("veterinarian is NOT health", sectorsFor("31103").has("health"), false);
check("ECE is NOT education", sectorsFor("42202").has("education"), false);
check("teacher is NOT childcare", sectorsFor("41221").has("childcare"), false);
check("no NOC -> no sectors", sectorsFor(null).size, 0);

// --- Verified vs unverified -------------------------------------------------------
{
  const out = provincialOutlook(profile());
  const codes = out.matches.map((m) => m.code);
  ok("only verified provinces are matched", codes.every((c) => ["ON", "BC", "AB", "SK"].includes(c)));
  ok("unverified provinces are named, not scored", out.unverified.length > 0);
  ok(
    "an unverified province never appears as a match",
    !out.unverified.some((u) => codes.includes(u.code))
  );
  // Quebec runs no PNP at all; listing it either way would be wrong.
  ok("Quebec is not offered as a PNP option", !codes.includes("QC") && !out.unverified.some((u) => u.code === "QC"));
}

// --- Ontario: closed streams must not be implied -----------------------------------
{
  const on = provincialOutlook(profile()).matches.find((m) => m.code === "ON")!;
  check("Ontario exposes exactly one open stream", on.streams.length, 1);
  check("and it is Workforce Priority", on.streams[0].id, "on_workforce_priority");
  ok(
    "Ontario's note says the other streams are closed",
    /closed/i.test(on.programNote ?? "")
  );
  ok("Workforce Priority is flagged as needing a job offer", on.streams[0].requiresJobOffer);
  ok(
    "the job-offer requirement is stated as a blocker, not assumed away",
    on.streams[0].blockers.some((b) => /job offer/i.test(b))
  );
}

// --- BC: sector targeting is the whole story ---------------------------------------
{
  const dev = provincialOutlook(profile({ noc: "21231" })).matches.find((m) => m.code === "BC")!;
  const sw = dev.streams.find((s) => s.id === "bc_skilled_worker")!;
  ok(
    "a software dev is told they are outside BC's invited sectors",
    sw.blockers.some((b) => /outside the sectors/i.test(b))
  );
  ok(
    "and is given the high-wage alternative rather than a dead end",
    sw.blockers.some((b) => /125,000|138/.test(b))
  );

  const carpenter = provincialOutlook(profile({ noc: "72310", teer: 2 })).matches.find(
    (m) => m.code === "BC"
  )!;
  const cw = carpenter.streams.find((s) => s.id === "bc_skilled_worker")!;
  ok(
    "a carpenter is matched to the construction sector with its real cut-off",
    cw.reasons.some((r) => /construction trades/i.test(r) && /88/.test(r))
  );
}

// --- Alberta and Saskatchewan: the no-job-offer routes -------------------------------
{
  const out = provincialOutlook(profile({ noc: "31301", teer: 1 }));
  const ab = out.matches.find((m) => m.code === "AB")!;
  const abEe = ab.streams.find((s) => s.id === "ab_express_entry")!;
  check("Alberta EE stream needs no job offer", abEe.requiresJobOffer, false);
  ok(
    "a nurse is told health care is a named Alberta pathway",
    abEe.reasons.some((r) => /health care/i.test(r) && /priority/i.test(r))
  );
  check("no-offer + priority sector ranks strong", abEe.fit, "strong");

  const sk = out.matches.find((m) => m.code === "SK")!;
  const skEe = sk.streams.find((s) => s.id === "sk_iswl_express_entry")!;
  ok(
    "Saskatchewan's excluded-occupation caveat is surfaced",
    skEe.reasons.some((r) => /Excluded Occupation List/i.test(r))
  );
}

// --- TEER gating -------------------------------------------------------------------
{
  const labourer = provincialOutlook(profile({ noc: "85110", teer: 5 }));
  const sk = labourer.matches.find((m) => m.code === "SK")!;
  ok("TEER 5 is blocked from SK skilled-worker streams", sk.streams.every((s) => s.fit === "blocked"));
  const on = labourer.matches.find((m) => m.code === "ON")!;
  ok("but Ontario's TEER 0-5 stream is not blocked on TEER", on.streams[0].fit !== "blocked");
}

// --- Language floors ----------------------------------------------------------------
{
  const weak = provincialOutlook(profile({ minClb: 4, teer: 1 }));
  const on = weak.matches.find((m) => m.code === "ON")!;
  ok(
    "CLB 4 is told it misses Ontario's CLB 6 floor",
    on.streams[0].blockers.some((b) => /CLB 6/.test(b))
  );
  const strong = provincialOutlook(profile({ minClb: 9, teer: 1 }));
  const on2 = strong.matches.find((m) => m.code === "ON")!;
  ok(
    "CLB 9 is told it clears that floor",
    on2.streams[0].reasons.some((r) => /clears the CLB 6 floor/.test(r))
  );
}

// --- National context ----------------------------------------------------------------
{
  const out = provincialOutlook(profile());
  check("2026 PNP allocation is carried", out.nationalContext.pnp_allocations_2026, 43999);
  ok("Quebec's exclusion is explained", /Canada-Quebec Accord/.test(out.nationalContext.quebec_note));
  ok("every match carries a source URL", out.matches.every((m) => m.sourceUrl.startsWith("https://")));
}

// --- Ranking --------------------------------------------------------------------------
{
  const out = provincialOutlook(profile({ noc: "31301", teer: 1, currentProvince: "AB" }));
  const order = out.matches.map((m) => m.code);
  ok("a no-job-offer province outranks a job-offer-only one", order.indexOf("AB") < order.indexOf("ON"));
}

for (const f of failures) console.error(`FAIL ${f}`);
console.log(`provinces: ${passed}/${passed + failures.length} passed`);
if (failures.length) process.exit(1);
