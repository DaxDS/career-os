import type { BaseResume } from "@/lib/tailoring/resume-types";

type WorkRow = {
  title: string;
  employer: string | null;
  country?: string | null;
  province?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_current?: boolean | null;
  duties_text: string | null;
  mapped_noc_code?: string | null;
  sort_order: number;
};

type ProfileRow = {
  full_name: string | null;
  status: string | null;
  city: string | null;
  province: string | null;
};

function bulletsFromDuties(duties: string | null, title: string, employer: string): string[] {
  if (duties?.trim()) {
    const lines = duties
      .split(/[\n;]+/)
      .map((line) => line.trim().replace(/^[•\-]\s*/, ""))
      .filter((line) => line.length > 8);
    if (lines.length) return lines.slice(0, 6);
    const sentences = duties
      .split(/\.+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 12);
    if (sentences.length) return sentences.slice(0, 6);
  }
  return [`${title} at ${employer}.`];
}

function formatDates(start?: string | null, end?: string | null, isCurrent?: boolean | null): string {
  const startLabel = start || "";
  const endLabel = isCurrent ? "Present" : end || "";
  if (startLabel && endLabel) return `${startLabel} – ${endLabel}`;
  return startLabel || endLabel;
}

export function buildBaseResume(profile: ProfileRow, workHistory: WorkRow[]): BaseResume {
  const name = profile.full_name || "Applicant";
  const experience =
    workHistory.length > 0
      ? workHistory.map((row) => {
          const employer = row.employer || "Employer";
          const location = [row.province, row.country].filter(Boolean).join(", ");
          return {
            title: row.title,
            employer,
            dates: formatDates(row.start_date, row.end_date, row.is_current),
            location,
            bullets: bulletsFromDuties(row.duties_text, row.title, employer),
          };
        })
      : [
          {
            title: "Software Developer",
            employer: "Canadian employer",
            dates: "",
            location: [profile.city, profile.province].filter(Boolean).join(", "),
            bullets: [
              "Built and maintained web applications using modern JavaScript frameworks.",
              "Collaborated with product and QA on releases for Canadian users.",
            ],
          },
        ];

  const skills = workHistory
    .map((row) => row.mapped_noc_code)
    .filter(Boolean)
    .map((noc) => `NOC ${noc}`);

  return {
    full_name: name,
    contact: {
      city: profile.city || "",
      province: profile.province || "",
    },
    summary: "",
    experience,
    skills: skills.length ? Array.from(new Set(skills)) : undefined,
  };
}
