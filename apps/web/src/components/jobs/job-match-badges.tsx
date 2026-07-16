import type { PathwayFlags } from "@careeros/shared";
import { Badge } from "@/components/ui/badge";

export interface JobBadgeFields {
  noc_code: string | null;
  teer_level: number | null;
  noc_confidence?: number | null;
  wage_offered: number | null;
  wage_median_region: number | null;
  bilingual_required?: boolean;
  source?: string;
}

export function JobWageBadge({
  wage_offered,
  wage_median_region,
}: Pick<JobBadgeFields, "wage_offered" | "wage_median_region">) {
  if (wage_offered == null || wage_median_region == null) return null;
  const diff = wage_offered - wage_median_region;
  if (diff >= 2) {
    return (
      <Badge variant="success">
        ${diff.toFixed(0)}/hr above median
      </Badge>
    );
  }
  if (diff <= -2) {
    return (
      <Badge variant="warning">
        ${Math.abs(diff).toFixed(0)}/hr below median
      </Badge>
    );
  }
  return <Badge variant="outline">Near regional median</Badge>;
}

export function JobPathwayBadges({ flags }: { flags: PathwayFlags }) {
  const badges: React.ReactNode[] = [];
  if (flags.ee_eligible) badges.push(<Badge key="ee">EE TEER 0–3</Badge>);
  (flags.ee_categories || []).slice(0, 2).forEach((cat) =>
    badges.push(
      <Badge key={cat} variant="secondary">
        EE {cat.replace("_", " ")}
      </Badge>
    )
  );
  (flags.pnp_streams || []).slice(0, 2).forEach((stream) =>
    badges.push(
      <Badge key={stream} variant="outline">
        {stream.replace(/_/g, " ")}
      </Badge>
    )
  );
  if (flags.aip_relevant) badges.push(<Badge key="aip">AIP relevant</Badge>);
  return <>{badges}</>;
}

export function JobMatchBadges({
  job,
  pathway_flags,
}: {
  job: JobBadgeFields;
  pathway_flags: PathwayFlags;
}) {
  const nocLowConfidence = (job.noc_confidence ?? 1) < 0.7;

  return (
    <>
      {job.noc_code && (
        <Badge>
          NOC {job.noc_code}
          {nocLowConfidence && " · best guess"}
        </Badge>
      )}
      {job.teer_level != null && <Badge variant="secondary">TEER {job.teer_level}</Badge>}
      <JobWageBadge wage_offered={job.wage_offered} wage_median_region={job.wage_median_region} />
      {job.bilingual_required && <Badge variant="outline">French/bilingual</Badge>}
      <JobPathwayBadges flags={pathway_flags} />
      {job.source && <Badge variant="outline">{job.source.replace("_", " ")}</Badge>}
    </>
  );
}
