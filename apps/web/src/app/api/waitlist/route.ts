import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_EMAIL_LEN = 254;

function isValidEmail(raw: string): boolean {
  const email = raw.trim().toLowerCase();
  return email.length > 0 && email.length <= MAX_EMAIL_LEN && EMAIL_RE.test(email);
}

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }

  if (!body || typeof body !== "object") {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }

  const { email, province, source, website } = body as Record<string, unknown>;

  // Honeypot — bots fill hidden fields; reject silently with generic 400
  if (typeof website === "string" && website.trim().length > 0) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }

  if (!email || typeof email !== "string" || !isValidEmail(email)) {
    return NextResponse.json({ error: "Valid email required" }, { status: 400 });
  }

  const normalizedEmail = email.trim().toLowerCase();
  const provinceValue =
    typeof province === "string" && province.trim().length > 0 ? province.trim() : null;
  const sourceValue = typeof source === "string" && source.trim().length > 0 ? source.trim() : "landing";

  const supabase = await createClient();
  const { error } = await supabase.from("waitlist").insert({
    email: normalizedEmail,
    province: provinceValue,
    source: sourceValue,
  });

  if (error && error.code !== "23505") {
    return NextResponse.json({ error: "Unable to join waitlist" }, { status: 500 });
  }

  // Same response for new signups and duplicates — do not leak enrollment status
  return NextResponse.json({ ok: true });
}
