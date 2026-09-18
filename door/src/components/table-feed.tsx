import { RefreshCw, Reply } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  relativeTime,
  ROOMS,
  type BoardItem,
} from "@/lib/commons/protocol";
import { cn } from "@/lib/utils";

function stateTone(state?: string) {
  const s = (state || "").toUpperCase();
  if (s.includes("DURABLE") || s === "OK") return "ok" as const;
  if (s.includes("RECEIVED") || s.includes("WAIT") || s.includes("BAKE"))
    return "warn" as const;
  if (s.includes("MISS") || s.includes("FAIL") || s.includes("GATE"))
    return "bad" as const;
  return "muted" as const;
}

function FeedRow({
  item,
  onOpen,
  onReply,
}: {
  item: BoardItem;
  onOpen: (id: string) => void;
  onReply: (item: BoardItem) => void;
}) {
  return (
    <li className="min-w-0 overflow-x-hidden py-3">
      <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <p className="min-w-0 flex-1 break-words font-medium">
          {item.from} → {item.to}
        </p>
        <span className="shrink-0 font-mono text-xs text-subtle">
          {relativeTime(item.ts)}
        </span>
      </div>
      <div className="mt-1.5 flex min-w-0 flex-wrap gap-1.5">
        {item.kind ? <Badge>{item.kind}</Badge> : null}
        {item.state ? <Badge tone={stateTone(item.state)}>{item.state}</Badge> : null}
        {item.lane ? <Badge>{item.lane}</Badge> : null}
        {item.subject ? <Badge tone="accent">{item.subject}</Badge> : null}
      </div>
      <p className="mt-1 break-all font-mono text-xs text-muted">{item.id}</p>
      <p className="mt-1 line-clamp-3 min-w-0 break-words text-sm leading-relaxed text-muted">
        {item.body}
      </p>
      <div className="mt-2 flex min-w-0 flex-wrap gap-2">
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
  );
}

export function TableFeed(props: {
  items: BoardItem[];
  warning: string;
  filter: string;
  roomId: string | null;
  roomTitle?: string;
  inbox: string;
  onOpen: (id: string) => void;
  onReply: (item: BoardItem) => void;
  onRefresh: () => void;
  busy?: boolean;
}) {
  const { items, warning, filter, roomId, roomTitle, inbox, onOpen, onReply, onRefresh, busy } =
    props;
  const room = roomId ? ROOMS.find((r) => r.id === roomId) : undefined;
  const sitLabel = room?.title || roomTitle;
  const rows = [...items]
    .sort((a, b) => Date.parse(b.ts || "0") - Date.parse(a.ts || "0"))
    .slice(0, 40);

  return (
    <div className="min-w-0 overflow-x-hidden rounded-xl border border-border bg-surface p-5">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <h2 className="min-w-0 text-sm font-medium">Table</h2>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-10 shrink-0"
          onClick={onRefresh}
          disabled={busy}
        >
          <RefreshCw className={cn("size-3.5", busy && "animate-spin")} />
          Refresh
        </Button>
      </div>
      <p className="mt-1 min-w-0 break-words text-xs text-subtle">{warning}</p>
      {(filter || sitLabel || inbox) && (
        <div className="mt-2 flex min-w-0 flex-wrap gap-1.5 overflow-x-hidden">
          {filter ? <Badge>search {filter}</Badge> : null}
          {sitLabel ? <Badge tone="accent">{sitLabel}</Badge> : null}
          {inbox ? <Badge>to={inbox}</Badge> : null}
        </div>
      )}
      <ul className="mt-3 min-w-0 divide-y divide-border overflow-x-hidden">
        {rows.length === 0 ? (
          <li className="min-w-0 py-8 text-sm text-muted">
            {busy ? "Loading the bake…" : "No posts in this view."}
          </li>
        ) : (
          rows.map((item, i) => (
            <FeedRow key={`${item.id}:${item.ts}:${i}`} item={item} onOpen={onOpen} onReply={onReply} />
          ))
        )}
      </ul>
    </div>
  );
}
