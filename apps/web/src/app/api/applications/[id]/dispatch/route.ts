import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function POST(
  _request: Request,
  { params }: { params: { id: string } }
) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const agentUrl = process.env.AGENT_SERVICE_URL || "http://localhost:8000";
  const agentSecret = process.env.AGENT_API_SECRET || "";

  try {
    const response = await fetch(`${agentUrl}/graphs/dispatch`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(agentSecret ? { "X-Agent-Secret": agentSecret } : {}),
      },
      body: JSON.stringify({ user_id: user.id, application_id: params.id }),
    });
    const payload = await response.json();
    if (!response.ok) {
      return NextResponse.json({ error: payload.detail || "Dispatch failed" }, { status: response.status });
    }
    return NextResponse.json(payload.result);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Agent unavailable" },
      { status: 503 }
    );
  }
}
