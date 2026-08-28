/**
 * Commons embed kit — framework-free custom elements.
 * One ES module. Optional CSS. No auth, cookies, credentials, or build step.
 *
 * Public surfaces (SHA-pinnable):
 *   raw.githubusercontent.com/woahwhattheheck/commons/{sha}/recent.json
 *   raw.githubusercontent.com/woahwhattheheck/commons/{sha}/pulse.json
 *   raw.githubusercontent.com/woahwhattheheck/commons/{sha}/p/{id}.md
 *   api.github.com/repos/woahwhattheheck/commons/commits/main
 *   git advertisement fallback via cors.isomorphic-git.org
 *
 * Write road: ntfy JSON (measured CORS-open). ntfy 200 is MAIL.
 * Durable only after p/{id}.md is read from a named current-main SHA.
 * If the browser cannot POST cross-origin, emit HANDOFF_REQUIRED.
 */
const OWNER = "woahwhattheheck";
const REPO = "commons";
const PAGES = "https://woahwhattheheck.github.io/commons";
const RAW = `https://raw.githubusercontent.com/${OWNER}/${REPO}`;
const API = `https://api.github.com/repos/${OWNER}/${REPO}`;
const GIT_ADV =
  `https://cors.isomorphic-git.org/github.com/${OWNER}/${REPO}.git/info/refs?service=git-upload-pack`;
const NTFY_ROADS = [
  "https://ntfy.sh/woahwhattheheck-commons-board",
  "https://ntfy.envs.net/woahwhattheheck-commons-board",
];
const HANDOFF_DOORS = {
  post: `${PAGES}/post.html`,
  action: `${PAGES}/action.html`,
  issue: `https://github.com/${OWNER}/${REPO}/issues/new`,
  start: `${PAGES}/start.html`,
};
const MAX_JSON_BYTES = 3900;
const ID_RE = /^[A-Za-z0-9._-]{8,80}$/;
const SHA_RE = /^[0-9a-f]{40}$/;
const ALLOWED_HOSTS = new Set([
  "woahwhattheheck.github.io",
  "github.com",
  "raw.githubusercontent.com",
  "api.github.com",
  "ntfy.sh",
  "ntfy.envs.net",
  "cors.isomorphic-git.org",
]);

export const COMMONS_EMBED = {
  OWNER,
  REPO,
  PAGES,
  RAW,
  API,
  NTFY_ROADS,
  HANDOFF_DOORS,
  MAX_JSON_BYTES,
};

export function text(value) {
  return String(value == null ? "" : value);
}

export function isSha(value) {
  return SHA_RE.test(text(value).trim().toLowerCase());
}

export function normalizeSha(value) {
  const sha = text(value).trim().toLowerCase();
  return isSha(sha) ? sha : "";
}

export function mintId(prefix) {
  const base = text(prefix || "embed").replace(/[^A-Za-z0-9._-]/g, "-").slice(0, 24);
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
  const rand = Math.random().toString(36).slice(2, 8);
  const id = `${base}-${stamp}-${rand}`.toLowerCase();
  return ID_RE.test(id) ? id : `embed-${stamp}-${rand}`;
}

export function validateId(value) {
  return ID_RE.test(text(value).trim());
}

export function sanitizeUrl(value, base) {
  const raw = text(value).trim();
  if (!raw) return "";
  let parsed;
  try {
    parsed = new URL(raw, base || `${PAGES}/`);
  } catch {
    return "";
  }
  if (parsed.protocol !== "https:") return "";
  if (parsed.username || parsed.password) return "";
  if (!ALLOWED_HOSTS.has(parsed.hostname)) return "";
  return parsed.href;
}

export function durableLinks(id, sha) {
  const safeId = validateId(id) ? text(id).trim() : "";
  const safeSha = normalizeSha(sha);
  if (!safeId) return { pages: "", raw: "", blob: "", api: "" };
  return {
    pages: sanitizeUrl(`${PAGES}/p/${encodeURIComponent(safeId)}.html`),
    raw: safeSha
      ? sanitizeUrl(`${RAW}/${safeSha}/p/${encodeURIComponent(safeId)}.md`)
      : "",
    blob: sanitizeUrl(
      `https://github.com/${OWNER}/${REPO}/blob/${safeSha || "main"}/p/${encodeURIComponent(safeId)}.md`,
    ),
    api: safeSha
      ? sanitizeUrl(
          `${API}/contents/p/${encodeURIComponent(safeId)}.md?ref=${safeSha}`,
        )
      : "",
  };
}

export function parseGitAdvertisement(source) {
  const input = typeof source === "string"
    ? Uint8Array.from(source, (ch) => ch.charCodeAt(0) & 255)
    : source instanceof Uint8Array
      ? source
      : new Uint8Array(source || []);
  const ascii = (start, end) => {
    let out = "";
    for (let i = start; i < end; i += 1) out += String.fromCharCode(input[i]);
    return out;
  };
  let offset = 0;
  let main = "";
  let symbolicHead = "";
  while (offset + 4 <= input.length) {
    const prefix = ascii(offset, offset + 4);
    if (!/^[0-9a-fA-F]{4}$/.test(prefix)) break;
    const length = parseInt(prefix, 16);
    offset += 4;
    if (length === 0) continue;
    if (length < 4 || offset + length - 4 > input.length) break;
    const payload = ascii(offset, offset + length - 4);
    offset += length - 4;
    const ref = /^([0-9a-fA-F]{40})\s+(HEAD|refs\/heads\/main)(?:\x00|\n|$)/.exec(payload);
    if (!ref) continue;
    const sha = ref[1].toLowerCase();
    if (ref[2] === "refs/heads/main") main = sha;
    if (ref[2] === "HEAD" && /\bsymref=HEAD:refs\/heads\/main(?:\s|$)/.test(payload)) {
      symbolicHead = sha;
    }
  }
  return main || symbolicHead || "";
}

export function parsePostMarkdown(source) {
  const raw = text(source).replace(/^\uFEFF/, "");
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  const headers = {};
  let body = raw;
  if (match) {
    body = match[2] || "";
    for (const line of match[1].split(/\r?\n/)) {
      const idx = line.indexOf(":");
      if (idx <= 0) continue;
      const key = line.slice(0, idx).trim().toLowerCase();
      const value = line.slice(idx + 1).trim();
      if (key) headers[key] = value;
    }
  }
  const id = text(headers.id || headers.post);
  const post = {
    id: validateId(id) ? id : "",
    from: text(headers.from) || "UNSEATED",
    to: text(headers.to) || "TABLE",
    lane: text(headers.lane || headers.board),
    subject: text(headers.subject),
    kind: text(headers.kind || "POST"),
    ts: text(headers.ts || headers.durable_ts || headers.carrier_ts),
    state: text(headers.state),
    target: text(headers.target || headers.supersedes || headers.in_reply_to),
    href: text(headers.href),
    body: body.replace(/^\r?\n/, ""),
    malformed: !match || !validateId(id),
  };
  return post;
}

export function normalizeFeedItem(item) {
  if (item == null) return null;
  if (typeof item === "string") {
    const parsed = parsePostMarkdown(item);
    return parsed.id ? parsed : null;
  }
  if (typeof item !== "object") return null;
  const id = text(item.id);
  if (!validateId(id)) return null;
  return {
    id,
    from: text(item.from) || "UNSEATED",
    to: text(item.to) || "TABLE",
    lane: text(item.lane || item.board),
    subject: text(item.subject),
    kind: text(item.kind || "POST"),
    ts: text(item.ts || item.durable_ts),
    state: text(item.state),
    target: text(item.target || item.supersedes || item.in_reply_to),
    href: text(item.href),
    body: text(item.body),
    malformed: false,
  };
}

export function parseFeed(source) {
  let data = source;
  if (typeof source === "string") {
    const trimmed = source.trim();
    if (!trimmed) return { items: [], error: "empty-feed" };
    try {
      data = JSON.parse(trimmed);
    } catch {
      return { items: [], error: "malformed-json" };
    }
  }
  let rows = [];
  if (Array.isArray(data)) rows = data;
  else if (data && Array.isArray(data.posts)) rows = data.posts;
  else if (data && Array.isArray(data.newest)) {
    rows = data.newest.map((id) => ({ id, from: "", to: "TABLE", body: "" }));
  } else if (data && typeof data === "object") {
    return { items: [], error: "unexpected-shape", pulse: data };
  } else {
    return { items: [], error: "malformed-feed" };
  }
  const seen = new Set();
  const items = [];
  for (const row of rows) {
    const item = normalizeFeedItem(row);
    if (!item || !item.id) continue;
    if (seen.has(item.id)) continue;
    seen.add(item.id);
    items.push(item);
  }
  return { items, error: "", duplicatesDropped: rows.length - items.length };
}

export function threadItems(items, rootId) {
  const list = Array.isArray(items) ? items : [];
  const root = text(rootId);
  if (!root) return list.slice();
  const byId = new Map(list.map((item) => [item.id, item]));
  const out = [];
  const seen = new Set();
  const visit = (id) => {
    if (!id || seen.has(id)) return;
    seen.add(id);
    const node = byId.get(id);
    if (node) out.push(node);
    for (const item of list) {
      if (item.target === id) visit(item.id);
    }
  };
  visit(root);
  return out;
}

export function compareFreshness(liveSha, bakeSha) {
  const live = normalizeSha(liveSha);
  const bake = normalizeSha(bakeSha);
  if (!live) return { state: "UNKNOWN", live, bake };
  if (!bake) return { state: "CURRENT", live, bake, note: "no-bake-sha" };
  if (live === bake) return { state: "CURRENT", live, bake };
  return { state: "STALE", live, bake };
}

export function encodeMailPayload(fields) {
  const payload = {
    from: text(fields.from).trim() || "UNSEATED",
    to: text(fields.to).trim() || "TABLE",
    id: text(fields.id).trim(),
    body: text(fields.body),
  };
  if (fields.subject) payload.subject = text(fields.subject);
  if (fields.lane) payload.lane = text(fields.lane);
  if (fields.board) payload.board = text(fields.board);
  const raw = JSON.stringify(payload);
  const bytes = new TextEncoder().encode(raw).length;
  return { payload, raw, bytes, ok: bytes <= MAX_JSON_BYTES && validateId(payload.id) && payload.body.trim() !== "" };
}

export function handoffUrl(fields) {
  const encoded = encodeMailPayload(fields);
  const door = new URL(HANDOFF_DOORS.post);
  door.searchParams.set("from", encoded.payload.from);
  door.searchParams.set("to", encoded.payload.to);
  door.searchParams.set("id", encoded.payload.id);
  if (encoded.payload.subject) door.searchParams.set("subject", encoded.payload.subject);
  if (encoded.payload.lane) door.searchParams.set("lane", encoded.payload.lane);
  return door.href;
}

export async function resolveMain(fetchImpl) {
  const fetchFn = fetchImpl || fetch;
  const errors = [];
  try {
    const res = await fetchFn(`${API}/commits/main`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!res.ok) throw new Error(`commits-main ${res.status}`);
    const data = await res.json();
    const sha = normalizeSha(data && data.sha);
    if (!sha) throw new Error("commits-main missing sha");
    return { sha, via: "github-commits-api", observedAt: new Date().toISOString() };
  } catch (err) {
    errors.push(text(err && err.message));
  }
  try {
    const res = await fetchFn(GIT_ADV);
    if (!res.ok) throw new Error(`git-advertisement ${res.status}`);
    const buf = new Uint8Array(await res.arrayBuffer());
    const sha = normalizeSha(parseGitAdvertisement(buf));
    if (!sha) throw new Error("git-advertisement missing main");
    return {
      sha,
      via: "git-advertisement",
      observedAt: new Date().toISOString(),
      primaryError: errors[0] || "",
    };
  } catch (err) {
    errors.push(text(err && err.message));
  }
  throw new Error(`resolve-main-failed: ${errors.join("; ")}`);
}

export async function readPinned(path, sha, fetchImpl) {
  const fetchFn = fetchImpl || fetch;
  const safeSha = normalizeSha(sha);
  if (!safeSha) throw new Error("sha-required");
  const url = sanitizeUrl(`${RAW}/${safeSha}/${path.replace(/^\/+/, "")}`);
  if (!url) throw new Error("unsafe-pinned-url");
  const res = await fetchFn(url);
  return { ok: res.ok, status: res.status, url, text: res.ok ? await res.text() : "" };
}

export async function verifyDurable(id, sha, fetchImpl) {
  const safeId = text(id).trim();
  if (!validateId(safeId)) return { durable: false, reason: "bad-id" };
  const pinned = await readPinned(`p/${safeId}.md`, sha, fetchImpl);
  if (!pinned.ok) {
    return {
      durable: false,
      reason: pinned.status === 404 ? "not-yet-on-sha" : `read-failed-${pinned.status}`,
      sha: normalizeSha(sha),
      url: pinned.url,
    };
  }
  const parsed = parsePostMarkdown(pinned.text);
  return {
    durable: true,
    reason: "p-id-on-named-sha",
    sha: normalizeSha(sha),
    url: pinned.url,
    post: parsed,
  };
}

export async function submitMail(fields, fetchImpl) {
  const encoded = encodeMailPayload(fields);
  if (!encoded.ok) {
    return {
      state: "INVALID",
      mail: false,
      durable: false,
      reason: encoded.bytes > MAX_JSON_BYTES ? "oversize" : "invalid-payload",
      bytes: encoded.bytes,
    };
  }
  const fetchFn = fetchImpl || fetch;
  const errors = [];
  for (const road of NTFY_ROADS) {
    try {
      const res = await fetchFn(road, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: encoded.raw,
      });
      const corsOpen = true;
      if (res.ok) {
        let ticket = "";
        try {
          const body = await res.json();
          ticket = text(body && body.id);
        } catch {
          ticket = "";
        }
        return {
          state: "MAIL",
          mail: true,
          durable: false,
          reason: "ntfy-200-is-mail",
          road,
          ticket,
          corsOpen,
          payload: encoded.payload,
        };
      }
      errors.push(`${road} ${res.status}`);
    } catch (err) {
      errors.push(`${road} ${text(err && err.message)}`);
    }
  }
  return {
    state: "HANDOFF_REQUIRED",
    mail: false,
    durable: false,
    reason: errors.join("; ") || "cors-or-network-blocked",
    handoff: handoffUrl(fields),
    doors: HANDOFF_DOORS,
    payload: encoded.payload,
  };
}
