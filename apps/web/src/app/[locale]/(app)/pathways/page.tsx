import { redirect } from "@/i18n/routing";
import { CrsProfileForm } from "@/components/pathways/crs-profile-form";
import { PathwayReportView, type PathwayReportData } from "@/components/pathways/pathway-report";
import { createClient } from "@/lib/supabase/server";

export default async function PathwaysPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const [profileResult, { data: reports }] = await Promise.all([
    supabase.from("profiles").select("*").eq("id", user.id).single(),
    supabase
      .from("pathway_reports")
      .select("report_json, generated_at")
      .eq("user_id", user.id)
      .order("generated_at", { ascending: false })
      .limit(1),
  ]);

  const profile = (profileResult.data ?? {}) as Record<string, unknown>;
  const report = (reports?.[0]?.report_json as PathwayReportData | undefined) ?? null;
  const completed = Boolean(profile.crs_profile_completed);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Your PR pathway report</h1>
        <p className="text-muted-foreground">
          Your CRS score against the Express Entry rounds actually being held — and what would move it.
        </p>
      </div>

      <CrsProfileForm initial={profile as never} completed={completed} />

      {/* Until the CRS inputs exist, a report would score near zero and read as
          authoritative. Better to show nothing than a confidently wrong number. */}
      {completed ? (
        <PathwayReportView report={report} />
      ) : (
        <p className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
          Fill in the details above to see your score, the routes open to you, and your gap to each.
        </p>
      )}
    </div>
  );
}
