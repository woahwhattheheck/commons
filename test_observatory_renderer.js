/* Exercise the shipped renderer, including refresh failures and a long-lived tab. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const test = require("node:test");

class Node {
  constructor() { this.children = []; this._text = ""; this._html = ""; this.listeners = new Map(); }
  set textContent(value) { this._text = String(value); this._html = ""; this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(""); }
  set innerHTML(value) { this._html = value; this._text = ""; this.children = []; }
  get innerHTML() { return this._html; }
  appendChild(child) { this.children.push(child); }
  addEventListener(kind, fn) {
    if (!this.listeners.has(kind)) this.listeners.set(kind, []);
    this.listeners.get(kind).push(fn);
  }
  fire(kind) {
    for (const fn of this.listeners.get(kind) || []) fn({ target: this, preventDefault() {} });
  }
}

const START = Date.parse("2026-09-06T22:00:00Z");
const flush = () => new Promise(resolve => setImmediate(resolve));
const response = snap => ({ ok: true, json: async () => snap });
function snapshot(overrides = {}) {
  const now = new Date(START - 60000).toISOString();
  return {
    schema: "commons-observatory/v0.1", now, stale_after_seconds: 3600,
    head: { sha: "abc" }, cockpit: { lines: [], counts: {} }, sessions: [],
    economy: { collected_cash_usd: null }, coverage_note: "Observed inputs, not the whole fleet.",
    source_coverage: [{ source: "protocol/events.jsonl", state: "MISSING" }],
    board_motion: [{ id: "durable-post-001", from: "SHARED", to: "TABLE", ts: now }],
    timeline: [
      { kind: "START", session_id: "old-start", ts: now },
      { kind: "CHECKPOINT", session_id: "old-checkpoint", ts: now }
    ],
    ...overrides
  };
}

async function render(first = response(snapshot())) {
  const nodes = new Map();
  const document = new Node();
  document.hidden = false;
  document.getElementById = id => {
    if (!nodes.has(id)) nodes.set(id, new Node());
    return nodes.get(id);
  };
  document.createElement = () => new Node();
  const timers = new Map();
  let timerId = 0;
  let now = START;
  function schedule(fn, delay, repeat = false) {
    timers.set(++timerId, { fn, delay, repeat, at: now + delay });
    return timerId;
  }
  const calls = [];
  const queue = [first];
  const window = {};
  vm.runInNewContext(fs.readFileSync(__dirname + "/observatory.js", "utf8"), {
    document, window, Number, encodeURIComponent, AbortController,
    Date: class extends Date { static now() { return now; } },
    FormData: class { constructor(form) { this.values = form.values || {}; } get(key) { return this.values[key] || ""; } },
    setTimeout: (fn, delay) => schedule(fn, delay),
    clearTimeout: id => timers.delete(id),
    setInterval: (fn, delay) => schedule(fn, delay, true),
    fetch: async (url, options) => {
      calls.push({ url, options });
      const item = queue.shift();
      if (item === undefined) throw new Error("Unexpected fetch");
      if (item instanceof Error) throw item;
      return typeof item === "function" ? item(options) : item;
    }
  });
  await flush();
  return {
    nodes, document, window, calls, queue, timers,
    node: id => document.getElementById(id),
    async advance(ms) {
      now += ms;
      for (const [id, timer] of [...timers]) {
        if (timer.at > now) continue;
        if (timer.repeat) timer.at = now + timer.delay;
        else timers.delete(id);
        timer.fn();
      }
      await flush();
    },
    async refresh(result) {
      queue.push(result);
      document.getElementById("refresh-snapshot").fire("click");
      await flush();
    }
  };
}

test("stale bake has an immediate visible warning and source coverage", async () => {
  const page = await render(response(snapshot({ now: "2026-08-28T00:00:00Z" })));
  assert.match(page.node("snapshot-status").textContent, /STALE SNAPSHOT.*baked 2026-08-28/);
  assert.match(page.node("snapshot-status").className, /error/);
  assert.match(page.node("source-coverage").textContent, /protocol\/events.jsonl.*MISSING/);
  assert.match(page.node("economy").textContent, /collected_cash_usd=UNKNOWN/);
  assert.match(page.node("session-rows").innerHTML, /does not establish that the fleet is idle/);
  assert.match(page.node("board-motion").textContent, /durable-post-001/);
});

test("current, malformed, and future bake dates remain distinguishable", async () => {
  const current = await render();
  assert.match(current.node("snapshot-status").textContent, /CURRENT SNAPSHOT/);
  for (const now of ["not-a-timestamp", new Date(START + 60000).toISOString()]) {
    const malformed = await render(response(snapshot({ now })));
    assert.match(malformed.node("snapshot-status").textContent, /FRESHNESS UNKNOWN/);
  }
});

test("a long-lived tab ages the source timestamp without fetching or repainting data", async () => {
  const source = snapshot();
  const page = await render(response(source));
  const metric = page.node("metrics").children[0];
  assert.match(page.node("snapshot-status").textContent, /CURRENT SNAPSHOT/);
  await page.advance(3600000);
  assert.match(page.node("snapshot-status").textContent, /STALE SNAPSHOT.*age 61 minutes/);
  assert.match(page.node("snapshot-status").className, /error/);
  assert.equal(page.node("metrics").children[0], metric);
  assert.equal(page.calls.length, 1);
  assert.equal(page.window.COMMONS_OBSERVATORY, source);
  assert.equal(source.now, new Date(START - 60000).toISOString());
});

test("returning to a hidden tab immediately updates only its freshness label", async () => {
  const page = await render();
  page.document.hidden = true;
  await page.advance(3600000);
  page.document.hidden = false;
  page.document.fire("visibilitychange");
  assert.match(page.node("snapshot-status").textContent, /STALE SNAPSHOT/);
  assert.equal(page.calls.length, 1);
});

test("an initial HTTP failure can be retried without reloading the whole page", async () => {
  const page = await render({ ok: false, status: 503 });
  assert.match(page.node("snapshot-status").textContent, /HTTP 503/);
  assert.equal(page.window.COMMONS_OBSERVATORY, undefined);
  assert.equal(page.node("refresh-snapshot").disabled, false);
  await page.refresh(response(snapshot()));
  assert.equal(page.calls.length, 2);
  assert.match(page.node("snapshot-status").textContent, /CURRENT SNAPSHOT/);
  assert.doesNotMatch(page.node("refresh-status").className, /error/);
  assert.equal(page.node("timeline-filters").listeners.get("submit").length, 1);
});

test("a successful refresh replaces the source and preserves filters on the new timeline", async () => {
  const page = await render();
  const form = page.node("timeline-filters");
  form.values = { kind: "CHECKPOINT" };
  form.fire("submit");
  assert.match(page.node("timeline").textContent, /old-checkpoint/);
  assert.doesNotMatch(page.node("timeline").textContent, /old-start/);
  const next = snapshot({
    head: { sha: "def" }, economy: { collected_cash_usd: 0 },
    timeline: [
      { kind: "START", session_id: "new-start" },
      { kind: "CHECKPOINT", session_id: "new-checkpoint" }
    ]
  });
  await page.refresh(response(next));
  assert.equal(page.window.COMMONS_OBSERVATORY, next);
  assert.match(page.node("snapshot-status").textContent, /head def/);
  assert.match(page.node("timeline").textContent, /new-checkpoint/);
  assert.doesNotMatch(page.node("timeline").textContent, /old-checkpoint|new-start/);
  assert.match(page.node("economy").textContent, /collected_cash_usd=0/);
  form.fire("reset");
  await page.advance(0);
  assert.match(page.node("timeline").textContent, /new-start/);
  assert.equal(form.listeners.get("submit").length, 1);
  assert.equal(form.listeners.get("reset").length, 1);
  for (const call of page.calls) {
    assert.equal(call.url, "./observatory.json");
    assert.equal(call.options.cache, "no-store");
  }
});

test("a failed refresh retains the last good source and keeps its warning when age changes", async () => {
  const source = snapshot();
  const page = await render(response(source));
  await page.refresh(new Error("offline"));
  assert.equal(page.window.COMMONS_OBSERVATORY, source);
  assert.match(page.node("refresh-status").textContent, /offline.*last successfully loaded snapshot/);
  assert.match(page.node("refresh-status").className, /error/);
  assert.match(page.node("board-motion").textContent, /durable-post-001/);
  await page.advance(3600000);
  assert.match(page.node("snapshot-status").textContent, /STALE SNAPSHOT/);
  assert.match(page.node("refresh-status").textContent, /offline/);
  await page.refresh(response(snapshot({ head: { sha: "recovered" } })));
  assert.match(page.node("snapshot-status").textContent, /head recovered/);
  assert.doesNotMatch(page.node("refresh-status").className, /error/);
});

test("invalid JSON and schema never replace the last successful snapshot", async () => {
  const source = snapshot();
  const page = await render(response(source));
  for (const invalid of [
    { ok: true, json: async () => { throw new SyntaxError("Invalid JSON"); } },
    response({ schema: "wrong" }), response(null)
  ]) {
    await page.refresh(invalid);
    assert.equal(page.window.COMMONS_OBSERVATORY, source);
    assert.match(page.node("snapshot-status").textContent, /head abc/);
    assert.match(page.node("refresh-status").className, /error/);
    assert.equal(page.node("refresh-snapshot").disabled, false);
  }
});

test("a renderer error restores already-painted sections from the last good snapshot", async () => {
  const source = snapshot();
  const page = await render(response(source));
  await page.refresh(response(snapshot({ head: { sha: "bad" }, routes: [null] })));
  assert.equal(page.window.COMMONS_OBSERVATORY, source);
  assert.match(page.node("snapshot-status").textContent, /head abc/);
  assert.match(page.node("refresh-status").className, /error/);
});

test("refresh allows only one request in flight and re-enables the button when done", async () => {
  const page = await render();
  let resolve;
  const pending = new Promise(done => { resolve = done; });
  await page.refresh(pending);
  const button = page.node("refresh-snapshot");
  assert.equal(button.disabled, true);
  button.fire("click");
  button.fire("click");
  assert.equal(page.calls.length, 2);
  resolve(response(snapshot({ head: { sha: "done" } })));
  await flush();
  assert.equal(button.disabled, false);
  assert.equal(button.textContent, "Refresh snapshot");
  assert.match(page.node("snapshot-status").textContent, /head done/);
  assert.equal([...page.timers.values()].filter(timer => !timer.repeat).length, 0);
});

test("a hung request is aborted after 15 seconds and a new explicit retry works", async () => {
  const page = await render(options => new Promise((resolve, reject) => {
    options.signal.addEventListener("abort", () => reject(new Error("aborted")));
  }));
  assert.equal(page.node("refresh-snapshot").disabled, true);
  await page.advance(15000);
  assert.equal(page.calls[0].options.signal.aborted, true);
  assert.match(page.node("snapshot-status").textContent, /timed out/);
  assert.equal(page.node("refresh-snapshot").disabled, false);
  await page.refresh(response(snapshot()));
  assert.match(page.node("snapshot-status").textContent, /CURRENT SNAPSHOT/);
  assert.equal(page.calls.length, 2);
});
