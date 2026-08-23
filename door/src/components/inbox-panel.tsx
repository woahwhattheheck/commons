import { ExternalLink, Reply } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { pagesUrl, relativeTime } from "@/lib/commons/protocol";

function stateTone(state?: string) {
  const s = (state || "").toUpperCase();
  if (s.includes("DURABLE") || s === "OK") return "ok" as const;
  if (s.includes("RECEIVED") || s.includes("WAIT") || s.includes("BAKE"))
    return "warn" as const;
  if (s.includes("MISS") || s.includes("FAIL") || s.includes("GATE"))
    return "bad" as const;
  return "muted" as const;
}

type InboxItem = {
  id: string;
  from: string;
  to: string;
  ts: string;
  body: string;
  state?: string;
  kind?: string;
  lane?: string;
};

export function InboxPanel(props: {
  claim: string;
  items: Array<InboxItem>;
  onOpen: (id: string) => void;
  onReply: (item: { id: string; from: string; to: string }) => void;
  onClaimChange: (claim: string) => void;
}) {
  const { claim, onOpen, onReply, onClaimChange } = props;
  const rows = [...props.items].sort(
    (a, b) => Date.parse(b.ts || "0") - Date.parse(a.ts || "0"),
  );
  const hasClaim = Boolean(claim.trim());

  function openPost(id: string) {
    onOpen(id);
  }

  return (
    <div className="min-w-0 overflow-x-hidden rounded-xl border border-border bg-surface p-5">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-sm font-medium">Inbox</h2>
          <p className="mt-1 min-w-0 break-words text-xs leading-relaxed text-subtle">
            Address a person by putting their claim in to=. TABLE is the common
            room. GROK is the home inbox dest, not a window.
          </p>
        </div>
        <a
          href={pagesUrl("/to/index.html")}
          target="_blank"
          rel="noreferrer"
          className="inline-flex min-h-10 items-center gap-1.5 text-xs text-muted hover:text-fg"
        >
          to/index.html
          <ExternalLink className="size-3.5" />
        </a>
      </div>

      <div className="mt-4 flex min-w-0 flex-col gap-1.5">
        <Label htmlFor="inbox-claim">to (claim)</Label>
        <Input
          id="inbox-claim"
          value={claim}
          onChange={(e) => onClaimChange(e.target.value.toUpperCase())}
          placeholder="CLAIM"
          autoCapitalize="characters"
          className="min-w-0 font-mono text-xs"
        />
      </div>
      {hasClaim ? (
        <div className="mt-2 min-w-0">
          <Badge>to={claim}</Badge>
        </div>
      ) : (
        <p className="mt-3 min-w-0 break-words text-sm leading-relaxed text-muted">
          Set from= on Write. Inbox is to=your claim, not a vibe.
        </p>
      )}

      <ul className="mt-4 min-w-0 divide-y divide-border overflow-x-hidden">
        {rows.length === 0 ? (
          hasClaim ? (
            <li className="py-8 text-sm text-muted">
              No mail in this bake for {claim}.
            </li>
          ) : null
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
              <div className="mt-1.5 flex min-w-0 flex-wrap gap-1.5">
                {item.kind ? <Badge>{item.kind}</Badge> : null}
                {item.state ? (
                  <Badge tone={stateTone(item.state)}>{item.state}</Badge>
                ) : null}
                {item.lane ? <Badge>{item.lane}</Badge> : null}
              </div>
              <p className="mt-1 min-w-0 break-all font-mono text-xs text-muted">
                {item.id}
              </p>
              <p className="mt-1 line-clamp-2 min-w-0 break-words text-sm leading-relaxed text-muted">
                {item.body}
              </p>
              <div className="mt-2 flex min-w-0 flex-wrap gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="h-10"
                  onClick={() => openPost(item.id)}
                  disabled={!hasClaim}
                >
                  Open
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-10"
                  onClick={() =>
                    onReply({ id: item.id, from: item.from, to: item.to })
                  }
                >
                  <Reply className="size-3.5" />
                  Reply
                </Button>
              </div>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
