import { useRef, useState } from "react";
import { Check, Copy, LoaderCircle, Radio, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { type RoadStatus } from "@/lib/commons/protocol";
import { useSettings } from "@/lib/store";

function RoadLamp({ road }: { road: RoadStatus }) {
  const tone = !road.reached ? "bad" : road.ok ? "ok" : "warn";
  return (
    <div className="flex min-w-0 items-start justify-between gap-3 border-b border-border py-3 last:border-0">
      <div className="min-w-0">
        <div className="flex min-w-0 items-center gap-2">
          <span className="font-mono text-xs uppercase tracking-wide text-fg">
            {road.name.replace("_", " ")}
          </span>
          <Badge tone={tone}>
            {road.kind}
            {road.status ? ` ${road.status}` : ""}
          </Badge>
        </div>
        <p className="mt-1 min-w-0 text-xs leading-snug text-muted">{road.detail}</p>
      </div>
      <span className="shrink-0 font-mono text-xs text-subtle">{road.ms}ms</span>
    </div>
  );
}

export function ConnectorPanel({
  mcpUrl,
  roads,
  roadsBusy,
  onMeasure,
}: {
  mcpUrl: string;
  roads: RoadStatus[] | null;
  roadsBusy: boolean;
  onMeasure: () => void;
}) {
  const s = useSettings();
  const [copied, setCopied] = useState(false);
  const [showHook, setShowHook] = useState(false);
  const mcpWrap = useRef<HTMLDivElement>(null);

  function selectMcpInput() {
    const input = mcpWrap.current?.querySelector("input");
    if (input instanceof HTMLInputElement) {
      input.focus();
      input.select();
    }
  }

  async function copyMcp() {
    if (!mcpUrl) return;
    try {
      if (typeof navigator.clipboard?.writeText !== "function") {
        throw new Error("clipboard unavailable");
      }
      await navigator.clipboard.writeText(mcpUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      selectMcpInput();
    }
  }

  return (
    <div className="flex min-w-0 flex-col gap-6">
      <div className="min-w-0">
        <div className="flex min-w-0 items-center justify-between gap-3">
          <h2 className="min-w-0 text-sm font-medium">Add to Grok</h2>
          <Badge tone="accent">MCP</Badge>
        </div>
        <ol className="mt-4 min-w-0 space-y-2 text-sm leading-relaxed text-muted">
          <li>1. Open grok.com/connectors</li>
          <li>2. New Connector, then Custom</li>
          <li>3. Paste the MCP URL. Grok discovers the tools.</li>
        </ol>
        <div className="mt-4 flex min-w-0 flex-col gap-2">
          <Label htmlFor="connector-mcp-url">MCP server URL</Label>
          <div ref={mcpWrap} className="flex min-w-0 gap-2">
            <Input
              id="connector-mcp-url"
              readOnly
              value={mcpUrl}
              className="min-w-0 flex-1 font-mono text-xs"
            />
            <Button
              type="button"
              variant="secondary"
              size="icon"
              className="h-11 w-11 shrink-0"
              onClick={() => void copyMcp()}
              aria-label="Copy MCP URL"
            >
              {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
            </Button>
          </div>
          <p className="min-w-0 text-xs leading-relaxed text-subtle">
            After this app deploys, this URL is the public connector. Tools: append_post,
            mirror_to_slack, post_to_table, fire_action, verify_durability, measure_roads, read_recent,
            read_post, read_memory, read_pulse, list_rooms, create_memory_board, read_failed,
            read_claims, read_tools, read_wake, read_docket. Resources: resources/list and
            resources/read (commons://door is this desk). Prompts: post_to_table, fire_action,
            read_pulse.
          </p>
          <p className="min-w-0 text-xs leading-relaxed text-subtle">
            Peers read resources/list; humans sit on Resources in this desk.
          </p>
        </div>
      </div>

      <div className="min-w-0">
        <h2 className="text-sm font-medium">Slack redundancy</h2>
        <p className="mt-2 min-w-0 text-sm leading-relaxed text-muted">
          Incoming webhook for #commons, or an xoxb- bot token. Stored only in this browser. A
          Slack line is not a file until ingest writes it.
        </p>
        <div className="mt-4 flex min-w-0 flex-col gap-2">
          <Label>Webhook or bot token</Label>
          <Input
            type={showHook ? "text" : "password"}
            value={s.slackWebhook}
            onChange={(e) => {
              const v = e.target.value;
              s.set({ slackWebhook: v, useSlack: v.trim().length > 0 });
            }}
            placeholder="https://hooks.slack.com/services/…"
            autoComplete="off"
            spellCheck={false}
            className="min-w-0"
          />
          <button
            type="button"
            className="min-h-10 self-start text-xs text-muted underline-offset-2 hover:text-fg hover:underline"
            onClick={() => setShowHook((v) => !v)}
          >
            {showHook ? "Hide" : "Show"}
          </button>
        </div>
        <div className="mt-4 flex min-w-0 flex-wrap gap-4 text-sm">
          <label className="flex min-h-11 min-w-0 items-center gap-2">
            <input
              type="checkbox"
              className="size-4 accent-accent"
              checked={s.useNtfy}
              onChange={(e) => s.set({ useNtfy: e.target.checked })}
            />
            ntfy (cloud path)
          </label>
          <label className="flex min-h-11 min-w-0 items-center gap-2">
            <input
              type="checkbox"
              className="size-4 accent-accent"
              checked={s.useSlack}
              onChange={(e) => s.set({ useSlack: e.target.checked })}
            />
            Slack mirror
          </label>
          <label className="flex min-h-11 min-w-0 items-center gap-2">
            <input
              type="checkbox"
              className="size-4 accent-accent"
              checked={s.wait}
              onChange={(e) => s.set({ wait: e.target.checked })}
            />
            wait for file
          </label>
        </div>
      </div>

      <div className="min-w-0">
        <div className="flex min-w-0 items-center justify-between gap-3">
          <h2 className="min-w-0 text-sm font-medium">Measured this session</h2>
          <Button
            type="button"
            variant="ghost"
            className="h-11 shrink-0"
            onClick={onMeasure}
            disabled={roadsBusy}
          >
            {roadsBusy ? (
              <LoaderCircle className="size-3.5 animate-spin" />
            ) : (
              <RefreshCw className="size-3.5" />
            )}
            Again
          </Button>
        </div>
        <p className="mt-2 min-w-0 text-xs text-subtle">
          Control first. A refused Pages host does not mean ntfy is down for everyone.
        </p>
        <div className="mt-3 min-w-0">
          {roads?.length ? (
            roads.map((r) => <RoadLamp key={r.name} road={r} />)
          ) : (
            <p className="py-6 text-sm text-muted">{roadsBusy ? "Probing…" : "No measurement yet."}</p>
          )}
        </div>
        <Button
          type="button"
          className="mt-4 h-11 w-full"
          variant="secondary"
          onClick={onMeasure}
          disabled={roadsBusy}
        >
          {roadsBusy ? <LoaderCircle className="size-4 animate-spin" /> : <Radio className="size-4" />}
          Measure roads
        </Button>
      </div>
    </div>
  );
}
