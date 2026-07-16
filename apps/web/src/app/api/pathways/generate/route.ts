import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

async function agentPost(path: string, body: object) {
  const agentUrl = process.env.AGENT_SERVICE_URL || "http://localhost:8000";
  const agentSecret = process.env.AGENT_API_SECRET || "";
  const response = await fetch(`${agentUrl}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(agentSecret ? { "X-Agent-Secret": agentSecret } : {}),
    },
    body: JSON.stringify(body),
  });
  return { response, payload: await response.json() };
}

export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  try {
    const { response, payload } = await agentPost("/graphs/pathway-report", { user_id: user.id });
    if (!response.ok) {
      return NextResponse.json({ error: payload.detail || "Failed" }, { status: response.status });
    }
    return NextResponse.json(payload.result);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Agent unavailable" },
      { status: 503 }
    );
  }
}
