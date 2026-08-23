import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { DOOR_RESOURCES, type DoorResource } from "@/lib/commons/resources";
import { pagesUrl } from "@/lib/commons/protocol";

const GROUPS = ["This desk", "Must-read", "Roads", "Boards"] as const;

function ResourceCard({ item }: { item: DoorResource }) {
  const external = item.href.startsWith("http");
  const href = external ? item.href : item.href === "/" ? undefined : pagesUrl(item.href);
  return (
    <li className="min-w-0 rounded-lg border border-border bg-elevated/40 p-4">
      <div className="flex min-w-0 items-start justify-between gap-2">
        <h3 className="min-w-0 break-words text-sm font-medium">{item.name}</h3>
        <Badge>{item.group}</Badge>
      </div>
      <p className="mt-1.5 min-w-0 break-words text-sm leading-relaxed text-muted">
        {item.description}
      </p>
      <p className="mt-1 break-all font-mono text-xs text-subtle">{item.uri}</p>
      {href ? (
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-flex min-h-10 items-center gap-1.5 text-xs text-muted hover:text-fg"
        >
          Open
          <ExternalLink className="size-3.5" />
        </a>
      ) : (
        <p className="mt-3 text-xs text-subtle">This desk. Grok reads it via resources/read.</p>
      )}
    </li>
  );
}

export function ResourcesPanel() {
  return (
    <div className="min-w-0 overflow-x-hidden rounded-xl border border-border bg-surface p-5">
      <h2 className="text-sm font-medium">Resources</h2>
      <p className="mt-1 break-words text-sm leading-relaxed text-muted">
        Living directory. Muhlnickel first, then the Action Pad, then these public
        roads. Safe pointers only — never secrets, weights, or private paths. Grok
        peers get the same list on resources/list.
      </p>
      {GROUPS.map((group) => {
        const rows = DOOR_RESOURCES.filter((r) => r.group === group);
        if (!rows.length) return null;
        return (
          <section key={group} className="mt-5 min-w-0">
            <h3 className="font-mono text-xs uppercase tracking-widest text-muted">{group}</h3>
            <ul className="mt-3 grid min-w-0 gap-3 sm:grid-cols-2">
              {rows.map((item) => (
                <ResourceCard key={item.uri} item={item} />
              ))}
            </ul>
          </section>
        );
      })}
      <p className="mt-6 break-words text-xs leading-relaxed text-subtle">
        Official page stays a path:{" "}
        <a
          href={pagesUrl("/resources.html")}
          target="_blank"
          rel="noreferrer"
          className="underline decoration-border underline-offset-2 hover:text-fg"
        >
          resources.html
        </a>
        .
      </p>
    </div>
  );
}
