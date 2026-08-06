import { Link, redirect } from "@/i18n/routing";
import { EDUCATION_LABELS, type EducationLevel } from "@/lib/crs/grid";
import { createClient } from "@/lib/supabase/server";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const dynamic = "force-dynamic";

/**
 * Profile summary.
 *
 * This page was a static stub — a heading and one line of text — while the sidebar
 * linked to it from every authenticated page and the dashboard offered a button
 * labelled "Edit profile". That is a broken promise rather than a missing feature:
 * the data it names is genuinely editable, just via the onboarding steps, which are
 * all revisitable and hydrate their saved values. This shows what is on file and
 * routes each section to the screen that already edits it, rather than duplicating
 * those forms.
 */

function formatDate(value: unknown): string | null {
  if (!value) return null;
  const date = new Date(`${String(value).slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("en-CA", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border/60 py-2 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value ?? <span className="text-muted-foreground">Not set</span>}</span>
    </div>
  );
}

function SectionCard({
  title,
  description,
  editHref,
  editLabel,
  children,
}: {
  title: string;
  description: string;
  editHref: string;
  editLabel: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
        <div>
          <CardTitle className="text-base">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
        <Button asChild variant="outline" size="sm" className="shrink-0">
          <Link href={editHref}>{editLabel}</Link>
        </Button>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export default async function ProfilePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const [{ data: profileRow }, { data: workHistory }] = await Promise.all([
    supabase.from("profiles").select("*").eq("id", user.id).single(),
    supabase
      .from("work_history")
      .select("title, employer, country, start_date, end_date, is_current, mapped_noc_code, mapped_teer")
      .eq("user_id", user.id)
      .order("sort_order"),
  ]);

  const profile = (profileRow ?? {}) as Record<string, unknown>;
  const roles = workHistory ?? [];
  const unmappedRoles = roles.filter((r) => !r.mapped_noc_code).length;

  const educationLevel = profile.education_level as EducationLevel | null;
  const clb = [
    profile.clb_en_reading,
    profile.clb_en_writing,
    profile.clb_en_listening,
    profile.clb_en_speaking,
  ];
  const hasClb = clb.some((v) => typeof v === "number" && v > 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Profile</h1>
        <p className="text-muted-foreground">
          Everything your CRS score and job matches are calculated from.
        </p>
      </div>

      <SectionCard
        title="Work history"
        description="Dates drive your Canadian experience points and CEC eligibility."
        editHref="/onboarding/work-history"
        editLabel="Edit"
      >
        {roles.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No roles added yet. Without work history your CRS score counts zero Canadian
            experience — worth up to 80 points.
          </p>
        ) : (
          <ul className="space-y-2">
            {roles.map((role, i) => (
              <li key={i} className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
                <span>
                  <span className="font-medium">{role.title}</span>
                  {role.employer && <span className="text-muted-foreground"> · {role.employer}</span>}
                </span>
                <span className="text-xs text-muted-foreground">
                  {role.mapped_noc_code ? `NOC ${role.mapped_noc_code}` : "NOC not mapped"}
                  {role.is_current ? " · current" : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard
        title="NOC mapping"
        description="Your occupation codes decide which category-based rounds you qualify for."
        editHref="/onboarding/noc-mapping"
        editLabel="Edit"
      >
        {roles.length === 0 ? (
          <p className="text-sm text-muted-foreground">Add work history first.</p>
        ) : unmappedRoles > 0 ? (
          <p className="text-sm text-muted-foreground">
            {unmappedRoles} of {roles.length} role{roles.length === 1 ? "" : "s"} still unmapped.
            Unmapped roles do not count toward category eligibility.
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">
            All {roles.length} role{roles.length === 1 ? "" : "s"} mapped to a NOC code.
          </p>
        )}
      </SectionCard>

      <SectionCard
        title="Status in Canada"
        description="Drives work-authorization filtering and your permit runway."
        editHref="/onboarding/permit-status"
        editLabel="Edit"
      >
        <Row
          label="Immigration status"
          value={profile.status ? String(profile.status).replace(/_/g, " ") : null}
        />
        <Row label="Permit expiry" value={formatDate(profile.permit_expiry)} />
        <Row label="Province" value={(profile.province as string) ?? null} />
      </SectionCard>

      <SectionCard
        title="CRS details"
        description="Age, education and language scores — the largest factors in your score."
        editHref="/onboarding/languages"
        editLabel="Edit"
      >
        <Row label="Date of birth" value={formatDate(profile.date_of_birth)} />
        <Row
          label="Highest education"
          value={educationLevel ? EDUCATION_LABELS[educationLevel] ?? educationLevel : null}
        />
        <Row
          label="English (CLB)"
          value={hasClb ? clb.map((v) => (typeof v === "number" ? v : 0)).join(" / ") : null}
        />
        <Row
          label="CRS profile"
          value={
            profile.crs_profile_completed ? (
              <Badge>Complete</Badge>
            ) : (
              <Badge variant="outline">Incomplete</Badge>
            )
          }
        />
      </SectionCard>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Your report</CardTitle>
          <CardDescription>
            Your CRS score against the Express Entry rounds actually being held.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild variant="outline" size="sm">
            <Link href="/pathways">View PR pathway report</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
