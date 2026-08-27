"use strict";
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const ops = require("./agent-ops.js");

const NOW = Date.parse("2026-08-27T20:00:00Z");
assert.strictEqual(ops.freshness("2026-08-27T19:00:00Z", NOW), "FRESH");
assert.strictEqual(ops.freshness("2026-08-26T19:59:59Z", NOW), "STALE");
assert.strictEqual(ops.freshness("", NOW), "UNKNOWN");

const data = {
  lastseen: [
    { from: "CODEX", ts: "2026-08-27T18:00:00Z", to: "TABLE", id: "new" },
    { from: "CODEX", ts: "2026-08-26T18:00:00Z", to: "OLD", id: "old" },
    { from: "GROK", ts: "", to: "TABLE", id: "undated" }
  ],
  claims: { claims: [{ status: "OPEN" }, { status: "CLOSED" }] },
  wakeups: { due: [{ id: "due" }], pending: [{ id: "pending" }], fired: ["done"], ts: "2026-08-27T19:30:00Z" },
  recent: [{ state: "DURABLE_PAGE" }, { state: "MAIL" }]
};
const view = ops.snapshot(data, NOW);
assert.strictEqual(view.agentCount, 2);
assert.strictEqual(view.freshCount, 1);
assert.strictEqual(view.openClaims.length, 1);
assert.strictEqual(view.dueWakes.length, 2);
assert.strictEqual(view.firedWakeCount, 1);
assert.strictEqual(view.durableReceipts.length, 1);
assert.strictEqual(view.agents[0].id, "new");

const html = fs.readFileSync(path.join(__dirname, "agent-ops.html"), "utf8");
for (const source of Object.values(ops.SOURCES)) assert(html.includes("agent-ops.js") && source.startsWith("./"));
for (const phrase of ["Every agent.", "collision", "SHA-pinned", "$49", "$2,500", "offer, not yet checkout-backed", "no purchase or buyer is claimed"]) assert(html.includes(phrase), phrase);
assert(!/\b(authentication|authorization) required\b/i.test(html));

const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, "agent-ops.webmanifest"), "utf8"));
assert.strictEqual(manifest.display, "standalone");
assert.strictEqual(manifest.start_url, "./agent-ops.html");

const sw = fs.readFileSync(path.join(__dirname, "agent-ops-sw.js"), "utf8");
for (const name of ["lastseen", "claims", "wakeups", "recent"]) assert(sw.includes(name), name);
console.log("AGENT OPS TEST: 22 assertions passed");
