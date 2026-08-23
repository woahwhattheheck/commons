import { ExternalLink, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { pagesUrl, relativeTime } from "@/lib/commons/protocol";
import { cn } from "@/lib/utils";

type FailedItem = {
  id?: string;
  from?: string;
  code?: string;
  reason?: string;
  ts?: string;
  body?: string;
  [k: string]: unknown;
};

function FailedRow({
  item,
  onOpen,
}: {
  item: FailedItem;
  onOpen: (id: string) => void;
}) {
  const id = typeof item.id === "string" ? item.id : "";
  const from = typeof item.from === "string" ? item.from : "";
  const code = typeof item.code === "string" ? item.code : "";
  const reason = typeof item.reason === "string" ? item.reason : "";
  const ts = typeof item.ts === "string" ? item.ts : "";
  const body = typeof item.body === "string" ? item.body : "";

  return (
    <li className="min-w-0 py-3">
      <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-2">
        <p className="min-w-0 break-words font-medium">{from || "unknown"}</p>
        <span className="shrink-0 font-mono text-xs text-subtle">
          {relativeTime(ts)}
        </span>
      </div>
      <div className="mt-1.5 flex min-w-0 flex-wrap items-center gap-1.5">
        {code ? <Badge tone="bad">{code}</Badge> : <Badge tone="bad">REJECT</Badge>}
      </div>
      {id ? (
        <p className="mt-1 break-all font-mono text-xs text-muted">{id}</p>
      ) : null}
      {reason ? (
        <p className="mt-1 break-words text-sm leading-relaxed text-muted">{reason}</p>
      ) : null}
      {body ? (
        <p className="mt-1 line-clamp-3 break-words text-sm leading-relaxed text-subtle">
          {body}
        </p>
      ) : null}
      {id ? (
        <div className="mt-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="h-10"
            onClick={() => onOpen(id)}
          >
            Open
          </Button>
        </div>
      ) : null}
    </li>
  );
}

export function FailedPanel(props: {
  items: FailedItem[];
  detail: string;
  onOpen: (id: string) => void;
  onRefresh: () => void;
  busy?: boolean;
}) {
  const { items, detail, onOpen, onRefresh, busy } = props;

  return (
    <div className="min-w-0 overflow-x-hidden rounded-xl border border-border bg-surface p-5">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex min-w-0 items-center gap-2">
            <h2 className="text-sm font-medium">Failed posts</h2>
            <Badge tone="bad">{items.length}</Badge>
          </div>
          <p className="mt-2 break-words text-sm leading-relaxed text-muted">
            ntfy 200 is mail. If it is not a durable page, ingest rejected it here.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
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
          <a
            href={pagesUrl("/failed.html")}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-10 items-center gap-1.5 text-xs text-muted hover:text-fg"
          >
            Open on Commons
            <ExternalLink className="size-3.5" />
          </a>
        </div>
      </div>

      {detail ? (
        <p className="mt-3 break-words text-xs text-subtle">{detail}</p>
      ) : null}

      <ul className="mt-4 min-w-0 divide-y divide-border overflow-x-hidden">
        {items.length === 0 ? (
          <li className="py-8 text-sm text-muted">
            {busy ? "Loading rejects…" : "No rejected posts on this bake."}
          </li>
        ) : (
          items.map((item, i) => (
            <FailedRow
              key={typeof item.id === "string" && item.id ? item.id : `failed-${i}`}
              item={item}
              onOpen={onOpen}
            />
          ))
        )}
      </ul>
    </div>
  );
}
