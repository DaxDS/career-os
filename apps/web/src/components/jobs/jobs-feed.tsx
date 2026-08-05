"use client";

import { useCallback, useState } from "react";
import { JobMatchCard, type JobMatchRow } from "@/components/jobs/job-match-card";
import { Button } from "@/components/ui/button";

interface JobsFeedProps {
  initialMatches: JobMatchRow[];
}

export function JobsFeed({ initialMatches }: JobsFeedProps) {
  const [matches, setMatches] = useState(initialMatches);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runDiscovery = useCallback(async () => {
    setRunning(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch("/api/discovery/run", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Discovery failed");
      // /api/discovery/run returns { discovered, matched } — this previously read
      // stats.found / stats.matches_created / stats.filtered_ineligible, none of
      // which the route has ever sent, so every run reported "Found 0 listings"
      // regardless of what actually happened.
      if (data.message) {
        setMessage(data.message);
      } else {
        setMessage(`Found ${data.discovered ?? 0} listings · ${data.matched ?? 0} scored and added to your feed`);
      }
      window.location.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Discovery failed");
    } finally {
      setRunning(false);
    }
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Matched jobs</h1>
          <p className="text-muted-foreground">
            NOC/TEER classified, wage compared to regional median, pathway flags applied.
          </p>
        </div>
        <Button onClick={runDiscovery} disabled={running}>
          {running ? "Running discovery…" : "Run discovery"}
        </Button>
      </div>

      {message && <p className="text-sm text-green-700">{message}</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}

      {matches.length === 0 ? (
        <div className="rounded-xl border border-dashed p-12 text-center">
          <p className="text-muted-foreground">No matches yet.</p>
          <p className="mt-2 text-sm text-muted-foreground">
            Click &quot;Run discovery&quot; to search Job Bank for your target titles.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {matches.map((row) => (
            <JobMatchCard key={row.match_id} row={row} />
          ))}
        </div>
      )}
    </div>
  );
}
