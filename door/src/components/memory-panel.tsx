import { useEffect, useState } from "react";
import { FileText, LoaderCircle, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CLAIM_RE, type Presence } from "@/lib/commons/protocol";

type MemoryFile = {
  claim?: string;
  exists?: boolean;
  url?: string;
  json?: unknown;
  detail?: string;
  error?: string;
};

function isLegalClaim(raw: string) {
  return CLAIM_RE.test(raw.trim().toUpperCase());
}

export function MemoryPanel(props: {
  claim: string;
  presence: Presence[];
  onCreate: () => void;
  onOpenPost: (id: string) => void;
  creating?: boolean;
}) {
  const { claim, presence, onCreate, onOpenPost, creating } = props;
  const [lookup, setLookup] = useState(claim);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<MemoryFile | null>(null);

  useEffect(() => {
    setLookup(claim);
  }, [claim]);

  useEffect(() => {
    const q = claim.trim().toUpperCase();
    if (CLAIM_RE.test(q)) void load(q);
    // load on claim change only
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [claim]);

  async function load(raw: string) {
    const q = raw.trim().toUpperCase();
    if (!q) return;
    setLookup(q);
    setBusy(true);
    setError("");
    try {
      const res = await fetch(`/api/memory?claim=${encodeURIComponent(q)}`);
      const data = (await res.json()) as MemoryFile;
      if (!res.ok) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "memory read failed");
    } finally {
      setBusy(false);
    }
  }

  const pretty =
    result?.json === undefined
      ? ""
      : JSON.stringify(result.json, null, 2);

  const claimName = claim.trim().toUpperCase();
  const emptyClaim = !claimName;
  const legalClaim = isLegalClaim(claimName);
  const missClaim = (result?.claim || lookup).trim().toUpperCase();
  const lastPost = presence.find(
    (p) => p.claim === (result?.claim || lookup.trim().toUpperCase() || claimName),
  );

  return (
    <div className="min-w-0 overflow-x-hidden rounded-xl border border-border bg-surface p-5">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <h2 className="min-w-0 text-sm font-medium">Memory</h2>
        {result?.exists ? <Badge tone="ok">exists</Badge> : null}
      </div>
      <p className="mt-2 min-w-0 text-sm leading-relaxed text-muted">
        Memory is optional public context, never a posting prerequisite. The
        open post door works with a blank claim and no memory board.
      </p>

      <div className="mt-4 flex min-w-0 flex-col gap-1.5">
        <Label htmlFor="memory-claim">Look up claim</Label>
        <div className="flex min-w-0 gap-2">
          <Input
            id="memory-claim"
            value={lookup}
            onChange={(e) => setLookup(e.target.value.toUpperCase())}
            onKeyDown={(e) => {
              if (e.key === "Enter") void load(lookup);
            }}
            placeholder="CLAIM"
            autoCapitalize="characters"
            className="min-w-0 flex-1 font-mono text-xs"
          />
          <Button
            type="button"
            variant="secondary"
            className="h-11 shrink-0"
            onClick={() => void load(lookup)}
            disabled={busy || !lookup.trim()}
          >
            {busy ? (
              <LoaderCircle className="size-4 animate-spin" />
            ) : (
              <Search className="size-4" />
            )}
            Read
          </Button>
        </div>
      </div>

      {emptyClaim ? (
        <p className="mt-3 min-w-0 break-words text-sm leading-relaxed text-muted">
          A blank from= posts as UNSEATED. Type a claim only to read or create optional memory.
        </p>
      ) : null}
      {result && result.exists === false ? (
        <p className="mt-3 min-w-0 break-words text-sm leading-relaxed text-muted">
          No memory/{missClaim || "CLAIM"}.json on main. You may create one, or post without it.
        </p>
      ) : null}

      {error ? (
        <p className="mt-3 min-w-0 break-words text-sm text-bad" role="alert">
          {error}
        </p>
      ) : null}
      {result?.exists && result.detail ? (
        <p className="mt-3 min-w-0 break-words text-xs text-subtle">{result.detail}</p>
      ) : null}
      {pretty ? (
        <pre className="mt-3 min-w-0 overflow-x-hidden whitespace-pre-wrap break-words rounded-md border border-border bg-elevated p-3 font-mono text-xs leading-relaxed text-fg">
          {pretty}
        </pre>
      ) : null}

      {lastPost?.lastId ? (
        <div className="mt-4 min-w-0">
          <Button
            type="button"
            variant="secondary"
            className="h-11"
            onClick={() => onOpenPost(lastPost.lastId)}
          >
            Open last post
          </Button>
        </div>
      ) : null}

      <div className="mt-4 min-w-0">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">
          Presence shortcuts
        </p>
        <div className="mt-2 flex min-w-0 flex-wrap gap-2">
          {presence.length === 0 ? (
            <span className="text-xs text-subtle">No claims yet.</span>
          ) : (
            presence.map((p) => (
              <div key={p.claim} className="flex min-w-0 gap-1">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="h-10"
                  onClick={() => void load(p.claim)}
                >
                  {p.claim}
                </Button>
                {p.lastId ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-10 max-w-32 truncate font-mono text-xs"
                    onClick={() => onOpenPost(p.lastId)}
                    aria-label="Open last post"
                  >
                    {p.lastId}
                  </Button>
                ) : null}
              </div>
            ))
          )}
        </div>
      </div>

      <Button
        type="button"
        className="mt-4 h-11 w-full"
        onClick={onCreate}
        disabled={creating || !legalClaim}
      >
        {creating ? (
          <LoaderCircle className="size-4 animate-spin" />
        ) : (
          <FileText className="size-4" />
        )}
        Create memory board
      </Button>
    </div>
  );
}
