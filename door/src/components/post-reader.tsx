import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { ExternalLink, LoaderCircle, Reply, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type FilePayload = {
  id: string;
  durable: boolean;
  markdown: string;
  from?: string;
  to?: string;
  file_url: string;
  pin_url: string;
  pages_url: string;
  detail: string;
  error?: string;
};

export function PostReader(props: {
  id: string | null;
  onClose: () => void;
  onReply: (id: string, from: string, to: string) => void;
}) {
  const { id, onClose, onReply } = props;
  const [file, setFile] = useState<FilePayload | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!id) {
      setFile(null);
      setError("");
      return;
    }
    const ac = new AbortController();
    setBusy(true);
    setError("");
    setFile(null);
    void (async () => {
      try {
        const res = await fetch(`/api/file?id=${encodeURIComponent(id)}`, {
          signal: ac.signal,
        });
        const data = (await res.json()) as FilePayload;
        if (ac.signal.aborted) return;
        if (!res.ok) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
        setFile(data);
      } catch (err) {
        if (ac.signal.aborted) return;
        setError(err instanceof Error ? err.message : "read failed");
      } finally {
        if (!ac.signal.aborted) setBusy(false);
      }
    })();
    return () => ac.abort();
  }, [id]);

  useEffect(() => {
    if (!id) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [id, onClose]);

  if (!id || !mounted) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[80] flex items-start justify-center overflow-y-auto bg-bg/85 px-3 py-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="post-reader-title"
      onClick={onClose}
    >
      <div
        className="w-full min-w-0 max-w-3xl overflow-x-hidden rounded-xl border border-border bg-surface p-5 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-mono text-xs uppercase tracking-widest text-muted">File</p>
            <h2
              id="post-reader-title"
              className="mt-1 break-all font-mono text-sm font-medium text-fg"
            >
              {id}
            </h2>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-10 shrink-0"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="size-4" />
          </Button>
        </div>

        {busy ? (
          <p className="mt-8 flex min-w-0 items-start gap-2 text-sm text-muted">
            <LoaderCircle className="mt-0.5 size-4 shrink-0 animate-spin" />
            <span className="min-w-0 break-all font-mono text-xs">Reading p/{id}.md</span>
          </p>
        ) : error ? (
          <p className="mt-6 min-w-0 break-words text-sm text-bad" role="alert">
            {error}
          </p>
        ) : file ? (
          <>
            <div className="mt-4 flex min-w-0 flex-wrap items-center gap-2">
              <Badge tone={file.durable ? "ok" : "warn"}>
                {file.durable ? "DURABLE_PAGE" : "MISSING"}
              </Badge>
              {file.from ? (
                <span className="min-w-0 break-words font-medium">
                  {file.from} → {file.to || "TABLE"}
                </span>
              ) : null}
            </div>
            <p className="mt-2 min-w-0 break-words font-mono text-xs text-subtle">{file.detail}</p>
            <pre
              className={cn(
                "mt-4 max-h-[55dvh] min-w-0 overflow-auto whitespace-pre-wrap break-words rounded-md border border-border bg-elevated p-3",
                "font-mono text-sm leading-relaxed text-fg",
              )}
            >
              {file.markdown || "(empty file)"}
            </pre>
            <div className="mt-4 flex min-w-0 flex-wrap gap-2">
              <Button
                type="button"
                variant="secondary"
                className="h-10"
                onClick={() => onReply(file.id, file.from || "", file.to || "TABLE")}
              >
                <Reply className="size-3.5" />
                Reply
              </Button>
              <Button variant="ghost" className="h-10" asChild>
                <a href={file.file_url} target="_blank" rel="noreferrer">
                  file
                  <ExternalLink className="size-3.5" />
                </a>
              </Button>
              <Button variant="ghost" className="h-10" asChild>
                <a href={file.pin_url} target="_blank" rel="noreferrer">
                  pin
                  <ExternalLink className="size-3.5" />
                </a>
              </Button>
              <Button variant="ghost" className="h-10" asChild>
                <a href={file.pages_url} target="_blank" rel="noreferrer">
                  pages
                  <ExternalLink className="size-3.5" />
                </a>
              </Button>
            </div>
          </>
        ) : null}
      </div>
    </div>,
    document.body,
  );
}
