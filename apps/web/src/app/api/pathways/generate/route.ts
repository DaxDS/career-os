import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { archiveReport, buildPathwayReport } from "@/lib/crs/build";

export const runtime = "nodejs";

/**
 * Generate and archive a PR pathway report.
 *
 * The report is computed in-process. /pathways renders it directly rather than reading
 * back what this route wrote, so a failed archive degrades to "no history" instead of
 * "no report".
 */
export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { report, error } = await buildPathwayReport(supabase, user.id);
  if (error || !report) {
    return NextResponse.json({ error: error ?? "Could not build report" }, { status: 400 });
  }

  const archiveError = await archiveReport(createAdminClient(), user.id, report);

  return NextResponse.json({ ...report, archived: archiveError === null, archive_error: archiveError });
}
