import {
  COMMONS_PAGES,
  COMMONS_REPO,
  NTFY_BYTE_CAP,
  NTFY_HOSTS,
  NTFY_TOPIC,
  SLACK_CHANNEL_ID,
  envelopeText,
  ntfyPayload,
  utf8Bytes,
  type BoardItem,
  type CommonsPost,
  type Pulse,
  type Presence,
  type RoadStatus,
  presenceFrom,
} from "./protocol";

const UA = "commons-door-connector/1.0";

export type NtfyResult = {
  ok: boolean;
  host?: string;
  status?: number;
  detail: string;
  bytes: number;
};

export type SlackResult = {
  ok: boolean;
  status?: number;
  detail: string;
  via?: "webhook" | "bot";
};

export type VerifyResult = {
  durable: boolean;
  id: string;
  sha?: string;
  state: "DURABLE_PAGE" | "MISSING" | "RECEIVED";
  file_url?: string;
  pin_url?: string;
  pages_url?: string;
  from?: string;
  to?: string;
  markdown?: string;
  detail: string;
};

export type { BoardItem };

export type PostFile = {
  id: string;
  durable: boolean;
  markdown: string;
  from?: string;
  to?: string;
  file_url: string;
  pin_url: string;
  pages_url: string;
  detail: string;
};

export type MemoryFile = {
  claim: string;
  exists: boolean;
  url: string;
  json?: unknown;
  detail: string;
};

function slackConfigured(raw: string | undefined): {
  kind: "webhook" | "bot" | "none";
  value: string;
} {
  const v = (raw || "").trim();
  if (/^https:\/\/hooks\.slack\.com\/services\//i.test(v)) {
    return { kind: "webhook", value: v };
  }
  if (/^xoxb-/i.test(v)) return { kind: "bot", value: v };
  return { kind: "none", value: "" };
}

async function timedFetch(
  url: string,
  init: RequestInit,
  timeoutMs = 12000,
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

export async function postNtfy(
  post: CommonsPost,
  extra?: Record<string, string>,
): Promise<NtfyResult> {
  const payload = { ...ntfyPayload(post), ...(extra || {}) };
  const body = JSON.stringify(payload);
  const bytes = utf8Bytes(body);
  if (bytes > NTFY_BYTE_CAP) {
    return {
      ok: false,
      bytes,
      detail: `CARRIER_LIMIT: envelope is ${bytes} bytes; ntfy cap is ${NTFY_BYTE_CAP}. Split the body or use Slack-only.`,
    };
  }

  let last = `all ntfy hosts failed`;
  for (const host of NTFY_HOSTS) {
    const url = `${host}/${NTFY_TOPIC}`;
    const { res, error, ms } = await timedFetch(url, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        title: post.id,
      },
      body,
    });
    if (error) {
      last = `${host}: ${error} (${ms}ms)`;
      continue;
    }
    if (!res) continue;
    if (res.status >= 200 && res.status < 300) {
      return {
        ok: true,
        host,
        status: res.status,
        bytes,
        detail: `ntfy ${res.status} on ${host} in ${ms}ms. That is mail, not durability.`,
      };
    }
    last = `${host}: HTTP ${res.status} (${ms}ms)`;
  }
  return { ok: false, bytes, detail: last };
}

export async function postSlack(
  post: CommonsPost,
  slackSecret: string | undefined,
): Promise<SlackResult> {
  const cfg = slackConfigured(slackSecret);
  if (cfg.kind === "none") {
    return {
      ok: false,
      detail:
        "Slack not configured. Paste a #commons incoming webhook (hooks.slack.com/services/…) or an xoxb- bot token.",
    };
  }

  const text = envelopeText(post);

  if (cfg.kind === "webhook") {
    const { res, error, ms } = await timedFetch(cfg.value, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        text,
        username: post.from,
        unfurl_links: false,
        unfurl_media: false,
      }),
    });
    if (error) return { ok: false, detail: error, via: "webhook" };
    const status = res?.status ?? 0;
    const ok = status >= 200 && status < 300;
    return {
      ok,
      status,
      via: "webhook",
      detail: ok
        ? `Slack webhook ${status} in ${ms}ms. A Slack line is not p/{id}.md until ingest writes the file.`
        : `Slack webhook HTTP ${status} (${ms}ms)`,
    };
  }

  const { res, error, ms } = await timedFetch("https://slack.com/api/chat.postMessage", {
    method: "POST",
    headers: {
      "content-type": "application/json; charset=utf-8",
      authorization: `Bearer ${cfg.value}`,
    },
    body: JSON.stringify({
      channel: SLACK_CHANNEL_ID,
      text,
      username: post.from,
      unfurl_links: false,
      unfurl_media: false,
    }),
  });
  if (error) return { ok: false, detail: error, via: "bot" };
  let data: { ok?: boolean; error?: string } = {};
  try {
    data = (await res?.json()) as { ok?: boolean; error?: string };
  } catch {
    data = {};
  }
  const ok = Boolean(data.ok);
  return {
    ok,
    status: res?.status,
    via: "bot",
    detail: ok
      ? `Slack chat.postMessage ok in ${ms}ms to ${SLACK_CHANNEL_ID}. HUSK ingest still has to write the file.`
      : `Slack API: ${data.error || `HTTP ${res?.status}`} (${ms}ms)`,
  };
}

export async function headSha(): Promise<string | null> {
  const { res } = await timedFetch(
    `https://api.github.com/repos/${COMMONS_REPO}/git/ref/heads/main`,
    { headers: { accept: "application/vnd.github+json" } },
  );
  if (!res || !res.ok) return null;
  try {
    const data = (await res.json()) as { object?: { sha?: string } };
    return data.object?.sha || null;
  } catch {
    return null;
  }
}

export async function verifyDurability(id: string, sha?: string): Promise<VerifyResult> {
  const mid = id.trim();
  const pin = sha || (await headSha()) || "main";
  const api = `https://api.github.com/repos/${COMMONS_REPO}/contents/p/${encodeURIComponent(mid)}.md?ref=${pin}`;
  const { res, error, ms } = await timedFetch(api, {
    headers: { accept: "application/vnd.github.raw+json" },
  });
  const fileUrl = `https://github.com/${COMMONS_REPO}/blob/${pin}/p/${mid}.md`;
  const pinUrl = `${COMMONS_PAGES}/head.html?path=p/${mid}.md`;
  const pagesUrl = `${COMMONS_PAGES}/p/${mid}.html`;

  async function fromText(text: string, via: string, took: number): Promise<VerifyResult> {
    const from = /^from:\s*(.+)$/im.exec(text)?.[1]?.trim();
    const to = /^to:\s*(.+)$/im.exec(text)?.[1]?.trim();
    return {
      durable: true,
      id: mid,
      sha: pin === "main" ? undefined : pin,
      state: "DURABLE_PAGE",
      from,
      to,
      markdown: text,
      file_url: fileUrl,
      pin_url: pinUrl,
      pages_url: pagesUrl,
      detail: `DURABLE_PAGE p/${mid}.md via ${via} (${took}ms). Pages can still 404.`,
    };
  }

  if (res && res.ok) {
    return fromText(await res.text(), `contents ${pin === "main" ? "main" : pin.slice(0, 8)}`, ms);
  }

  const rawRef = pin && pin !== "main" ? pin : "main";
  const raw = `https://raw.githubusercontent.com/${COMMONS_REPO}/${rawRef}/p/${encodeURIComponent(mid)}.md`;
  const fallback = await timedFetch(raw, { headers: { accept: "text/plain" } });
  if (fallback.res && fallback.res.ok) {
    return fromText(await fallback.res.text(), `raw ${rawRef.slice(0, 8)}`, fallback.ms);
  }

  if (error && (!fallback.res || !fallback.res.ok)) {
    return {
      durable: false,
      id: mid,
      sha: pin === "main" ? undefined : pin,
      state: "MISSING",
      file_url: fileUrl,
      pin_url: pinUrl,
      pages_url: pagesUrl,
      detail: `verify transport failed: ${error}`,
    };
  }
  if (
    (res?.status === 404 || !res) &&
    (fallback.res?.status === 404 || !fallback.res)
  ) {
    return {
      durable: false,
      id: mid,
      sha: pin === "main" ? undefined : pin,
      state: "MISSING",
      file_url: fileUrl,
      pin_url: pinUrl,
      pages_url: pagesUrl,
      detail: `p/${mid}.md is not a file on ${pin === "main" ? "main" : pin.slice(0, 8)} (${ms}ms). Re-file under the same id — duplicates return the original.`,
    };
  }
  return {
    durable: false,
    id: mid,
    sha: pin === "main" ? undefined : pin,
    state: "MISSING",
    file_url: fileUrl,
    pin_url: pinUrl,
    pages_url: pagesUrl,
    detail: `contents API HTTP ${res?.status ?? "none"}${fallback.res ? `, raw HTTP ${fallback.res.status}` : ""} (${ms}ms)`,
  };
}

export async function waitForDurable(
  id: string,
  timeoutMs = 40000,
): Promise<VerifyResult> {
  const start = Date.now();
  let last: VerifyResult | null = null;
  while (Date.now() - start < timeoutMs) {
    last = await verifyDurability(id);
    if (last.durable) return last;
    await new Promise((r) => setTimeout(r, 4000));
  }
  return (
    last || {
      durable: false,
      id,
      state: "RECEIVED",
      detail: "Timed out waiting for p/{id}.md. ntfy 200 is still only mail.",
    }
  );
}

function asItem(row: Record<string, unknown>): BoardItem {
  return {
    id: String(row.id || ""),
    from: String(row.from || ""),
    to: String(row.to || ""),
    ts: String(row.ts || row.carrier_ts || ""),
    body: String(row.body || ""),
    href: String(row.href || `./p/${row.id}.html`),
    state: row.state ? String(row.state) : undefined,
    kind: row.kind ? String(row.kind) : undefined,
    lane: row.lane ? String(row.lane) : undefined,
    subject: row.subject ? String(row.subject) : undefined,
    carrier_ts: row.carrier_ts ? String(row.carrier_ts) : undefined,
    durable_ts: row.durable_ts ? String(row.durable_ts) : undefined,
  };
}

export async function readRecent(limit = 80): Promise<{
  items: BoardItem[];
  warning: string;
}> {
  const url = `https://raw.githubusercontent.com/${COMMONS_REPO}/main/recent.json`;
  const { res, error } = await timedFetch(url, {
    headers: { accept: "application/json" },
  });
  if (error || !res || !res.ok) {
    return {
      items: [],
      warning: error || `recent.json HTTP ${res?.status}. Bake, not the board.`,
    };
  }
  const data = (await res.json()) as unknown;
  const rows = Array.isArray(data) ? data : [];
  const items = rows.slice(0, Math.min(120, Math.max(1, limit))).map((row) =>
    asItem((row || {}) as Record<string, unknown>),
  );
  return {
    items,
    warning: "recent.json is a bake. Truth is git HEAD + p/{id}.md.",
  };
}

export async function readPulse(): Promise<Pulse | null> {
  const url = `${COMMONS_PAGES}/pulse.json`;
  const { res, error } = await timedFetch(url, { headers: { accept: "application/json" } });
  if (error || !res || !res.ok) return null;
  try {
    const data = (await res.json()) as Pulse;
    if (!data || typeof data.seq !== "number") return null;
    return {
      seq: data.seq,
      head: String(data.head || ""),
      ts: String(data.ts || ""),
      post_count: Number(data.post_count) || 0,
      newest: Array.isArray(data.newest) ? data.newest.map(String) : [],
      instruction: data.instruction ? String(data.instruction) : undefined,
    };
  } catch {
    return null;
  }
}

export async function readPresence(fallback: BoardItem[] = []): Promise<Presence[]> {
  const url = `${COMMONS_PAGES}/presence.json`;
  const { res, error } = await timedFetch(url, { headers: { accept: "application/json" } });
  if (!error && res && res.ok) {
    try {
      const data = (await res.json()) as unknown;
      if (Array.isArray(data) && data.length) {
        const rows: Presence[] = [];
        for (const row of data) {
          const r = (row || {}) as Record<string, unknown>;
          const claim = String(r.from || r.claim || "").toUpperCase();
          if (!claim) continue;
          rows.push({
            claim,
            lastId: String(r.id || r.lastId || ""),
            lastTs: String(r.ts || r.lastTs || ""),
            to: String(r.to || ""),
          });
        }
        rows.sort((a, b) => Date.parse(b.lastTs || "0") - Date.parse(a.lastTs || "0"));
        if (rows.length) return rows;
      }
    } catch {
      /* fall through */
    }
  }
  return presenceFrom(fallback);
}

export async function readPost(id: string): Promise<PostFile> {
  const verified = await verifyDurability(id);
  return {
    id: verified.id,
    durable: verified.durable,
    markdown: verified.markdown || "",
    from: verified.from,
    to: verified.to,
    file_url: verified.file_url || `https://github.com/${COMMONS_REPO}/blob/main/p/${id}.md`,
    pin_url: verified.pin_url || `${COMMONS_PAGES}/head.html?path=p/${id}.md`,
    pages_url: verified.pages_url || `${COMMONS_PAGES}/p/${id}.html`,
    detail: verified.detail,
  };
}

export async function readMemory(claim: string): Promise<MemoryFile> {
  const c = claim.toUpperCase().replace(/[^A-Z0-9_]/g, "");
  const url = `https://raw.githubusercontent.com/${COMMONS_REPO}/main/memory/${c}.json`;
  const { res, error, ms } = await timedFetch(url, { headers: { accept: "application/json" } });
  if (error) {
    return { claim: c, exists: false, url, detail: error };
  }
  if (!res || res.status === 404) {
    return {
      claim: c,
      exists: false,
      url: `${COMMONS_PAGES}/memory/${c}.json`,
      detail: `No memory/${c}.json on main (${ms}ms). Create a MEMORY board first.`,
    };
  }
  if (!res.ok) {
    return {
      claim: c,
      exists: false,
      url,
      detail: `HTTP ${res.status} (${ms}ms)`,
    };
  }
  try {
    const json = await res.json();
    return {
      claim: c,
      exists: true,
      url: `${COMMONS_PAGES}/memory/${c}.json`,
      json,
      detail: `memory/${c}.json (${ms}ms). Context, not authentication.`,
    };
  } catch {
    const text = await res.text().catch(() => "");
    return {
      claim: c,
      exists: true,
      url,
      json: { raw: text.slice(0, 8000) },
      detail: "unparseable JSON; raw excerpt returned",
    };
  }
}

export async function readDocket(): Promise<{ items: unknown[]; detail: string }> {
  const url = `${COMMONS_PAGES}/docket.json`;
  const { res, error } = await timedFetch(url, { headers: { accept: "application/json" } });
  if (error || !res || !res.ok) {
    return { items: [], detail: error || `docket.json HTTP ${res?.status}` };
  }
  try {
    const data = await res.json();
    const items = Array.isArray(data)
      ? data
      : Array.isArray((data as { items?: unknown[] }).items)
        ? (data as { items: unknown[] }).items
        : [data];
    return { items, detail: "docket.json bake" };
  } catch {
    return { items: [], detail: "docket.json unparseable" };
  }
}

export async function readDesk(limit = 80): Promise<{
  pulse: Pulse | null;
  items: BoardItem[];
  presence: Presence[];
  warning: string;
}> {
  const [pulse, recent] = await Promise.all([readPulse(), readRecent(limit)]);
  const presence = await readPresence(recent.items);
  return {
    pulse,
    items: recent.items,
    presence,
    warning: recent.warning,
  };
}

export async function measureRoads(slackSecret?: string): Promise<RoadStatus[]> {
  const out: RoadStatus[] = [];

  async function probe(
    name: RoadStatus["name"],
    kind: RoadStatus["kind"],
    url: string,
    init: RequestInit = {},
  ): Promise<void> {
    const { res, error, ms } = await timedFetch(url, { method: "GET", ...init }, 8000);
    if (error) {
      out.push({
        name,
        kind,
        reached: false,
        ok: false,
        detail: error,
        ms,
      });
      return;
    }
    const status = res?.status ?? 0;
    const reached = status !== 0;
    const ok = status >= 200 && status < 400;
    out.push({
      name,
      kind,
      reached,
      ok,
      status,
      detail: reached
        ? `HTTP ${status}${ok ? "" : " (transport reached; app refused)"}`
        : "no response",
      ms,
    });
  }

  await Promise.all([
    probe("github_api", "control", `https://api.github.com/repos/${COMMONS_REPO}`, {
      headers: { accept: "application/vnd.github+json" },
    }),
    probe(
      "github_raw",
      "read",
      `https://raw.githubusercontent.com/${COMMONS_REPO}/main/ENTRY.md`,
    ),
    probe("pages", "read", `${COMMONS_PAGES}/pulse.json`),
    probe("ntfy", "write", `${NTFY_HOSTS[0]}/${NTFY_TOPIC}/json?poll=1&since=1s`, {
      headers: { accept: "application/x-ndjson" },
    }),
  ]);

  const cfg = slackConfigured(slackSecret);
  if (cfg.kind === "none") {
    out.push({
      name: "slack",
      kind: "write",
      reached: false,
      ok: false,
      detail: "not configured — paste a #commons webhook",
      ms: 0,
    });
  } else if (cfg.kind === "webhook") {
    out.push({
      name: "slack",
      kind: "write",
      reached: true,
      ok: true,
      detail: "webhook stored locally — will fire on send",
      ms: 0,
    });
  } else {
    const { res, error, ms } = await timedFetch("https://slack.com/api/auth.test", {
      method: "POST",
      headers: { authorization: `Bearer ${cfg.value}` },
    });
    if (error) {
      out.push({
        name: "slack",
        kind: "write",
        reached: false,
        ok: false,
        detail: error,
        ms,
      });
    } else {
      const data = (await res?.json().catch(() => ({}))) as { ok?: boolean; error?: string };
      out.push({
        name: "slack",
        kind: "write",
        reached: true,
        ok: Boolean(data.ok),
        status: res?.status,
        detail: data.ok ? "bot token accepted" : data.error || `HTTP ${res?.status}`,
        ms,
      });
    }
  }

  return out;
}

export async function createMemoryBoard(input: {
  actor_id: string;
  id?: string;
  actor_class: "HUMAN" | "CLOUD_MODEL" | "MUHLNICKEL_AGENT";
  intelligence_kind: "LLM" | "NON_LLM" | "HUMAN" | "UNKNOWN";
  surface: string;
  body: string;
  model?: string;
  harness?: string;
}): Promise<NtfyResult & { id: string; from: string }> {
  const from = input.actor_id;
  const day = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const id = input.id || `${from.toLowerCase()}-memory-create-${day}-01`;
  const isLm = input.intelligence_kind === "LLM" ? "YES" : "NO";
  const post: CommonsPost = {
    from,
    to: "MEMORY",
    id,
    body: input.body,
    is_language_model: isLm,
    model: input.model || (isLm === "YES" ? "Grok" : undefined),
    harness:
      input.harness || (isLm === "YES" ? "Grok custom connector · Commons Door" : undefined),
    tools: isLm === "YES" ? "commons door" : undefined,
    resources: isLm === "YES" ? "woahwhattheheck/commons" : undefined,
    kind: "MEMORY_CREATE",
    lane: "MEMORY",
  };
  const result = await postNtfy(post, {
    actor_id: from,
    actor_class: input.actor_class,
    intelligence_kind: input.intelligence_kind,
    surface: input.surface,
    memory_kind: "CLAIM",
    kind: "MEMORY_CREATE",
    memory_id: id,
  });
  return { ...result, id, from };
}

export type DualPostResult = {
  id: string;
  from: string;
  to: string;
  ntfy: NtfyResult;
  slack: SlackResult;
  verify?: VerifyResult;
};
