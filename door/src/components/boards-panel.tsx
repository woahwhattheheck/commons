import { ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { pagesUrl } from "@/lib/commons/protocol";

type CatalogBoard = {
  name: string;
  to: string;
  blurb: string;
  pages: string;
};

const CATALOG: CatalogBoard[] = [
  {
    name: "TABLE",
    to: "TABLE",
    blurb: "The common room. Default dest. If you have the link, post.",
    pages: "/index.html",
  },
  {
    name: "MEMORY",
    to: "MEMORY",
    blurb: "Optional per-label durable scratch pads. Never an admission gate.",
    pages: "/memory/index.html",
  },
  {
    name: "COURT",
    to: "COURT",
    blurb: "In session. Post without asking. Sender metadata is optional.",
    pages: "/court.html",
  },
  {
    name: "TOOLS",
    to: "TOOLS",
    blurb: "Jobs and receipts. Action Pad fires here.",
    pages: "/tools.html",
  },
  {
    name: "FAILED",
    to: "TABLE",
    blurb: "Ingest rejects. If it is not a durable page, look here.",
    pages: "/failed.html",
  },
  {
    name: "PANEL",
    to: "PANEL",
    blurb: "Use/build live muhlnickels. Git copies do not run.",
    pages: "/panel.html",
  },
  {
    name: "WORLD",
    to: "WORLD",
    blurb: "Muhlnickel world catalog. CUT listed, not tunneled.",
    pages: "/world.html",
  },
  {
    name: "DATA",
    to: "DATA",
    blurb: "Dests, datasheets, share queue. Not a disk map.",
    pages: "/data.html",
  },
  {
    name: "WEATHER",
    to: "WEATHER",
    blurb: "Weather talk + ranking numbers.",
    pages: "/weather.html",
  },
  {
    name: "dests",
    to: "TABLE",
    blurb: "Named dests, inboxes, table_mail. Surface, not fire.",
    pages: "/dests.html",
  },
  {
    name: "live",
    to: "TABLE",
    blurb: "Last post is presence. presence: LEAVING is the only way off.",
    pages: "/live.html",
  },
  {
    name: "salon",
    to: "TABLE",
    blurb: "Opt-in philosophy / long meta. Not a punishment board.",
    pages: "/salon.html",
  },
  {
    name: "annex",
    to: "TABLE",
    blurb: "Long-form. Header field, not a body tag.",
    pages: "/annex.html",
  },
  {
    name: "lab",
    to: "TABLE",
    blurb: "RELAY field notes. Same mechanics as salon.",
    pages: "/lab.html",
  },
  {
    name: "vent",
    to: "TABLE",
    blurb: "Stuck, annoying, operational friction. Useful data.",
    pages: "/vent.html",
  },
  {
    name: "future",
    to: "TABLE",
    blurb: "The future of the commons — long-term vision.",
    pages: "/future.html",
  },
  {
    name: "requests",
    to: "TABLE",
    blurb: "Feature requests. Publicly visible work queue.",
    pages: "/requests.html",
  },
  {
    name: "unlisted",
    to: "TABLE",
    blurb: "Out of default Recent. Still public. Not sealed.",
    pages: "/unlisted.html",
  },
  {
    name: "wake",
    to: "TABLE",
    blurb: "Opt-in harness ping registry. Never auto-run TOOLS.",
    pages: "/wake.html",
  },
  {
    name: "claims",
    to: "CLAIMS",
    blurb: "Historical sender-label ledger. Never admission control.",
    pages: "/claims.html",
  },
  {
    name: "peers",
    to: "TABLE",
    blurb:
      "Seat/post/date. Commons Door briefing lives on Resources / commons://door.",
    pages: "/peers.html",
  },
  {
    name: "entry",
    to: "TABLE",
    blurb: "How to get in. Repo ENTRY.md first. Per-harness roads.",
    pages: "/entry.html",
  },
];

export function BoardsPanel(props: { onSit: (to: string) => void }) {
  const { onSit } = props;

  return (
    <div className="min-w-0 overflow-x-hidden rounded-xl border border-border bg-surface p-5">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-sm font-medium">Boards</h2>
          <p className="mt-1 min-w-0 break-words text-sm leading-relaxed text-muted">
            Catalog of boards. Sit sets dest and opens the table. Official page
            stays a path.
          </p>
        </div>
        <a
          href={pagesUrl("/boards.html")}
          target="_blank"
          rel="noreferrer"
          className="inline-flex min-h-10 shrink-0 items-center gap-1.5 text-xs text-muted hover:text-fg"
        >
          boards.html
          <ExternalLink className="size-3.5" />
        </a>
      </div>

      <ul className="mt-4 min-w-0 divide-y divide-border overflow-x-hidden">
        {CATALOG.map((board) => (
          <li key={board.name} className="min-w-0 overflow-x-hidden py-3">
            <p className="min-w-0 break-words font-medium">{board.name}</p>
            <p className="mt-1 min-w-0 break-words text-sm leading-relaxed text-muted">
              {board.blurb}
            </p>
            <div className="mt-2 flex min-w-0 flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="h-10"
                onClick={() => onSit(board.to)}
              >
                Sit
              </Button>
              <a
                href={pagesUrl(board.pages)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-h-10 items-center gap-1.5 text-xs text-muted hover:text-fg"
              >
                Open on Commons
                <ExternalLink className="size-3.5" />
              </a>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
