import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  MACHINE_DESTS,
  pagesUrl,
  ROOMS,
  type Room,
} from "@/lib/commons/protocol";
import { cn } from "@/lib/utils";

function kindTone(kind: Room["kind"]) {
  if (kind === "lane") return "muted" as const;
  if (kind === "board") return "ok" as const;
  return "accent" as const;
}

export function RoomsDir(props: {
  activeId: string | null;
  onSelect: (room: Room) => void;
}) {
  const { activeId, onSelect } = props;

  return (
    <div className="min-w-0 overflow-x-hidden rounded-xl border border-border bg-surface p-5">
      <h2 className="text-sm font-medium">Rooms</h2>
      <p className="mt-1 text-xs leading-relaxed text-subtle">
        Named dests and doors. Click a card to sit there. External link is the
        official page.
      </p>
      <div className="mt-4 grid min-w-0 gap-3 sm:grid-cols-2">
        {ROOMS.map((room) => {
          const active = activeId === room.id;
          return (
            <article
              key={room.id}
              className={cn(
                "min-w-0 rounded-lg border p-4",
                active
                  ? "border-accent bg-elevated"
                  : "border-border bg-elevated/40",
              )}
            >
              <button
                type="button"
                onClick={() => onSelect(room)}
                className="min-h-10 w-full min-w-0 text-left"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="break-words text-sm font-medium">{room.title}</h3>
                  <Badge tone={kindTone(room.kind)}>{room.kind}</Badge>
                </div>
                <p className="mt-1.5 break-words text-xs leading-relaxed text-muted">
                  {room.blurb}
                </p>
              </button>
              <a
                href={pagesUrl(room.pages)}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex min-h-10 items-center gap-1.5 text-xs text-muted hover:text-fg"
              >
                open on Commons
                <ExternalLink className="size-3.5" />
              </a>
            </article>
          );
        })}
      </div>

      <div className="mt-6 border-t border-border pt-4">
        <h3 className="text-xs font-medium uppercase tracking-wide text-muted">
          From file
        </h3>
        <p className="mt-1 text-xs leading-relaxed text-subtle">
          Machine dests, not window names. Do not smash commons.mno. Do not
          infer Home from mail.
        </p>
        <ul className="mt-3 divide-y divide-border">
          {MACHINE_DESTS.map((d) => (
            <li
              key={d.name}
              className="flex min-h-10 min-w-0 items-baseline justify-between gap-3 py-2"
            >
              <div className="min-w-0">
                <p className="font-mono text-xs font-medium">{d.name}</p>
                <p className="break-words text-xs text-muted">{d.note}</p>
              </div>
              <span className="shrink-0 font-mono text-xs text-subtle">
                {d.mail}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
