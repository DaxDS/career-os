import { NextResponse } from "next/server";

import { monthStartIso, normalizePlan, tailoringLimitResponse } from "@/lib/billing/plan-limits";

import { createClient } from "@/lib/supabase/server";

import { prepareApplicationLocally, shouldCallAgentService } from "@/lib/tailoring/local-prepare";



const AGENT_TIMEOUT_MS = 12_000;



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

    signal: AbortSignal.timeout(AGENT_TIMEOUT_MS),

  });

  const payload = await response.json();

  return { response, payload };

}



export async function POST(request: Request) {

  const supabase = await createClient();

  const {

    data: { user },

  } = await supabase.auth.getUser();

  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });



  const { match_id } = await request.json();

  if (!match_id) return NextResponse.json({ error: "match_id required" }, { status: 400 });



  const { data: profile } = await supabase

    .from("profiles")

    .select("plan")

    .eq("id", user.id)

    .single();



  const plan = normalizePlan(profile?.plan);



  const { count: tailoredUsed } = await supabase

    .from("applications")

    .select("*", { count: "exact", head: true })

    .eq("user_id", user.id)

    .gte("created_at", monthStartIso());



  const limitCheck = tailoringLimitResponse(plan, tailoredUsed ?? 0);

  if (!limitCheck.allowed) {

    return NextResponse.json(

      {

        error: limitCheck.message,

        code: "PLAN_LIMIT",

        used: limitCheck.used,

        limit: limitCheck.limit,

        upgrade_url: "/settings",

      },

      { status: 402 }

    );

  }



  if (shouldCallAgentService()) {

    try {

      const { response, payload } = await agentPost("/graphs/tailoring", {

        user_id: user.id,

        match_id,

      });

      if (response.ok) {

        return NextResponse.json(payload.result);

      }

    } catch {

      /* fall through to local tailoring */

    }

  }



  try {

    const result = await prepareApplicationLocally(supabase, user.id, match_id);

    return NextResponse.json(result);

  } catch (error) {

    return NextResponse.json(

      { error: error instanceof Error ? error.message : "Tailoring failed" },

      { status: 503 }

    );

  }

}

