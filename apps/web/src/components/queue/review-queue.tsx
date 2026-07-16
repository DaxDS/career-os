"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface ReviewApplication {
  id: string;
  match_id: string;
  status: string;
  cover_letter_text: string | null;
  tailored_resume_json: {
    full_name?: string;
    summary?: string;
    experience?: Array<{ title: string; employer: string; bullets: string[] }>;
    _base_resume?: {
      experience?: Array<{ title: string; employer: string; bullets: string[] }>;
    };
    changes_made?: Array<{ section: string; reason: string }>;
  } | null;
  match: {
    match_score: number;
    jobs: {
      title: string;
      company: string | null;
      url: string;
    };
  };
}

function DiffColumn({
  title,
  experience,
}: {
  title: string;
  experience?: Array<{ title: string; employer: string; bullets: string[] }>;
}) {
  return (
    <div className="rounded-lg border p-4">
      <h3 className="mb-3 font-semibold">{title}</h3>
      {!experience?.length ? (
        <p className="text-sm text-muted-foreground">No experience entries</p>
      ) : (
        <div className="space-y-4">
          {experience.map((role, i) => (
            <div key={i}>
              <p className="font-medium text-sm">
                {role.title} · {role.employer}
              </p>
              <ul className="mt-1 list-inside list-disc text-sm text-muted-foreground">
                {(role.bullets || []).map((b, j) => (
                  <li key={j}>{b}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ReviewQueue({ applications }: { applications: ReviewApplication[] }) {
  const router = useRouter();
  const [selectedId, setSelectedId] = useState<string | null>(applications[0]?.id ?? null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const selected = applications.find((a) => a.id === selectedId);

  async function review(decision: "approve" | "reject") {
    if (!selected) return;
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch(`/api/applications/${selected.id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed");
      setMessage(decision === "approve" ? "Approved — ready to send from Tracker." : "Rejected.");
      router.refresh();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  if (applications.length === 0) {
    return (
      <div className="rounded-xl border border-dashed p-12 text-center">
        <p className="text-muted-foreground">No applications pending review.</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Prepare an application from the Jobs feed to see it here.
        </p>
      </div>
    );
  }

  const tailored = selected?.tailored_resume_json;
  const base = tailored?._base_resume;

  return (
    <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
      <div className="space-y-2">
        <h2 className="font-semibold">Pending ({applications.length})</h2>
        {applications.map((app) => (
          <button
            key={app.id}
            type="button"
            onClick={() => setSelectedId(app.id)}
            className={`w-full rounded-lg border p-3 text-left text-sm transition-colors ${
              selectedId === app.id ? "border-primary bg-primary/5" : "hover:bg-muted/50"
            }`}
          >
            <p className="font-medium">{app.match.jobs.title}</p>
            <p className="text-muted-foreground">{app.match.jobs.company}</p>
            <Badge variant="outline" className="mt-2">
              {Math.round(app.match.match_score)}% match
            </Badge>
          </button>
        ))}
      </div>

      {selected && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>
                {selected.match.jobs.title} · {selected.match.jobs.company}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <DiffColumn title="Base resume" experience={base?.experience} />
                <DiffColumn title="Tailored resume" experience={tailored?.experience} />
              </div>

              {tailored?.changes_made && tailored.changes_made.length > 0 && (
                <div className="rounded-md bg-muted/50 p-3 text-sm">
                  <p className="mb-2 font-medium">Changes made</p>
                  <ul className="list-inside list-disc space-y-1 text-muted-foreground">
                    {tailored.changes_made.map((c, i) => (
                      <li key={i}>{c.reason || c.section}</li>
                    ))}
                  </ul>
                </div>
              )}

              {selected.cover_letter_text && (
                <div className="rounded-lg border p-4">
                  <h3 className="mb-2 font-semibold">Cover letter</h3>
                  <p className="whitespace-pre-wrap text-sm text-muted-foreground">
                    {selected.cover_letter_text}
                  </p>
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                <Button onClick={() => review("approve")} disabled={loading}>
                  Approve
                </Button>
                <Button variant="outline" onClick={() => review("reject")} disabled={loading}>
                  Reject
                </Button>
                <Button variant="ghost" asChild>
                  <a href={selected.match.jobs.url} target="_blank" rel="noopener noreferrer">
                    View job posting
                  </a>
                </Button>
              </div>
              {message && <p className="text-sm text-muted-foreground">{message}</p>}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
