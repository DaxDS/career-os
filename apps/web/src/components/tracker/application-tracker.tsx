"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLUMNS = [
  { key: "approved", label: "Approved", desc: "Ready to send" },
  { key: "sent", label: "Sent", desc: "Submitted" },
  { key: "response", label: "Response", desc: "Heard back" },
  { key: "interview", label: "Interview", desc: "Scheduled" },
  { key: "offer", label: "Offer", desc: "Offers" },
  { key: "rejected", label: "Rejected", desc: "Closed" },
] as const;

export interface TrackerApplication {
  id: string;
  status: string;
  sent_at: string | null;
  cover_letter_text: string | null;
  submission_method: string | null;
  match: {
    jobs: { title: string; company: string | null; url: string };
  };
}

export function ApplicationTracker({ applications }: { applications: TrackerApplication[] }) {
  const router = useRouter();
  const [loadingId, setLoadingId] = useState<string | null>(null);

  async function dispatch(appId: string) {
    setLoadingId(appId);
    try {
      const res = await fetch(`/api/applications/${appId}/dispatch`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed");
      if (data.apply_url) window.open(data.apply_url, "_blank");
      router.refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Dispatch failed");
    } finally {
      setLoadingId(null);
    }
  }

  async function moveStatus(appId: string, status: string) {
    await fetch(`/api/applications/${appId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    router.refresh();
  }

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {COLUMNS.map((col) => {
        const items = applications.filter((a) => a.status === col.key);
        return (
          <div key={col.key} className="min-w-[240px] flex-1">
            <div className="mb-3">
              <h2 className="font-semibold">{col.label}</h2>
              <p className="text-xs text-muted-foreground">{col.desc} · {items.length}</p>
            </div>
            <div className="space-y-3">
              {items.map((app) => (
                <Card key={app.id} className="shadow-sm">
                  <CardHeader className="p-4 pb-2">
                    <CardTitle className="text-sm leading-snug">
                      {app.match.jobs.title}
                    </CardTitle>
                    <p className="text-xs text-muted-foreground">{app.match.jobs.company}</p>
                  </CardHeader>
                  <CardContent className="space-y-2 p-4 pt-0">
                    {col.key === "approved" && (
                      <Button
                        size="sm"
                        className="w-full"
                        onClick={() => dispatch(app.id)}
                        disabled={loadingId === app.id}
                      >
                        {loadingId === app.id ? "Sending…" : "Open apply link"}
                      </Button>
                    )}
                    {col.key === "sent" && (
                      <Button size="sm" variant="outline" className="w-full" onClick={() => moveStatus(app.id, "response")}>
                        Mark response
                      </Button>
                    )}
                    {col.key === "response" && (
                      <Button size="sm" variant="outline" className="w-full" onClick={() => moveStatus(app.id, "interview")}>
                        Mark interview
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" className="w-full" asChild>
                      <a href={app.match.jobs.url} target="_blank" rel="noopener noreferrer">
                        Job posting
                      </a>
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
