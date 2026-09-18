import { COMMONS_PAGES } from "./protocol";

const UA = "commons-door-connector/1.0";
const ITEM_CAP = 40;
const TIMEOUT_MS = 12000;

export type LedgerKind = "failed" | "claims" | "tools" | "wake";

export const LEDGER_KINDS: readonly LedgerKind[] = [
  "failed",
  "claims",
  "tools",
  "wake",
];

const KIND_FILE: Record<LedgerKind, string> = {
  failed: "rejects.json",
  claims: "claims.json",
  tools: "tools.json",
  wake: "wake.json",
};

const KIND_KEYS: Record<LedgerKind, string[]> = {
  failed: ["rejects", "items"],
  claims: ["claims", "items"],
  tools: ["tools", "items"],
  wake: ["requests", "items"],
};

export function isLedgerKind(value: string): value is LedgerKind {
  return (LEDGER_KINDS as readonly string[]).includes(value);
}

async function timedFetch(
  url: string,
  init: RequestInit,
  timeoutMs = TIMEOUT_MS,
): Promise<{ res?: Response; error?: string; ms: number }> {
  const t0 = Date.now();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      ...init,
      signal: ctrl.signal,
      headers: { "user-agent": UA, ...(init.headers || {}) },
    });
    return { res, ms: Date.now() - t0 };
  } catch (err) {
    const msg = err instanceof Error ? err.message : "fetch failed";
    const connect = /abort|connect|ENOTFOUND|ECONNREFUSED|fetch failed/i.test(msg);
    return {
      error: connect ? `CONNECT refused or timed out: ${msg}` : msg,
      ms: Date.now() - t0,
    };
  } finally {
    clearTimeout(timer);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function asRecords(rows: unknown[]): Record<string, unknown>[] {
  return rows.filter(isRecord);
}

function normalizeItems(
  data: unknown,
  preferredKeys: string[] = [],
): Record<string, unknown>[] {
  if (Array.isArray(data)) return asRecords(data);
  if (!isRecord(data)) return [];
  if (Array.isArray(data.items)) return asRecords(data.items);
  for (const key of preferredKeys) {
    const row = data[key];
    if (Array.isArray(row)) return asRecords(row);
  }
  const values = Object.values(data);
  if (values.length && values.every(isRecord)) return values;
  let best: Record<string, unknown>[] = [];
  for (const value of values) {
    if (!Array.isArray(value)) continue;
    const recs = asRecords(value);
    if (recs.length > best.length) best = recs;
  }
  return best;
}

function cap(items: Record<string, unknown>[]): Record<string, unknown>[] {
  return items.slice(0, ITEM_CAP);
}

type Bake = {
  ok: boolean;
  data?: unknown;
  status?: number;
  ms: number;
  error?: string;
  path: string;
};

async function fetchBake(path: string): Promise<Bake> {
  const url = `${COMMONS_PAGES}/${path.replace(/^\//, "")}`;
  const { res, error, ms } = await timedFetch(url, {
    headers: { accept: "application/json" },
  });
  if (error) return { ok: false, error, ms, path };
  if (!res) return { ok: false, error: `${path} no response`, ms, path };
  const ct = (res.headers.get("content-type") || "").toLowerCase();
  if (ct.includes("text/html")) {
    return {
      ok: false,
      status: res.status,
      ms,
      path,
      error: `${path} is HTML, skipped`,
    };
  }
  if (!res.ok) {
    return {
      ok: false,
      status: res.status,
      ms,
      path,
      error: `${path} HTTP ${res.status} (${ms}ms)`,
    };
  }
  try {
    const data = await res.json();
    return { ok: true, data, status: res.status, ms, path };
  } catch {
    return {
      ok: false,
      status: res.status,
      ms,
      path,
      error: `${path} unparseable JSON`,
    };
  }
}

function empty(
  kind: LedgerKind,
  detail: string,
): {
  kind: LedgerKind;
  items: Record<string, unknown>[];
  detail: string;
} {
  return { kind, items: [], detail };
}

async function readFailed(): Promise<{
  kind: LedgerKind;
  items: Record<string, unknown>[];
  detail: string;
}> {
  const rejects = await fetchBake("rejects.json");
  if (rejects.ok) {
    const items = cap(normalizeItems(rejects.data, KIND_KEYS.failed));
    if (items.length) {
      return {
        kind: "failed",
        items,
        detail: `rejects.json bake · ${items.length} items (${rejects.ms}ms). Bake, not HEAD. skipped failed.html (HTML).`,
      };
    }
  }
  const gaps = await fetchBake("durable_gaps.json");
  if (gaps.ok) {
    const items = cap(normalizeItems(gaps.data, ["items"]));
    const rejectNote = rejects.ok
      ? "rejects.json empty"
      : rejects.error || "rejects.json failed";
    return {
      kind: "failed",
      items,
      detail: `${rejectNote}; durable_gaps.json bake · ${items.length} items (${gaps.ms}ms). Bake, not HEAD. skipped failed.html (HTML).`,
    };
  }
  return empty(
    "failed",
    rejects.error ||
      gaps.error ||
      "failed ledger unavailable. skipped failed.html (HTML).",
  );
}

export async function readLedger(kind: LedgerKind): Promise<{
  kind: LedgerKind;
  items: Record<string, unknown>[];
  detail: string;
}> {
  try {
    if (kind === "failed") return await readFailed();
    const file = KIND_FILE[kind];
    const bake = await fetchBake(file);
    if (!bake.ok) {
      return empty(kind, bake.error || `${file} failed`);
    }
    const items = cap(normalizeItems(bake.data, KIND_KEYS[kind]));
    return {
      kind,
      items,
      detail: `${file} bake · ${items.length} items (${bake.ms}ms). Bake, not HEAD.`,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : "ledger read failed";
    return empty(kind, msg);
  }
}
