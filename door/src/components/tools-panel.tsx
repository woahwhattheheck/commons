import { ExternalLink, RefreshCw, Reply } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { pagesUrl, relativeTime } from "@/lib/commons/protocol";
import { cn } from "@/lib/utils";

type ToolJob = {
  id?: string;
  from?: string;
  tool?: string;
  status?: string;
  ts?: string;
  body?: string;
  [k: string]: unknown;
};

function asText(v: unknown): string | undefined {
  return typeof v === "string" && v.trim() ? v : undefined;
}

function jobStatus(item: ToolJob): string {
  const raw = (item.status || asText(item.kind) || "").toUpperCase();
  if (raw.includes("RECEIPT") || raw === "DONE" || raw === "DONE_ALREADY") {
    return "RECEIPT";
  }
  if (!raw || raw === "OPEN" || raw === "ACTION") return "OPEN";
  return raw;
}

function statusTone(status: string): "ok" | "warn" | "bad" | "muted" {
  const s = status.toUpperCase();
  if (s === "RECEIPT" || s === "DONE" || s === "DONE_ALREADY") return "ok";
  if (s === "OPEN") return "warn";
  if (s.includes("FAIL") || s.includes("REFUSE") || s.includes("GATE")) return "bad";
  return "muted";
}

export function ToolsPanel(props: {
  items: Array<ToolJob>;
  detail: string;
  onOpen: (id: string) => void;
  onReply: (item: { id: string; from?: string; to?: string }) => void;
  onRefresh: () => void;
  busy?: boolean;
}) {
  const { detail, onOpen, onReply, onRefresh, busy } = props;
  const rows = [...props.items].sort(
    (a, b) => Date.parse(b.ts || "0") - Date.parse(a.ts || "0"),
  );

  return (
    <div className="min-w-0 overflow-x-hidden rounded-xl border border-border bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-sm font-medium">Tools jobs</h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge tone="warn">OPEN</Badge>
            <Badge tone="ok">RECEIPT</Badge>
            <span className="font-mono text-xs text-muted">{rows.length}</span>
          </div>
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <a
            href={pagesUrl("/tools.html")}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-10 items-center gap-1.5 text-xs text-muted hover:text-fg"
          >
            tools.html
            <ExternalLink className="size-3.5" />
          </a>
          <a
            href={pagesUrl("/action.html")}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-10 items-center gap-1.5 text-xs text-muted hover:text-fg"
          >
            action.html
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
          Post a job on TOOLS. Someone on the PC runs{" "}
          <code className="break-words font-mono text-xs text-fg">
            python host/muhl_tools_once.py --go
          </code>{" "}
          — one allowed job, receipt, dies. Not a tunnel. CUT :7862 White Box
          stays on the PC. HTTP is not the computer.
        </p>
      </blockquote>

      {detail ? (
        <p className="mt-3 break-words text-xs text-subtle">{detail}</p>
      ) : null}

      <ul className="mt-4 min-w-0 divide-y divide-border overflow-x-hidden">
        {rows.length === 0 ? (
          <li className="py-8 text-sm text-muted">
            {busy ? "Loading TOOLS jobs…" : "No TOOLS jobs on this bake."}
          </li>
        ) : (
          rows.map((item, i) => {
            const status = jobStatus(item);
            const id = item.id;
            return (
              <li key={id || `${item.from}-${item.ts}-${i}`} className="min-w-0 py-3">
                <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-2">
                  <p className="min-w-0 break-words font-medium">
                    {item.tool || "job"}
                    {item.from ? (
                      <span className="text-muted"> · {item.from}</span>
                    ) : null}
                  </p>
                  <span className="shrink-0 font-mono text-xs text-subtle">
                    {relativeTime(item.ts || "")}
                  </span>
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  <Badge tone={statusTone(status)}>{status}</Badge>
                  {item.tool ? <Badge>{item.tool}</Badge> : null}
                  {item.from ? <Badge>{item.from}</Badge> : null}
                </div>
                {id ? (
                  <p className="mt-1 break-all font-mono text-xs text-muted">{id}</p>
                ) : null}
                {item.body ? (
                  <p className="mt-1 line-clamp-3 break-words text-sm leading-relaxed text-muted">
                    {item.body}
                  </p>
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
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-10"
                    disabled={!id}
                    onClick={() => {
                      if (!id) return;
                      onReply({
                        id,
                        from: item.from,
                        to: asText(item.to) || "TOOLS",
                      });
                    }}
                  >
                    <Reply className="size-3.5" />
                    Reply
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
