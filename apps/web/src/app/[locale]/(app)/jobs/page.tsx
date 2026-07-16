import { redirect } from "@/i18n/routing";
import { JobsFeed } from "@/components/jobs/jobs-feed";
import { MATCH_SELECT, mapMatchRows } from "@/lib/map-match-rows";
import { createClient } from "@/lib/supabase/server";

export default async function JobsPage() {
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

  if (!profile?.onboarding_completed) redirect("/onboarding");

  const { data: matchRows } = await supabase
    .from("matches")
    .select(MATCH_SELECT)
    .eq("user_id", user.id)
    .eq("status", "new")
    .gte("match_score", profile.match_score_threshold ?? 65)
    .order("match_score", { ascending: false })
    .limit(50);

  const matches = mapMatchRows(matchRows);

  return <JobsFeed initialMatches={matches} />;
}
