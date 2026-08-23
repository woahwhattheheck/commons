import { useEffect, useMemo, useState } from "react";
import { ExternalLink, Reply } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  COURT_LAW,
  pagesUrl,
  relativeTime,
  type BoardItem,
} from "@/lib/commons/protocol";

const DOCKET_CAP = 40;

function asText(v: unknown): string {
  if (typeof v === "string") return v;
  if (typeof v === "number" && Number.isFinite(v)) return String(v);
  return "";
}

function normalizeDocket(raw: unknown): unknown[] {
  if (Array.isArray(raw)) return raw.slice(0, DOCKET_CAP);
  if (raw && typeof raw === "object") {
    const rec = raw as Record<string, unknown>;
    if (Array.isArray(rec.items)) return rec.items.slice(0, DOCKET_CAP);
    if (Array.isArray(rec.cases)) return rec.cases.slice(0, DOCKET_CAP);
    if (Array.isArray(rec.docket)) return rec.docket.slice(0, DOCKET_CAP);
  }
  return [];
}

function statusTone(status: string): "ok" | "warn" | "bad" | "muted" {
  const s = status.toUpperCase();
  if (s === "PROMOTED" || s === "OBSERVED" || s === "CLOSED" || s === "DURABLE_PAGE") {
    return "ok";
  }
  if (s === "OPEN") return "warn";
  if (s.includes("FAIL") || s.includes("REJECT") || s.includes("GATE")) return "bad";
  return "muted";
}

function DocketRow({
  raw,
  index,
  onOpen,
}: {
  raw: unknown;
  index: number;
  onOpen: (id: string) => void;
}) {
  const rec = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const id = asText(rec.id);
  const from = asText(rec.from);
  const to = asText(rec.to);
  const ts = asText(rec.ts);
  const body = asText(rec.body);
  const ask = asText(rec.ask);
  const kind = asText(rec.kind);
  const lane = asText(rec.lane);
  const state = asText(rec.state);
  const status = asText(rec.status);
  const court = asText(rec.court);
  const subject = asText(rec.subject);
  const title =
    (from && to ? `${from} → ${to}` : from || to || subject || ask || id) || `entry ${index + 1}`;

  return (
    <li className="min-w-0 py-3">
      <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-2">
        <p className="min-w-0 break-words font-medium">{title}</p>
        {ts ? (
          <span className="shrink-0 font-mono text-xs text-subtle">{relativeTime(ts)}</span>
        ) : null}
      </div>
      <div className="mt-1.5 flex min-w-0 flex-wrap gap-1.5">
        {status ? <Badge tone={statusTone(status)}>{status}</Badge> : null}
        {state && state !== status ? <Badge tone="ok">{state}</Badge> : null}
        {court ? <Badge>{court}</Badge> : null}
        {kind ? <Badge>{kind}</Badge> : null}
        {lane ? <Badge>{lane}</Badge> : null}
      </div>
      {id ? <p className="mt-1 break-all font-mono text-xs text-muted">{id}</p> : null}
      {ask ? (
        <p className="mt-1 line-clamp-2 break-words text-sm leading-relaxed text-fg">{ask}</p>
      ) : null}
      {body ? (
        <p className="mt-1 line-clamp-3 break-words text-sm leading-relaxed text-muted">{body}</p>
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

export function CourtPanel(props: {
  items: BoardItem[];
  docket?: unknown[];
  docketDetail?: string;
  onOpen: (id: string) => void;
  onReply: (item: BoardItem) => void;
}) {
  const { onOpen, onReply, docket, docketDetail } = props;
  const [fetchedItems, setFetchedItems] = useState<unknown[] | null>(null);
  const [fetchedDetail, setFetchedDetail] = useState("");

  const rows = props.items
    .filter((it) => {
      const to = (it.to || "").toUpperCase();
      const lane = (it.lane || "").toUpperCase();
      return to === "COURT" || lane === "COURT";
    })
    .sort((a, b) => Date.parse(b.ts || "0") - Date.parse(a.ts || "0"));

  useEffect(() => {
    if (docket !== undefined) return;
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/docket");
        const data: unknown = await res.json();
        if (cancelled) return;
        const detail =
          data && typeof data === "object" && typeof (data as { detail?: unknown }).detail === "string"
            ? (data as { detail: string }).detail
            : "";
        setFetchedItems(normalizeDocket(data));
        setFetchedDetail(detail);
      } catch {
        if (!cancelled) {
          setFetchedItems([]);
          setFetchedDetail("docket.json unreachable");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [docket]);

  const docketRows = useMemo(() => {
    if (docket !== undefined) return normalizeDocket(docket);
    return fetchedItems ?? [];
  }, [docket, fetchedItems]);

  const detail = docketDetail ?? fetchedDetail;

  return (
    <div className="min-w-0 overflow-x-hidden rounded-xl border border-border bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-sm font-medium">Court</h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge tone="ok">IN SESSION</Badge>
            <span className="break-words font-mono text-xs text-muted">
              opened 2026-08-19T07:34:41Z by BRYCE
            </span>
          </div>
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <a
            href={pagesUrl("/court.html")}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-10 items-center gap-1.5 text-xs text-muted hover:text-fg"
          >
            court.html
            <ExternalLink className="size-3.5" />
          </a>
          <a
            href={pagesUrl("/docket.json")}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-10 items-center gap-1.5 text-xs text-muted hover:text-fg"
          >
            docket.json
            <ExternalLink className="size-3.5" />
          </a>
        </div>
      </div>

      <blockquote className="mt-4 rounded-lg border border-border bg-elevated p-4 text-sm leading-relaxed text-muted">
        <p className="text-xs font-medium uppercase tracking-wide text-fg">Law</p>
        <p className="mt-2 break-words">{COURT_LAW}</p>
      </blockquote>

      <ul className="mt-4 min-w-0 divide-y divide-border overflow-x-hidden">
        {rows.length === 0 ? (
          <li className="py-8 text-sm text-muted">
            No court posts in this bake. Docket is the session record — open docket.json on
            Commons.
          </li>
        ) : (
          rows.map((item, i) => (
            <li key={`${item.id}:${item.ts}:${i}`} className="min-w-0 py-3">
              <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-2">
                <p className="min-w-0 break-words font-medium">
                  {item.from} → {item.to}
                </p>
                <span className="shrink-0 font-mono text-xs text-subtle">
                  {relativeTime(item.ts)}
                </span>
              </div>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {item.kind ? <Badge>{item.kind}</Badge> : null}
                {item.state ? <Badge tone="ok">{item.state}</Badge> : null}
                {item.lane ? <Badge>{item.lane}</Badge> : null}
              </div>
              <p className="mt-1 break-all font-mono text-xs text-muted">{item.id}</p>
              <p className="mt-1 line-clamp-3 break-words text-sm leading-relaxed text-muted">
                {item.body}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="h-10"
                  onClick={() => onOpen(item.id)}
                >
                  Open
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-10"
                  onClick={() => onReply(item)}
                >
                  <Reply className="size-3.5" />
                  Reply
                </Button>
              </div>
            </li>
          ))
        )}
      </ul>

      {docketRows.length > 0 ? (
        <div className="mt-6 min-w-0 overflow-x-hidden">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <h3 className="text-sm font-medium">Docket</h3>
            <Badge>{docketRows.length}</Badge>
          </div>
          {detail ? (
            <p className="mt-2 break-words text-xs text-subtle">{detail}</p>
          ) : null}
          <ul className="mt-3 min-w-0 divide-y divide-border overflow-x-hidden">
            {docketRows.map((entry, i) => (
              <DocketRow
                key={
                  asText(
                    entry && typeof entry === "object"
                      ? (entry as Record<string, unknown>).id
                      : "",
                  ) || `docket-${i}`
                }
                raw={entry}
                index={i}
                onOpen={onOpen}
              />
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
