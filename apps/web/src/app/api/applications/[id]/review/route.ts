import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { decision } = await request.json();
  if (!["approve", "reject"].includes(decision)) {
    return NextResponse.json({ error: "decision must be approve or reject" }, { status: 400 });
  }

  const app = await supabase
    .from("applications")
    .select("id, match_id, status")
    .eq("id", params.id)
    .eq("user_id", user.id)
    .single();

  if (app.error || !app.data) {
    return NextResponse.json({ error: "Application not found" }, { status: 404 });
  }

  const newStatus = decision === "approve" ? "approved" : "rejected";
  const matchStatus = decision === "approve" ? "approved" : "rejected";

  await supabase.from("applications").update({ status: newStatus }).eq("id", params.id);
  await supabase.from("matches").update({ status: matchStatus }).eq("id", app.data.match_id);

  const summary =
    decision === "approve"
      ? "You approved an application in the review queue"
      : "You rejected an application in the review queue";

  await supabase.from("activity_log").insert({
    user_id: user.id,
    action: `application_${decision}d`,
    summary,
    entity_type: "application",
    entity_id: params.id,
    metadata: { decision },
  });

  return NextResponse.json({ ok: true, status: newStatus });
}
