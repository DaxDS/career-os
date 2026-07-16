import { redirect } from "@/i18n/routing";
import { PathwayReportView, type PathwayReportData } from "@/components/pathways/pathway-report";
import { createClient } from "@/lib/supabase/server";

export default async function PathwaysPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: reports } = await supabase
    .from("pathway_reports")
    .select("report_json, generated_at")
    .eq("user_id", user.id)
    .order("generated_at", { ascending: false })
    .limit(1);

  const report = (reports?.[0]?.report_json as PathwayReportData | undefined) ?? null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Immigration pathway report</h1>
        <p className="text-muted-foreground">
          Situational analysis based on your profile, NOC-mapped experience, and published program criteria.
        </p>
      </div>
      <PathwayReportView report={report} />
    </div>
  );
}
