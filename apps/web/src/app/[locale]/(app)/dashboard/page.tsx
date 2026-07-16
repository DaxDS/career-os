import Link from "next/link";
import { redirect } from "@/i18n/routing";
import { getTranslations } from "next-intl/server";
import { ActivityTimeline } from "@/components/activity/activity-timeline";
import {
  DashboardPathwayPreview,
  DashboardTopMatches,
} from "@/components/dashboard/dashboard-preview";
import type { PathwayReportData } from "@/components/pathways/pathway-report";
import { MATCH_SELECT, mapMatchRows } from "@/lib/map-match-rows";
import { createClient } from "@/lib/supabase/server";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default async function DashboardPage() {
  const t = await getTranslations("dashboard");
  const ta = await getTranslations("activity");
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const { data: profile } = await supabase
    .from("profiles")
    .select("onboarding_completed, match_score_threshold")
    .eq("id", user.id)
    .single();

  if (!profile?.onboarding_completed) {
    redirect("/onboarding");
  }

  const threshold = profile.match_score_threshold ?? 65;

  const { count: matchCount } = await supabase
    .from("matches")
    .select("*", { count: "exact", head: true })
    .eq("user_id", user.id)
    .gte("match_score", threshold);

  const { count: queueCount } = await supabase
    .from("applications")
    .select("*", { count: "exact", head: true })
    .eq("user_id", user.id)
    .eq("status", "pending_review");

  const { count: sentCount } = await supabase
    .from("applications")
    .select("*", { count: "exact", head: true })
    .eq("user_id", user.id)
    .eq("status", "sent");

  const { data: matchRows } = await supabase
    .from("matches")
    .select(MATCH_SELECT)
    .eq("user_id", user.id)
    .eq("status", "new")
    .gte("match_score", threshold)
    .order("match_score", { ascending: false })
    .limit(5);

  const topMatches = mapMatchRows(matchRows);

  const { data: pathwayRow } = await supabase
    .from("pathway_reports")
    .select("report_json")
    .eq("user_id", user.id)
    .order("generated_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const pathwayReport = (pathwayRow?.report_json ?? null) as PathwayReportData | null;

  const { data: recentActivity } = await supabase
    .from("activity_log")
    .select("id, action, summary, metadata, created_at")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(5);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t("title")}</h1>
        <p className="text-sm text-muted-foreground sm:text-base">{t("subtitle")}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("matchedJobs")}</CardTitle>
            <CardDescription>{t("matchedJobsHint")}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{matchCount ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("reviewQueue")}</CardTitle>
            <CardDescription>{t("reviewQueueHint")}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{queueCount ?? 0}</p>
          </CardContent>
        </Card>
        <Card className="sm:col-span-2 md:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">{t("applicationsSent")}</CardTitle>
            <CardDescription>{t("applicationsSentHint")}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{sentCount ?? 0}</p>
          </CardContent>
        </Card>
      </div>

      <DashboardTopMatches
        matches={topMatches}
        title={t("topMatchesTitle")}
        description={t("topMatchesDescription")}
        viewAllLabel={t("browseJobs")}
      />

      <DashboardPathwayPreview report={pathwayReport} />

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
          <div>
            <CardTitle className="text-base">{ta("recentTitle")}</CardTitle>
            <CardDescription>{ta("recentDescription")}</CardDescription>
          </div>
          <Button asChild variant="outline" size="sm" className="shrink-0">
            <Link href="/activity">{ta("viewAll")}</Link>
          </Button>
        </CardHeader>
        <CardContent>
          <ActivityTimeline entries={recentActivity || []} compact />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("quickLinks")}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button asChild variant="outline" size="sm">
            <Link href="/jobs">{t("browseJobs")}</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/pathways">{t("pathwayReport")}</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/profile">{t("editProfile")}</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
