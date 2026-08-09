/**
 * Province-and-stream matching: which part of Canada, which stream, which occupation.
 *
 * The report used to end its provincial advice at "pursue a provincial nomination,
 * 600 points, effort: high". That is true and useless — it names no province, no
 * stream, and no occupation, and it is the same sentence for a welder in Alberta and
 * a childcare worker in BC.
 *
 * Three rules carry over from the draw-landscape code, for the same reason:
 *
 *  1. Unverified data never becomes advice. A province whose streams have not been
 *     read off its own page is surfaced as "check directly", never as a match.
 *  2. What is closed is called closed. Ontario has shut every stream but one; a
 *     report that still implies the Human Capital stream exists is worse than silent.
 *  3. A stream requiring a job offer is stated as requiring one. We do not collect
 *     job-offer status, so it is a condition to meet — never an assumed pass.
 *
 * Informational only. Not immigration advice.
 */

import data from "./provinces-data.json";

export type Fit = "strong" | "possible" | "conditional" | "blocked";

export interface StreamMatch {
  id: string;
  label: string;
  fit: Fit;
  expressEntryAligned: boolean;
  requiresJobOffer: boolean;
  /** Why this stream is or isn't a route for this person. */
  reasons: string[];
  /** What stands between them and it. */
  blockers: string[];
  sourceUrl: string;
}

export interface ProvinceMatch {
  code: string;
  name: string;
  program: string;
  verified: boolean;
  programNote: string | null;
  sourceUrl: string;
  /** Best fit across the province's streams, for ranking. */
  fit: Fit;
  streams: StreamMatch[];
}

const FIT_RANK: Record<Fit, number> = { strong: 0, possible: 1, conditional: 2, blocked: 3 };

/**
 * Sector classification by NOC 2021 code.
 *
 * Order matters: veterinary codes sit inside the health broad category, so they are
 * matched first. Prefixes are used only where the whole major group belongs to the
 * sector; anything narrower is listed explicitly.
 */
const SECTOR_RULES: { id: string; codes?: string[]; prefixes?: string[] }[] = [
  { id: "veterinary", codes: ["31103", "32104"] },
  { id: "childcare", codes: ["42202", "44100"] },
  { id: "education", codes: ["41220", "41221", "42203", "43100"] },
  { id: "health", prefixes: ["31", "32", "33"] },
  { id: "construction", prefixes: ["72", "73"], codes: ["70010", "70011"] },
  { id: "technology", prefixes: ["21", "22"] },
  { id: "policing", codes: ["42100", "42101"] },
];

export function sectorsFor(noc: string | null): Set<string> {
  const found = new Set<string>();
  if (!noc) return found;
  const code = noc.trim();
  for (const rule of SECTOR_RULES) {
    if (rule.codes?.includes(code)) {
      found.add(rule.id);
      continue;
    }
    if (rule.prefixes?.some((p) => code.startsWith(p))) found.add(rule.id);
  }
  // A veterinarian is not a candidate for BC's "Care — health" sector, and an
  // early childhood educator is not "Care — education". Keep the narrow win.
  if (found.has("veterinary")) found.delete("health");
  if (found.has("childcare")) found.delete("education");
  return found;
}

export interface ProvinceInput {
  noc: string | null;
  teer: number | null;
  minClb: number;
  /** Months of Canadian work experience. */
  canadianMonths: number;
  /** Where they already are, if known — a stream you are standing in is easier to enter. */
  currentProvince: string | null;
  hasNomination: boolean;
}

interface RawStream {
  id: string;
  label: string;
  requires_job_offer: boolean;
  express_entry_aligned: boolean;
  ee_note?: string;
  teer_eligible?: number[];
  min_clb_by_group?: Record<string, number>;
  min_education?: string;
  min_experience_note?: string;
  occupation_note?: string;
  job_offer_exception?: string;
  priority_sectors?: string[];
  targeted_sectors?: {
    id: string;
    label: string;
    last_invited: string;
    invitations: number | null;
    min_score: number | null;
  }[];
  general_route_note?: string;
  min_points_sinp_grid?: number;
  source_url?: string;
}

interface RawProvince {
  code: string;
  name: string;
  program: string;
  verification_status: string;
  program_note?: string;
  source_url: string;
  sector_caps_2026?: { sector: string; share: number; nominations: number }[];
  streams: RawStream[];
}

function clbFloor(stream: RawStream, teer: number | null): number | null {
  const groups = stream.min_clb_by_group;
  if (!groups) return null;
  if (teer === null) return groups.teer_0_3 ?? null;
  return teer >= 4 ? (groups.teer_4_5 ?? null) : (groups.teer_0_3 ?? null);
}

function matchStream(stream: RawStream, input: ProvinceInput, sectors: Set<string>): StreamMatch {
  const reasons: string[] = [];
  const blockers: string[] = [];
  let fit: Fit = "possible";

  // TEER gate — the hardest one, because no amount of points moves it.
  if (stream.teer_eligible && input.teer !== null && !stream.teer_eligible.includes(input.teer)) {
    blockers.push(
      `Open to TEER ${stream.teer_eligible.join(", ")}; your main occupation is TEER ${input.teer}.`
    );
    fit = "blocked";
  }

  // Language floor.
  const floor = clbFloor(stream, input.teer);
  if (floor !== null) {
    if (input.minClb >= floor) {
      reasons.push(`Your CLB ${input.minClb} clears the CLB ${floor} floor.`);
    } else {
      blockers.push(`Needs CLB ${floor} in all four abilities; your lowest is CLB ${input.minClb}.`);
      if (fit !== "blocked") fit = "conditional";
    }
  }

  // Sector targeting — the difference between "eligible" and "actually invited".
  if (stream.targeted_sectors?.length) {
    const hit = stream.targeted_sectors.find((s) => sectors.has(s.id));
    if (hit) {
      const score = hit.min_score !== null ? `, minimum score ${hit.min_score}` : "";
      reasons.push(
        `Your occupation falls in "${hit.label}", which was invited on ${hit.last_invited}${score}.`
      );
      if (fit === "possible") fit = "strong";
    } else if (fit !== "blocked") {
      blockers.push(
        "Your occupation is outside the sectors currently being invited " +
          `(${stream.targeted_sectors.map((s) => s.label).join(", ")}).` +
          (stream.general_route_note ? ` ${stream.general_route_note}` : "")
      );
      fit = "conditional";
    }
  }

  if (stream.priority_sectors?.length) {
    const hit = stream.priority_sectors.find((s) =>
      sectors.has(s.replace(/\s+/g, "").replace("healthcare", "health"))
    );
    if (hit) {
      reasons.push(`${hit} is a named priority pathway here.`);
      if (fit === "possible") fit = "strong";
    }
  }

  if (stream.requires_job_offer) {
    blockers.push(
      "Requires a job offer" +
        (stream.job_offer_exception ? `. Exception: ${stream.job_offer_exception}` : ".")
    );
    if (fit === "strong") fit = "conditional";
    else if (fit === "possible") fit = "conditional";
  } else {
    reasons.push("No job offer required.");
    if (fit === "possible") fit = "strong";
  }

  if (stream.express_entry_aligned) {
    reasons.push("Enhanced stream — a nomination adds 600 CRS points to your Express Entry profile.");
  } else if (stream.ee_note) {
    reasons.push(stream.ee_note);
  }

  if (input.currentProvince && stream.min_experience_note) {
    reasons.push(stream.min_experience_note);
  }
  if (stream.occupation_note) reasons.push(stream.occupation_note);
  if (stream.min_points_sinp_grid) {
    reasons.push(`Requires at least ${stream.min_points_sinp_grid} points on the province's own grid.`);
  }
  if (stream.min_education) reasons.push(stream.min_education);

  return {
    id: stream.id,
    label: stream.label,
    fit,
    expressEntryAligned: stream.express_entry_aligned,
    requiresJobOffer: stream.requires_job_offer,
    reasons,
    blockers,
    sourceUrl: stream.source_url ?? "",
  };
}

export interface ProvincialOutlook {
  matches: ProvinceMatch[];
  /** Provinces operating a PNP whose streams we have not verified. Named, not scored. */
  unverified: { code: string; name: string; program: string; sourceUrl: string }[];
  nationalContext: typeof data.national_context;
  lastVerified: string;
  disclaimer: string;
}

export function provincialOutlook(input: ProvinceInput): ProvincialOutlook {
  const sectors = sectorsFor(input.noc);
  const matches: ProvinceMatch[] = [];
  const unverified: ProvincialOutlook["unverified"] = [];

  for (const raw of data.provinces as RawProvince[]) {
    if (raw.verification_status !== "verified") {
      unverified.push({
        code: raw.code,
        name: raw.name,
        program: raw.program,
        sourceUrl: raw.source_url,
      });
      continue;
    }

    const streams = raw.streams.map((s) => matchStream(s, input, sectors));
    streams.sort((a, b) => FIT_RANK[a.fit] - FIT_RANK[b.fit]);

    matches.push({
      code: raw.code,
      name: raw.name,
      program: raw.program,
      verified: true,
      programNote: raw.program_note ?? null,
      sourceUrl: raw.source_url,
      fit: streams.length ? streams[0].fit : "blocked",
      streams,
    });
  }

  // Rank by best available route, then put the province they already live in first
  // among equals — local experience and employer contact are real advantages.
  matches.sort((a, b) => {
    const byFit = FIT_RANK[a.fit] - FIT_RANK[b.fit];
    if (byFit !== 0) return byFit;
    if (a.code === input.currentProvince) return -1;
    if (b.code === input.currentProvince) return 1;
    return a.name.localeCompare(b.name);
  });

  return {
    matches,
    unverified,
    nationalContext: data.national_context,
    lastVerified: data.last_verified,
    disclaimer: data.disclaimer,
  };
}
