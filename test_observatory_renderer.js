/* Exercise the shipped renderer against stale, missing, and current bakes. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const test = require("node:test");

class Node {
  constructor() { this.children = []; this._text = ""; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(""); }
  appendChild(child) { this.children.push(child); }
  addEventListener() {}
}

async function render(now) {
  const nodes = new Map();
  const document = {
    getElementById(id) { if (!nodes.has(id)) nodes.set(id, new Node()); return nodes.get(id); },
    createElement() { return new Node(); }
  };
  const snap = {
    schema: "commons-observatory/v0.1", now, stale_after_seconds: 3600,
    head: { sha: "abc" }, cockpit: { lines: [], counts: {} }, sessions: [],
    economy: { collected_cash_usd: null }, coverage_note: "Observed inputs, not the whole fleet.",
    source_coverage: [{ source: "protocol/events.jsonl", state: "MISSING" }],
    board_motion: [{ id: "durable-post-001", from: "SHARED", to: "TABLE", ts: now }]
  };
  vm.runInNewContext(fs.readFileSync(__dirname + "/observatory.js", "utf8"), {
    document, window: {}, Date, Number, encodeURIComponent, setTimeout,
    fetch: async () => ({ ok: true, json: async () => snap })
  });
  await new Promise(resolve => setImmediate(resolve));
  return nodes;
}

test("stale bake has an immediate visible warning and source coverage", async () => {
  const nodes = await render("2026-08-28T00:00:00Z");
  assert.match(nodes.get("snapshot-status").textContent, /STALE SNAPSHOT.*baked 2026-08-28/);
  assert.match(nodes.get("snapshot-status").className, /error/);
  assert.match(nodes.get("source-coverage").textContent, /protocol\/events.jsonl.*MISSING/);
  assert.match(nodes.get("economy").textContent, /collected_cash_usd=UNKNOWN/);
  assert.match(nodes.get("session-rows").innerHTML, /does not establish that the fleet is idle/);
  assert.match(nodes.get("board-motion").textContent, /durable-post-001/);
});

test("current and malformed bake dates remain distinguishable", async () => {
  const current = await render(new Date(Date.now() - 60000).toISOString());
  assert.match(current.get("snapshot-status").textContent, /CURRENT SNAPSHOT/);
  const malformed = await render("not-a-timestamp");
  assert.match(malformed.get("snapshot-status").textContent, /FRESHNESS UNKNOWN/);
});
