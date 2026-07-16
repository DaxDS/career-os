import { redirect } from "@/i18n/routing";
import { ReviewQueue, type ReviewApplication } from "@/components/queue/review-queue";
import { createClient } from "@/lib/supabase/server";

export default async function QueuePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: rows } = await supabase
    .from("applications")
    .select(
      `
      id,
      match_id,
      status,
      cover_letter_text,
      tailored_resume_json,
      matches (
        match_score,
        jobs ( title, company, url )
      )
    `
    )
    .eq("user_id", user.id)
    .eq("status", "pending_review")
    .order("created_at", { ascending: false });

  const applications: ReviewApplication[] = (rows || [])
    .filter((r) => r.matches && !Array.isArray(r.matches))
    .map((r) => ({
      id: r.id,
      match_id: r.match_id,
      status: r.status,
      cover_letter_text: r.cover_letter_text,
      tailored_resume_json: r.tailored_resume_json as ReviewApplication["tailored_resume_json"],
      match: r.matches as unknown as ReviewApplication["match"],
    }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Review queue</h1>
        <p className="text-muted-foreground">
          Nothing sends automatically. Approve, edit externally, or reject each application.
        </p>
      </div>
      <ReviewQueue applications={applications} />
    </div>
  );
}
