import { redirect } from "@/i18n/routing";
import { ApplicationTracker, type TrackerApplication } from "@/components/tracker/application-tracker";
import { createClient } from "@/lib/supabase/server";

export default async function TrackerPage() {
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
      status,
      sent_at,
      cover_letter_text,
      submission_method,
      matches ( jobs ( title, company, url ) )
    `
    )
    .eq("user_id", user.id)
    .in("status", ["approved", "sent", "response", "interview", "offer", "rejected"])
    .order("updated_at", { ascending: false });

  const applications: TrackerApplication[] = (rows || [])
    .filter((r) => r.matches && !Array.isArray(r.matches))
    .map((r) => ({
      id: r.id,
      status: r.status,
      sent_at: r.sent_at,
      cover_letter_text: r.cover_letter_text,
      submission_method: r.submission_method,
      match: r.matches as unknown as TrackerApplication["match"],
    }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Application tracker</h1>
        <p className="text-muted-foreground">
          Approved applications open the employer apply link — you submit manually (daily cap enforced).
        </p>
      </div>
      <ApplicationTracker applications={applications} />
    </div>
  );
}
