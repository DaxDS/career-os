import { createAdminClient } from "@/lib/supabase/admin";

/**
 * Write an entry to the user's activity timeline.
 *
 * Best-effort by design: the timeline is a record of what happened, so a failure to
 * write one must never fail the operation it is describing. Errors are logged
 * server-side and swallowed.
 *
 * Uses the service-role client because activity_log has no INSERT policy for end
 * users — entries are written on their behalf, never by them directly.
 */
export async function logActivity(
  userId: string,
  action: string,
  summary: string,
  metadata: Record<string, unknown> = {}
): Promise<void> {
  try {
    const admin = createAdminClient();
    const { error } = await admin.from("activity_log").insert({
      user_id: userId,
      action,
      summary,
      metadata,
    });
    if (error) {
      console.error("[activity-log] insert failed:", action, error.message);
    }
  } catch (thrown) {
    console.error("[activity-log] threw:", action, thrown instanceof Error ? thrown.message : thrown);
  }
}
