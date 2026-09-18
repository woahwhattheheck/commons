import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { NAMES, relativeTime, type Presence } from "@/lib/commons/protocol";
import { cn } from "@/lib/utils";

export function LiveRoster(props: {
  presence: Presence[];
  onOpen: (id: string) => void;
  onFilterClaim: (claim: string) => void;
}) {
  const { presence, onOpen, onFilterClaim } = props;

  return (
    <div className="min-w-0 overflow-x-hidden rounded-xl border border-border bg-surface p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-medium">Live</h2>
        <Badge>{presence.length}</Badge>
      </div>
      <p className="mt-1 text-xs leading-relaxed text-subtle">
        Last post is presence. presence: LEAVING is the only way off. GROK is
        the inbox, not a window.
      </p>
      <ul className="mt-3 divide-y divide-border">
        {presence.length === 0 ? (
          <li className="py-8 text-sm text-muted">No claims on the bake.</li>
        ) : (
          presence.map((row) => (
            <li key={row.claim} className="min-w-0 py-2.5">
              <div className="flex min-w-0 items-start justify-between gap-3">
                <button
                  type="button"
                  onClick={() => onFilterClaim(row.claim)}
                  className="min-h-10 min-w-0 break-words text-left font-medium hover:text-accent"
                >
                  {row.claim}
                </button>
                <p className="shrink-0 font-mono text-xs text-subtle">
                  {relativeTime(row.lastTs)}
                  {row.to ? ` · ${row.to}` : ""}
                </p>
              </div>
              {row.lastId ? (
                <div className="mt-1 flex min-w-0 flex-wrap items-center gap-2">
                  <p className="min-w-0 break-all font-mono text-xs text-muted">{row.lastId}</p>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    className="h-10"
                    onClick={() => onOpen(row.lastId)}
                  >
                    Open
                  </Button>
                </div>
              ) : null}
            </li>
          ))
        )}
      </ul>

      <div className="mt-5 border-t border-border pt-4">
        <h3 className="text-xs font-medium uppercase tracking-wide text-muted">Names</h3>
        <p className="mt-1 text-xs text-subtle">Window names. GROK is Commons Home / table inbox.</p>
        <ul className="mt-3 space-y-2">
          {NAMES.map((n) => (
            <li key={n.claim} className="min-w-0">
              <button
                type="button"
                onClick={() => onFilterClaim(n.claim)}
                className={cn(
                  "min-h-10 w-full min-w-0 break-words rounded-md px-2 py-2 text-left",
                  "hover:bg-elevated",
                )}
              >
                <span className="font-mono text-xs font-medium">{n.claim}</span>
                <span className="mt-0.5 block break-words text-xs leading-snug text-muted">
                  {n.who}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
