#!/usr/bin/env node
"use strict";
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const engine = require("./fleet-work-order.js");

const fixture = {
  event_id: "inspection-1042",
  vehicle_id: "truck-17",
  fault_code: "BRAKE-PAD-LOW",
  severity: "HIGH",
  reported_at: "2026-08-31T00:00:00Z",
  note: "rear axle sensor"
};

function counts(ledger) {
  return [Object.keys(ledger.work_orders).length, Object.keys(ledger.escalations).length];
}

function crash(store, at) {
  assert.throws(() => engine.process(store, fixture, { fail_at: at }), new RegExp("SIMULATED_CRASH:" + at));
}

{
  const store = engine.memoryStore();
  const first = engine.process(store, fixture);
  assert.equal(first.kind, "COMMITTED");
  assert.deepEqual(counts(store.load()), [1, 1]);
  const replay = engine.process(store, fixture);
  assert.equal(replay.kind, "REPLAY_NOOP");
  assert.deepEqual(replay.receipt, first.receipt);
  assert.deepEqual(counts(store.load()), [1, 1]);
}

for (const failAt of ["after_prepare", "after_effects"]) {
  const store = engine.memoryStore();
  crash(store, failAt);
  const resumed = engine.process(store, fixture);
  assert.equal(resumed.kind, "COMMITTED");
  assert.deepEqual(counts(store.load()), [1, 1]);
  assert.equal(store.load().receipts[fixture.event_id].effects, 2);
}

{
  const store = engine.memoryStore();
  crash(store, "after_effects");
  const rolled = engine.rollback(store, fixture.event_id);
  assert.equal(rolled.kind, "ROLLED_BACK");
  assert.deepEqual(counts(store.load()), [0, 0]);
  assert.equal(store.load().receipts[fixture.event_id].effects_remaining, 0);
}

{
  const store = engine.memoryStore();
  engine.process(store, fixture);
  const conflicting = Object.assign({}, fixture, { fault_code: "ENGINE-HOT" });
  const result = engine.process(store, conflicting);
  assert.equal(result.kind, "CONFLICT");
  assert.deepEqual(counts(store.load()), [1, 1]);
  assert.equal(engine.rollback(store, fixture.event_id).kind, "ROLLBACK_REFUSED");
}

{
  const store = engine.memoryStore();
  const invalid = engine.process(store, { event_id: "bad" });
  assert.equal(invalid.kind, "REJECTED");
  assert.deepEqual(counts(store.load()), [0, 0]);
}

{
  const page = fs.readFileSync(path.join(__dirname, "fleet-work-order.html"), "utf8");
  for (const marker of ["$199 diagnostic", "$2,500 proof", "Exactly Once", "Crash after prepare", "Rollback incomplete", "no login", "synthetic inputs only"]) assert(page.includes(marker), marker);
  assert(!/\b(login required|sign up required|permission required)\b/i.test(page));
}

console.log("fleet-work-order: 7 scenarios PASS");
