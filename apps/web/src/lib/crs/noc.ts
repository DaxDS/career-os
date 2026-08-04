import nocData from "./noc-data.json";

/**
 * NOC 2021 helpers.
 *
 * The bundled reference list covers only a sample of NOC 2021's ~500 unit groups, so a
 * picker alone would strand most users. Two things close the gap:
 *
 *  - TEER is derivable from any valid code. In NOC 2021 the second digit of the
 *    five-digit code *is* the TEER level, so a user who knows their code gets a correct
 *    TEER without needing the full table.
 *  - Users who know neither can search the official list, linked from the UI.
 */

export interface NocUnitGroup {
  code: string;
  title: string;
  teer: number;
  exampleTitles: string[];
}

export const NOC_UNIT_GROUPS = nocData.unitGroups as NocUnitGroup[];
export const NOC_SOURCE_URL =
  (nocData.sourceUrl as string) ||
  "https://noc.esdc.gc.ca/Structure/NocSearch";

/** A NOC 2021 unit group code is five digits. */
export function isValidNocCode(code: string): boolean {
  return /^\d{5}$/.test(code.trim());
}

/**
 * TEER level for a code, from the second digit.
 *
 * Prefers the bundled table when the code is known, so a data correction there wins
 * over the structural rule.
 */
export function teerFromNocCode(code: string): number | null {
  const trimmed = code.trim();
  if (!isValidNocCode(trimmed)) return null;

  const known = NOC_UNIT_GROUPS.find((g) => g.code === trimmed);
  if (known) return known.teer;

  const teer = Number(trimmed[1]);
  return teer >= 0 && teer <= 5 ? teer : null;
}

/** Case-insensitive search over titles and example titles. */
export function searchNoc(query: string, limit = 8): NocUnitGroup[] {
  const q = query.trim().toLowerCase();
  if (q.length < 2) return [];

  const scored: Array<{ group: NocUnitGroup; score: number }> = [];
  for (const group of NOC_UNIT_GROUPS) {
    const title = group.title.toLowerCase();
    const examples = group.exampleTitles.map((t) => t.toLowerCase());

    let score = 0;
    if (title === q) score = 100;
    else if (title.startsWith(q)) score = 80;
    else if (title.includes(q)) score = 60;
    else if (examples.some((t) => t === q)) score = 70;
    else if (examples.some((t) => t.startsWith(q))) score = 50;
    else if (examples.some((t) => t.includes(q))) score = 40;
    else if (group.code.startsWith(q)) score = 30;

    if (score > 0) scored.push({ group, score });
  }

  scored.sort((a, b) => b.score - a.score || a.group.code.localeCompare(b.group.code));
  return scored.slice(0, limit).map((s) => s.group);
}

export function nocLabel(code: string): string | null {
  return NOC_UNIT_GROUPS.find((g) => g.code === code.trim())?.title ?? null;
}
