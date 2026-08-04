import { redirect } from "@/i18n/routing";
import { CrsProfileForm } from "@/components/pathways/crs-profile-form";
import { PathwayReportView, type PathwayReportData } from "@/components/pathways/pathway-report";
import { buildPathwayReport } from "@/lib/crs/build";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function PathwaysPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: profileRow } = await supabase.from("profiles").select("*").eq("id", user.id).single();
  const profile = (profileRow ?? {}) as Record<string, unknown>;
  const completed = Boolean(profile.crs_profile_completed);

  // Computed on every load rather than read back from pathway_reports. The score is
  // pure computation over the profile, so making it depend on a prior successful write
  // is what previously left a fully-filled profile staring at "No pathway report yet."
  let report: PathwayReportData | null = null;
  let buildError: string | null = null;
  if (completed) {
    const built = await buildPathwayReport(supabase, user.id);
    report = (built.report as PathwayReportData | null) ?? null;
    buildError = built.error;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Your PR pathway report</h1>
        <p className="text-muted-foreground">
          Your CRS score against the Express Entry rounds actually being held — and what would move it.
        </p>
      </div>

      <CrsProfileForm initial={profile as never} completed={completed} />

      {!completed && (
        <p className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
          Fill in the details above to see your score, the routes open to you, and your gap to each.
        </p>
      )}

      {completed && buildError && (
        <p className="rounded-xl border border-destructive/40 bg-destructive/10 p-6 text-sm text-destructive">
          {buildError}
        </p>
      )}

      {completed && report && <PathwayReportView report={report} />}
    </div>
  );
}
