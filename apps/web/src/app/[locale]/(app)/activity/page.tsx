import { redirect } from "@/i18n/routing";
import { getTranslations } from "next-intl/server";
import {
  ActivityPagination,
  ActivityTimeline,
} from "@/components/activity/activity-timeline";
import { createClient } from "@/lib/supabase/server";

const PAGE_SIZE = 30;

export default async function ActivityPage({
  searchParams,
}: {
  searchParams: { page?: string };
}) {
  const t = await getTranslations("activity");
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const page = Math.max(1, parseInt(searchParams.page || "1", 10) || 1);
  const from = (page - 1) * PAGE_SIZE;
  const to = from + PAGE_SIZE - 1;

  const { data: entries, count } = await supabase
    .from("activity_log")
    .select("id, action, summary, metadata, created_at", { count: "exact" })
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .range(from, to);

  const totalPages = Math.max(1, Math.ceil((count ?? 0) / PAGE_SIZE));

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-1">
      <div>
        <h1 className="text-2xl font-bold">{t("title")}</h1>
        <p className="text-sm text-muted-foreground sm:text-base">{t("description")}</p>
      </div>
      <ActivityTimeline entries={entries || []} />
      <ActivityPagination page={page} totalPages={totalPages} />
    </div>
  );
}
