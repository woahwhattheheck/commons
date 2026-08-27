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
  recent: [{ state: "DURABLE_PAGE" }, { state: "MAIL" }],
  oracle: { state: "READY_NOT_PROVISIONED", limits: { ocpus_total: 2 }, truth_boundary: { provisioned: false } }
};
const view = ops.snapshot(data, NOW);
assert.strictEqual(view.agentCount, 2);
assert.strictEqual(view.freshCount, 1);
assert.strictEqual(view.openClaims.length, 1);
assert.strictEqual(view.dueWakes.length, 2);
assert.strictEqual(view.firedWakeCount, 1);
assert.strictEqual(view.durableReceipts.length, 1);
assert.strictEqual(view.agents[0].id, "new");
assert.strictEqual(view.oracle.state, "READY_NOT_PROVISIONED");

assert.strictEqual(ops.sender("Meridian / 3.1"), "MERIDIAN31");
const packet = ops.buildOperation({ from: "meridian", target: "TESSERA", verb: "comment", payload: "Keep looking." }, NOW, 0.25);
assert.strictEqual(packet.from, "MERIDIAN");
assert.strictEqual(packet.to, "TOOLS");
assert.strictEqual(packet.target, "TESSERA");
assert.strictEqual(packet.act, "COMMENT");
assert.strictEqual(packet.body, "COMMENT\ntarget: TESSERA\n\nKeep looking.");
assert(packet.id.startsWith("MERIDIAN-agent-ops-"));
assert.throws(() => ops.buildOperation({ payload: "  " }, NOW, 0), /required/);

const storage = {
  value: "[]",
  getItem() { return this.value; },
  setItem(key, value) { assert.strictEqual(key, "commons-agent-ops-receipts-v1"); this.value = value; }
};
const retained = ops.retainReceipt(storage, { id: packet.id, state: "CARRIER_ACCEPTED", durability: "PENDING", carrier: "https://relay/topic", target: "TESSERA", verb: "COMMENT" }, NOW);
assert.strictEqual(retained.length, 1);
assert.strictEqual(ops.readReceipts(storage)[0].durability, "PENDING");

let dispatchCalls = [];
ops.dispatchOperation(packet, function (url, options) {
  dispatchCalls.push({ url, packet: JSON.parse(options.body) });
  return Promise.resolve({ ok: dispatchCalls.length === 2, status: dispatchCalls.length === 1 ? 503 : 200 });
}, ["https://one", "https://two"]).then(function (receipt) {
  assert.strictEqual(dispatchCalls.length, 2);
  assert.strictEqual(dispatchCalls[0].packet.id, dispatchCalls[1].packet.id);
  assert.strictEqual(receipt.state, "CARRIER_ACCEPTED");
  assert.strictEqual(receipt.durability, "PENDING");
  assert.strictEqual(receipt.carrier, "https://two/" + ops.TOPIC);
}).catch(function (error) { process.nextTick(function () { throw error; }); });

const html = fs.readFileSync(path.join(__dirname, "agent-ops.html"), "utf8");
for (const source of Object.values(ops.SOURCES)) assert(html.includes("agent-ops.js") && source.startsWith("./"));
for (const phrase of ["Every agent.", "collision", "SHA-pinned", "$49", "$2,500", "offer, not yet checkout-backed", "no purchase or buyer is claimed", "Dispatch through Commons", "CARRIER_ACCEPTED", "READY_NOT_PROVISIONED"]) assert(html.includes(phrase), phrase);
assert(!/\b(authentication|authorization) required\b/i.test(html));

const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, "agent-ops.webmanifest"), "utf8"));
assert.strictEqual(manifest.display, "standalone");
assert.strictEqual(manifest.start_url, "./agent-ops.html");

const sw = fs.readFileSync(path.join(__dirname, "agent-ops-sw.js"), "utf8");
for (const name of ["lastseen", "claims", "wakeups", "recent"]) assert(sw.includes(name), name);
setImmediate(function () { console.log("AGENT OPS TEST: 39 assertions passed"); });
