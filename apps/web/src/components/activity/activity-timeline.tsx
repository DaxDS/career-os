"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Ban,
  CheckCircle2,
  FileText,
  Filter,
  MapPin,
  Play,
  Search,
  Send,
  Sparkles,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { Link } from "@/i18n/routing";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface ActivityEntry {
  id: string;
  action: string;
  summary: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

const ACTION_ICONS: Record<string, LucideIcon> = {
  discovery_started: Play,
  discovery_completed: CheckCircle2,
  discovery_failed: XCircle,
  application_marked_sent: Send,
  source_searched: Search,
  noc_classified: MapPin,
  jobs_filtered: Filter,
  matches_below_threshold: Filter,
  jobs_skipped_dedup: Filter,
  tailoring_started: Sparkles,
  tailoring_completed: FileText,
  tailoring_blocked: Ban,
  tailoring_failed: XCircle,
  pathway_report_generated: MapPin,
  pathway_report_blocked: Ban,
  application_dispatched: Send,
  dispatch_blocked: Ban,
  dispatch_failed: XCircle,
  application_approved: CheckCircle2,
  application_rejected: XCircle,
};

function actionIcon(action: string): LucideIcon {
  return ACTION_ICONS[action] ?? Sparkles;
}

function dayKey(iso: string): string {
  return iso.slice(0, 10);
}

function formatDayLabel(iso: string, t: (key: string, values?: Record<string, string>) => string): string {
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);

  const sameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();

  if (sameDay(date, today)) return t("today");
  if (sameDay(date, yesterday)) return t("yesterday");
  return date.toLocaleDateString(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function EntryRow({ entry }: { entry: ActivityEntry }) {
  const t = useTranslations("activity");
  const [open, setOpen] = useState(false);
  const Icon = actionIcon(entry.action);
  const summary = entry.summary ?? t(`actions.${entry.action}` as "actions.discovery_started");
  const hasMetadata = entry.metadata && Object.keys(entry.metadata).length > 0;

  return (
    <li className="flex gap-3 rounded-lg border bg-card p-3 sm:p-4">
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-full",
          entry.action.includes("blocked") || entry.action.includes("failed") || entry.action.includes("rejected")
            ? "bg-destructive/10 text-destructive"
            : "bg-primary/10 text-primary"
        )}
      >
        <Icon className="h-4 w-4" aria-hidden />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium leading-snug">{summary}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {new Date(entry.created_at).toLocaleTimeString(undefined, {
            hour: "numeric",
            minute: "2-digit",
          })}
        </p>
        {hasMetadata && (
          <div className="mt-2">
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="text-xs font-medium text-primary hover:underline"
              aria-expanded={open}
            >
              {open ? t("hideDetails") : t("showDetails")}
            </button>
            {open && (
              <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-muted/60 p-2 text-xs text-muted-foreground">
                {JSON.stringify(entry.metadata, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>
    </li>
  );
}

export function ActivityTimeline({
  entries,
  compact = false,
}: {
  entries: ActivityEntry[];
  compact?: boolean;
}) {
  const t = useTranslations("activity");

  if (entries.length === 0) {
    return (
      <div className="rounded-xl border border-dashed p-8 text-center">
        <p className="font-medium">{t("emptyTitle")}</p>
        <p className="mt-2 text-sm text-muted-foreground">{t("emptyDescription")}</p>
      </div>
    );
  }

  const grouped = entries.reduce<Map<string, ActivityEntry[]>>((acc, entry) => {
    const key = dayKey(entry.created_at);
    if (!acc.has(key)) acc.set(key, []);
    acc.get(key)!.push(entry);
    return acc;
  }, new Map());

  return (
    <div className={cn("space-y-6", compact && "space-y-4")}>
      {Array.from(grouped.entries()).map(([day, items]) => (
        <section key={day}>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {formatDayLabel(items[0].created_at, t)}
          </h2>
          <ul className={cn("space-y-2", compact && "space-y-2")}>
            {items.map((entry) => (
              <EntryRow key={entry.id} entry={entry} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

export function ActivityPagination({
  page,
  totalPages,
  basePath = "/activity",
}: {
  page: number;
  totalPages: number;
  basePath?: string;
}) {
  const t = useTranslations("activity");

  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between gap-4 pt-4">
      <p className="text-sm text-muted-foreground">{t("pageOf", { page, total: totalPages })}</p>
      <div className="flex gap-2">
        {page > 1 ? (
          <Button asChild variant="outline" size="sm">
            <Link href={`${basePath}?page=${page - 1}`}>{t("prevPage")}</Link>
          </Button>
        ) : (
          <Button variant="outline" size="sm" disabled>
            {t("prevPage")}
          </Button>
        )}
        {page < totalPages ? (
          <Button asChild variant="outline" size="sm">
            <Link href={`${basePath}?page=${page + 1}`}>{t("nextPage")}</Link>
          </Button>
        ) : (
          <Button variant="outline" size="sm" disabled>
            {t("nextPage")}
          </Button>
        )}
      </div>
    </div>
  );
}
