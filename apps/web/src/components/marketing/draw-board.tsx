import { useTranslations } from "next-intl";

import snapshot from "@/lib/draw-snapshot.json";

type DrawRow = {
  id: string;
  label: string;
  rounds: number;
  itas: number;
  lastDrawn: string | null;
  typicalCutoff: number | null;
};

const live = snapshot.live as DrawRow[];
const dormant = snapshot.dormant as DrawRow[];

/** Programme rounds are not occupation categories; the dormant list is only
 *  interesting for categories a candidate could otherwise be told they qualify for. */
const PROGRAM_IDS = new Set(["general", "fsw", "fst"]);
const dormantCategories = dormant.filter((row) => !PROGRAM_IDS.has(row.id));

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(`${value}T00:00:00Z`).toLocaleDateString("en-CA", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function DrawBoard() {
  const t = useTranslations("landing.drawBoard");

  return (
    <section className="border-y border-border/60 bg-card/20 py-16 sm:py-20">
      <div className="mx-auto max-w-5xl px-4">
        <h2 className="mb-3 text-center text-2xl font-bold sm:text-3xl">{t("title")}</h2>
        <p className="mx-auto mb-10 max-w-2xl text-center text-sm text-muted-foreground sm:text-base">
          {t("subtitle")}
        </p>

        <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
          <div className="rounded-xl border border-border bg-card p-5 sm:p-6">
            <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              <span
                aria-hidden="true"
                className="inline-block h-2 w-2 shrink-0 rounded-full bg-emerald-500"
              />
              {t("liveLabel")}
            </h3>
            <div className="-mx-1 overflow-x-auto">
              <table className="w-full min-w-[26rem] border-collapse text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th scope="col" className="py-2 pr-3 font-medium">
                      Category
                    </th>
                    <th scope="col" className="py-2 pr-3 text-right font-medium">
                      Invitations
                    </th>
                    <th scope="col" className="py-2 pr-3 text-right font-medium">
                      Cut-off
                    </th>
                    <th scope="col" className="py-2 text-right font-medium">
                      Last round
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {live.map((row) => (
                    <tr key={row.id} className="border-t border-border/60">
                      <td className="py-2 pr-3 font-medium">{row.label}</td>
                      <td className="py-2 pr-3 text-right tabular-nums text-muted-foreground">
                        {row.itas.toLocaleString("en-CA")}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">
                        {row.typicalCutoff ?? "—"}
                      </td>
                      <td className="py-2 text-right whitespace-nowrap text-muted-foreground">
                        {formatDate(row.lastDrawn)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-xl border border-amber-500/40 bg-amber-500/5 p-5 sm:p-6">
            <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              <span
                aria-hidden="true"
                className="inline-block h-2 w-2 shrink-0 rounded-full bg-amber-500"
              />
              {t("dormantLabel")}
            </h3>
            <ul className="space-y-2 text-sm">
              {dormantCategories.map((row) => (
                <li key={row.id} className="flex items-baseline justify-between gap-3">
                  <span className="font-medium">{row.label}</span>
                  <span className="whitespace-nowrap text-xs text-muted-foreground">
                    0 rounds in {snapshot.windowMonths} months
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-5 border-t border-amber-500/30 pt-4 text-sm text-muted-foreground">
              {t("stemNote")}
            </p>
          </div>
        </div>

        <p className="mx-auto mt-8 max-w-3xl text-center text-xs text-muted-foreground">
          {t("sourceNote")}{" "}
          <span className="whitespace-nowrap">Draw data as of {formatDate(snapshot.asOf)}.</span>
        </p>
      </div>
    </section>
  );
}
