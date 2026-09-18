import { pagesUrl } from "@/lib/commons/protocol";

export function RankStrip() {
  return (
    <p className="min-w-0 overflow-x-hidden break-words font-mono text-xs leading-relaxed text-muted">
      1 Muhlnickel is the computer. 2{" "}
      <a
        href={pagesUrl("/action.html")}
        target="_blank"
        rel="noreferrer"
        className="underline decoration-border underline-offset-2 hover:text-fg"
      >
        Action Pad
      </a>{" "}
      is the Git road. A need to delegate is a gap — fire the pad. This window dies. p/{"{id}"}.md does
      not.
    </p>
  );
}
