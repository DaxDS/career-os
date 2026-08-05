import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { logActivity } from "@/lib/activity-log";

export const runtime = "nodejs";

/**
 * Mark an approved application as submitted by the user.
 *
 * This route used to hand off to a Playwright worker that filled in and submitted the
 * employer's form. That cannot run here — serverless functions have no browser — and
 * the worker was never deployed, so every call returned 503.
 *
 * Rather than fake it, the flow is honest: the tailored documents are ready, the user
 * applies on the employer's site, and we record that it happened. Nothing is submitted
 * on anyone's behalf.
 */
export async function POST(_request: Request, { params }: { params: { id: string } }) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { data: application, error: loadError } = await supabase
    .from("applications")
    .select("id, status, job_id, jobs(url, title, company)")
    .eq("id", params.id)
    .eq("user_id", user.id)
    .single();

  if (loadError || !application) {
    return NextResponse.json({ error: "Application not found" }, { status: 404 });
  }

  const { error: updateError } = await supabase
    .from("applications")
    .update({ status: "sent", updated_at: new Date().toISOString() })
    .eq("id", params.id)
    .eq("user_id", user.id);

  if (updateError) {
    return NextResponse.json({ error: updateError.message }, { status: 500 });
  }

  const job = (application as { jobs?: { url?: string; title?: string; company?: string } }).jobs;

  await logActivity(
    user.id,
    "application_marked_sent",
    job?.title
      ? `Marked as applied: ${job.title}${job.company ? ` at ${job.company}` : ""}`
      : "Marked an application as applied",
    { application_id: params.id, job_url: job?.url ?? null }
  );

  return NextResponse.json({
    status: "recorded",
    job_url: job?.url ?? null,
    message:
      "Marked as applied. CareerOS does not submit applications for you — open the posting, " +
      "attach your tailored documents, and apply directly.",
  });
}
