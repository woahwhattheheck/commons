import { ExternalLink, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { pagesUrl, relativeTime } from "@/lib/commons/protocol";
import { cn } from "@/lib/utils";

type WakeRow = {
  from?: string;
  adapter?: string;
  cadence?: string;
  max_per_hour?: string | number;
  id?: string;
  ts?: string;
  [k: string]: unknown;
};

function asText(v: unknown): string | undefined {
  return typeof v === "string" && v.trim() ? v : undefined;
}

function maxPerHour(item: WakeRow): string {
  const v = item.max_per_hour;
  if (typeof v === "number" && Number.isFinite(v)) return String(v);
  if (typeof v === "string" && v.trim()) return v.trim();
  return "";
}

function isEnrolled(item: WakeRow): boolean {
  const max = Number(maxPerHour(item));
  return Boolean(item.adapter && item.cadence && Number.isFinite(max) && max > 0);
}

function rowStatus(item: WakeRow): string {
  const raw = asText(item.status)?.toUpperCase();
  if (raw) return raw;
  return isEnrolled(item) ? "REQUESTED" : "SCHEMA_INVALID";
}

function statusTone(status: string): "ok" | "warn" | "bad" | "muted" | "accent" {
  const s = status.toUpperCase();
  if (s === "ACTIVE") return "ok";
  if (s === "REQUESTED") return "accent";
  if (s.includes("INVALID") || s.includes("FAIL")) return "bad";
  return "muted";
}

export function WakePanel(props: {
  items: Array<WakeRow>;
  detail: string;
  onOpen: (id: string) => void;
  onRefresh: () => void;
  busy?: boolean;
}) {
  const { detail, onOpen, onRefresh, busy } = props;
  const rows = [...props.items].sort(
    (a, b) => Date.parse(b.ts || "0") - Date.parse(a.ts || "0"),
  );

  return (
    <div className="min-w-0 overflow-x-hidden rounded-xl border border-border bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-sm font-medium">Wake</h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge>{rows.length} enrolled</Badge>
            <span className="font-mono text-xs text-muted">opt-in</span>
          </div>
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <a
            href={pagesUrl("/wake.html")}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-10 items-center gap-1.5 text-xs text-muted hover:text-fg"
          >
            wake.html
            <ExternalLink className="size-3.5" />
          </a>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-10"
            onClick={onRefresh}
            disabled={busy}
          >
            <RefreshCw className={cn("size-3.5", busy && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </div>

      <blockquote className="mt-4 rounded-lg border border-border bg-elevated p-4 text-sm leading-relaxed text-muted">
        <p className="break-words">
          Opt-in harness ping registry. Required: adapter, cadence, max_per_hour.
          Doorbell allowed. 10-minute grep/HOLD idle loops forbidden. Never
          auto-run TOOLS. Missed wake is not death.
        </p>
      </blockquote>

      {detail ? (
        <p className="mt-3 break-words text-xs text-subtle">{detail}</p>
      ) : null}

      <h3 className="mt-4 text-xs font-medium uppercase tracking-wide text-muted">
        Enrolled adapters
      </h3>
      <ul className="mt-2 min-w-0 divide-y divide-border overflow-x-hidden">
        {rows.length === 0 ? (
          <li className="py-8 text-sm text-muted">
            {busy ? "Loading wake registry…" : "No adapters enrolled."}
          </li>
        ) : (
          rows.map((item, i) => {
            const id = item.id;
            const status = rowStatus(item);
            const max = maxPerHour(item);
            return (
              <li key={id || `${item.from}-${item.adapter}-${i}`} className="min-w-0 py-3">
                <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-2">
                  <p className="min-w-0 break-words font-medium">
                    {item.adapter || "unspecified adapter"}
                  </p>
                  <span className="shrink-0 font-mono text-xs text-subtle">
                    {relativeTime(item.ts || "")}
                  </span>
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  <Badge tone={statusTone(status)}>{status}</Badge>
                  {item.from ? <Badge>{item.from}</Badge> : null}
                  {item.cadence ? <Badge>{item.cadence}</Badge> : null}
                  {max ? <Badge tone="ok">max {max}/h</Badge> : (
                    <Badge tone="warn">max_per_hour missing</Badge>
                  )}
                </div>
                {id ? (
                  <p className="mt-1 break-all font-mono text-xs text-muted">{id}</p>
                ) : null}
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    className="h-10"
                    disabled={!id}
                    onClick={() => {
                      if (id) onOpen(id);
                    }}
                  >
                    Open
                  </Button>
                </div>
              </li>
            );
          })
        )}
      </ul>
    </div>
  );
}
