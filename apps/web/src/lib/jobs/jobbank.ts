/**
 * Government of Canada Job Bank search.
 *
 * Chosen as the discovery source because it needs no API key and no credentials —
 * Adzuna and JSearch both do, which would have made the jobs feed undeployable today.
 *
 * The markup patterns here are corrected against the live site as of 2026-08-04. The
 * previous Python versions targeted a `job-posting-details-sidebar` sibling and a
 * `NOC 2021: 12345` string, neither of which exists any more — descriptions came back
 * empty and every NOC was null, which silently disabled all category scoring.
 */

const BASE = "https://www.jobbank.gc.ca";
const USER_AGENT =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 CareerOS/1.0";

export interface RawJobListing {
  source: string;
  externalId: string;
  url: string;
  title: string;
  company: string;
  city: string;
  province: string;
  description: string;
  nocCode: string | null;
}

async function fetchText(url: string, timeoutMs = 12_000): Promise<string | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      headers: {
        "User-Agent": USER_AGENT,
        Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en;q=0.9",
      },
      signal: controller.signal,
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

function decodeEntities(text: string): string {
  return text
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#(\d+);/g, (_, d) => String.fromCharCode(Number(d)))
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCharCode(parseInt(h, 16)));
}

function stripTags(html: string): string {
  return decodeEntities(
    html
      .replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/gi, " ")
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/p>/gi, "\n")
      .replace(/<[^>]+>/g, " ")
  )
    .replace(/\s+/g, " ")
    .trim();
}

function parseLocation(raw: string): { city: string; province: string } {
  const cleaned = decodeEntities(raw).trim();
  const match = cleaned.match(/^(.*?)[\s,]*\(?([A-Z]{2})\)?$/);
  if (match) return { city: match[1].replace(/,\s*$/, "").trim(), province: match[2] };
  return { city: cleaned, province: "" };
}

function extractNoc(html: string): string | null {
  // Live markup exposes the code as `noccode">21232`.
  const direct = html.match(/noccode"?>\s*(\d{5})/i);
  if (direct) return direct[1];
  const labelled = html.match(/NOC\s*(?:2021)?[:\s]*(\d{5})/i);
  return labelled ? labelled[1] : null;
}

function extractDescription(html: string): string {
  const body = html.match(
    /<div class="job-posting-details-body[^"]*">([\s\S]*?)<div class="job-posting-details-menu/i
  );
  if (body) {
    const text = stripTags(body[1]);
    if (text.length >= 40) return text.slice(0, 8000);
  }
  const requirements = html.match(
    /<div class="[^"]*job-posting-detail-requirements[^"]*">([\s\S]*?)<\/div>\s*<div/i
  );
  if (requirements) {
    const text = stripTags(requirements[1]);
    if (text.length >= 40) return text.slice(0, 8000);
  }
  return "";
}

/** Fetch detail page for description and NOC. Failure degrades to empty, never throws. */
async function fetchDetail(jobId: string): Promise<{ description: string; nocCode: string | null }> {
  const html = await fetchText(`${BASE}/jobsearch/jobposting/${jobId}`);
  if (!html) return { description: "", nocCode: null };
  return { description: extractDescription(html), nocCode: extractNoc(html) };
}

async function mapWithConcurrency<T, R>(
  items: T[],
  limit: number,
  fn: (item: T) => Promise<R>
): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let cursor = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (cursor < items.length) {
      const index = cursor++;
      results[index] = await fn(items[index]);
    }
  });
  await Promise.all(workers);
  return results;
}

export async function searchJobBank(
  keywords: string[],
  location = "Canada",
  maxResults = 12
): Promise<RawJobListing[]> {
  const seen = new Set<string>();
  const listings: Array<Omit<RawJobListing, "description" | "nocCode">> = [];

  for (const keyword of keywords) {
    if (listings.length >= maxResults) break;

    const params = new URLSearchParams({
      searchstring: keyword,
      locationstring: location || "Canada",
    });
    const html = await fetchText(`${BASE}/jobsearch/jobsearch?${params.toString()}`);
    if (!html) continue;

    // Array.from rather than iterating the matchAll iterator directly: the tsconfig
    // target predates iterator downleveling.
    const articles = Array.from(
      html.matchAll(/<article[^>]*id="article-(\d+)"[^>]*>([\s\S]*?)<\/article>/gi)
    );
    for (const [, jobId, block] of articles) {
      if (listings.length >= maxResults || seen.has(jobId)) continue;

      const titleMatch = block.match(/<span class="noctitle">\s*([\s\S]*?)\s*<\/span>/i);
      if (!titleMatch) continue;

      const companyMatch = block.match(/<li class="business">([\s\S]*?)<\/li>/i);
      const locationMatch = block.match(
        /<li class="location">[\s\S]*?<span class="wb-inv">Location<\/span>\s*([\s\S]*?)\s*<\/li>/i
      );

      const { city, province } = parseLocation(locationMatch ? stripTags(locationMatch[1]) : "");
      seen.add(jobId);
      listings.push({
        source: "job_bank",
        externalId: jobId,
        url: `${BASE}/jobsearch/jobposting/${jobId}`,
        title: stripTags(titleMatch[1]),
        company: companyMatch ? stripTags(companyMatch[1]) : "Unknown",
        city,
        province,
      });
    }
  }

  // Detail pages are fetched with bounded concurrency: sequential fetches with a
  // politeness delay would blow a serverless timeout well before finishing.
  const details = await mapWithConcurrency(listings, 4, (l) => fetchDetail(l.externalId));

  return listings.map((listing, i) => ({
    ...listing,
    description: details[i].description,
    nocCode: details[i].nocCode,
  }));
}
