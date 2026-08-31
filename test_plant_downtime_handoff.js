"use strict";
const assert = require("assert");
const handoff = require("./plant-downtime-handoff.js");

function base(overrides) {
  const extra = overrides || {};
  const fieldsIn = extra.fields || {};
  const fields = Object.assign({
    plantId: "PLANT-RIVERBEND-DEMO",
    assetId: "ASSET-KILN-04-DEMO",
    faultCode: "OVERTEMP",
    severity: "HIGH",
    observedAt: "2026-08-31T01:40:00Z",
    windowId: "WIN-SYN-A1",
    partsNeeded: "YES"
  }, fieldsIn);
  const packet = Object.assign({
    faultId: "FAULT-SYN-7701",
    faultClass: "overtemp",
    source: "FAULT_REPORT",
    eventId: "RPT-SYN-2001",
    submittedAt: "2026-08-31T02:00:00Z"
  }, extra);
  packet.fields = fields;
  return packet;
}

function run(input, store, options) {
  return handoff.processFault(input, store, Object.assign({ now: "2026-08-31T02:00:00Z" }, options || {}));
}

{
  const store = handoff.createStore();
  const r = run(base(), store);
  assert.strictEqual(r.status, "DISPATCHED");
  assert.strictEqual(r.idempotencyKey, "FAULT-SYN-7701");
  assert.strictEqual(r.technicianHandoff.id, "FAULT-SYN-7701:tech");
  assert.strictEqual(r.technicianHandoff.lane, "TECH_KILN_THERMAL");
  assert.strictEqual(r.partsRequest.id, "FAULT-SYN-7701:parts");
  assert.strictEqual(r.partsRequest.kit, "PARTS_THERMAL_KIT");
  assert.strictEqual(r.statusReceipt.kind, "HANDOFF_STATUS_RECEIPT");
  assert.deepStrictEqual(r.effectCounts, {
    classifications: 1,
    technicianHandoffs: 1,
    partsRequests: 1,
    statusReceipts: 1,
    progressReceipts: 1,
    dispatches: 1
  });
  assert.strictEqual(r.livePlantControl, 0);
  assert.strictEqual(r.cmmsWrites, 0);
  assert.strictEqual(r.purchasingOrders, 0);
  assert.strictEqual(r.safetyDecisions, 0);
  assert.strictEqual(r.piiEmitted, 0);
  assert.strictEqual(r.cashUsd, 0);
  assert.strictEqual(r.outreach, 0);
}

{
  const store = handoff.createStore();
  const input = base();
  input.fields.severity = "UNKNOWN";
  const r = run(input, store);
  assert.strictEqual(r.status, "HELD_INCOMPLETE");
  assert.strictEqual(r.technicianHandoff, null);
  assert.strictEqual(r.effectCounts.dispatches, 0);
  assert.deepStrictEqual(r.statusReceipt.operationalHold, ["severity"]);
}

{
  const expected = {
    overtemp: ["TECH_KILN_THERMAL", "PARTS_THERMAL_KIT"],
    vibration: ["TECH_ROTATING", "PARTS_BEARING_KIT"],
    "pressure-drop": ["TECH_PROCESS", "PARTS_SEAL_KIT"],
    estop: ["TECH_SAFETY", "PARTS_NONE"]
  };
  Object.keys(expected).forEach(function (cls, i) {
    const fields = {
      plantId: "PLANT-RIVERBEND-DEMO",
      assetId: "ASSET-KILN-04-DEMO",
      faultCode: handoff.ENUMS.faultCode[i],
      severity: "HIGH",
      observedAt: "2026-08-31T01:40:00Z",
      windowId: "WIN-SYN-A1",
      partsNeeded: cls === "estop" ? "NO" : "YES"
    };
    const r = run(base({
      faultId: "FAULT-SYN-M" + i,
      faultClass: cls,
      eventId: "RPT-SYN-M" + i,
      fields: fields
    }), handoff.createStore());
    assert.strictEqual(r.status, "DISPATCHED", cls);
    assert.strictEqual(r.technicianHandoff.lane, expected[cls][0], cls);
    assert.strictEqual(r.partsRequest.kit, expected[cls][1], cls);
    assert.strictEqual(r.effectCounts.dispatches, 1, cls);
  });
}

{
  const store = handoff.createStore();
  const sensor = base({ source: "SENSOR_PING", eventId: "SENSOR-SYN-1001" });
  const first = run(sensor, store);
  const dupSensor = run(sensor, store, { now: "2026-08-31T02:01:00Z" });
  const report = run(base({ source: "FAULT_REPORT", eventId: "RPT-SYN-2001" }), store, { now: "2026-08-31T02:02:00Z" });
  assert.strictEqual(first.status, "DISPATCHED");
  assert.strictEqual(dupSensor.status, "REPLAY_NOOP");
  assert.strictEqual(report.status, "REPLAY_NOOP");
  assert.strictEqual(dupSensor.technicianHandoff.id, first.technicianHandoff.id);
  assert.strictEqual(report.technicianHandoff.id, first.technicianHandoff.id);
  assert.strictEqual(report.effectCounts.dispatches, 1);
  assert.strictEqual(Object.keys(store.faults).length, 1);
  assert.strictEqual(report.events.length, 2);
}

{
  const store = handoff.createStore();
  const crashed = run(base(), store, { crashAt: "after_classify" });
  assert.strictEqual(crashed.status, "CRASHED_AFTER_CLASSIFY");
  assert.deepStrictEqual(crashed.effectCounts.dispatches, 0);
  assert.ok(crashed.progressReceipt.createdAt);
  const resumed = run(base(), store, { now: "2026-08-31T02:03:00Z" });
  assert.strictEqual(resumed.status, "DISPATCHED");
  assert.strictEqual(resumed.effectCounts.dispatches, 1);
  assert.strictEqual(resumed.technicianHandoff.id, "FAULT-SYN-7701:tech");
}

{
  const worker1 = handoff.createWorker();
  assert.strictEqual(worker1.generation, 1);
  const crashed = worker1.processFault(base({ source: "SENSOR_PING", eventId: "SENSOR-SYN-1001" }), {
    crashAt: "after_tech",
    now: "2026-08-31T02:04:00Z"
  });
  assert.strictEqual(crashed.status, "CRASHED_AFTER_TECH");
  assert.strictEqual(crashed.effectCounts.technicianHandoffs, 1);
  assert.strictEqual(crashed.effectCounts.partsRequests, 0);
  assert.strictEqual(crashed.effectCounts.dispatches, 1);
  const worker2 = handoff.createWorker(worker1.snapshot());
  assert.strictEqual(worker2.generation, 2);
  assert.notStrictEqual(worker2.store, worker1.store);
  const dupSensor = worker2.processFault(base({ source: "SENSOR_PING", eventId: "SENSOR-SYN-1001" }), {
    now: "2026-08-31T02:05:00Z"
  });
  assert.strictEqual(dupSensor.status, "DISPATCHED");
  assert.strictEqual(dupSensor.technicianHandoff.id, crashed.technicianHandoff.id);
  const report = worker2.processFault(base({ source: "FAULT_REPORT", eventId: "RPT-SYN-2001" }), {
    now: "2026-08-31T02:06:00Z"
  });
  assert.strictEqual(report.status, "REPLAY_NOOP");
  assert.strictEqual(report.effectCounts.dispatches, 1);
  assert.strictEqual(report.effectCounts.technicianHandoffs, 1);
  assert.strictEqual(report.effectCounts.partsRequests, 1);
  assert.strictEqual(Object.keys(worker2.store.faults).length, 1);
  const worker3 = handoff.createWorker(worker2.snapshot());
  assert.strictEqual(worker3.generation, 3);
  const afterRestart = worker3.processFault(base({ source: "FAULT_REPORT", eventId: "RPT-SYN-2001" }), {
    now: "2026-08-31T02:07:00Z"
  });
  assert.strictEqual(afterRestart.status, "REPLAY_NOOP");
  assert.strictEqual(afterRestart.effectCounts.dispatches, 1);
  assert.strictEqual(afterRestart.technicianHandoff.id, crashed.technicianHandoff.id);
}

{
  const worker1 = handoff.createWorker();
  const crashed = worker1.processFault(base(), { crashAt: "after_parts", now: "2026-08-31T02:08:00Z" });
  assert.strictEqual(crashed.status, "CRASHED_AFTER_PARTS");
  assert.strictEqual(crashed.effectCounts.dispatches, 1);
  assert.strictEqual(crashed.statusReceipt, null);
  const worker2 = handoff.createWorker(worker1.snapshot());
  const resumed = worker2.processFault(base(), { now: "2026-08-31T02:09:00Z" });
  assert.strictEqual(resumed.status, "DISPATCHED");
  assert.strictEqual(resumed.technicianHandoff.id, crashed.technicianHandoff.id);
  assert.strictEqual(resumed.partsRequest.id, crashed.partsRequest.id);
  assert.strictEqual(resumed.effectCounts.dispatches, 1);
}

{
  const store = handoff.createStore();
  run(base(), store, { crashAt: "after_tech" });
  const rolled = handoff.rollback("FAULT-SYN-7701", store, { now: "2026-08-31T02:10:00Z" });
  assert.strictEqual(rolled.status, "ROLLED_BACK");
  assert.strictEqual(rolled.technicianHandoff, null);
  assert.strictEqual(rolled.effectCounts.dispatches, 0);
  assert.ok(rolled.progressReceipt.createdAt);
  const rerun = run(base(), store, { now: "2026-08-31T02:11:00Z" });
  assert.strictEqual(rerun.status, "DISPATCHED");
  assert.strictEqual(rerun.technicianHandoff.id, "FAULT-SYN-7701:tech");
  assert.strictEqual(rerun.effectCounts.dispatches, 1);
  const keep = handoff.rollback("FAULT-SYN-7701", store);
  assert.strictEqual(keep.status, "NOT_ROLLBACKABLE");
  assert.strictEqual(keep.effectCounts.dispatches, 1);
}

{
  const store = handoff.createStore();
  const first = run(base(), store);
  const conflict = run(base({
    faultClass: "vibration",
    fields: {
      plantId: "PLANT-RIVERBEND-DEMO",
      assetId: "ASSET-KILN-04-DEMO",
      faultCode: "VIBRATION",
      severity: "HIGH",
      observedAt: "2026-08-31T01:40:00Z",
      windowId: "WIN-SYN-A1",
      partsNeeded: "YES"
    }
  }), store);
  assert.strictEqual(conflict.status, "FAULT_CONFLICT");
  assert.strictEqual(conflict.storedFingerprint, first.fingerprint);
  assert.strictEqual(conflict.effectCounts.dispatches, 1);
  assert.strictEqual(conflict.technicianHandoff.id, first.technicianHandoff.id);
  assert.strictEqual(conflict.cashUsd, 0);
}

{
  const store = handoff.createStore();
  const dirty = base();
  dirty.fields.operatorName = "DO_NOT_USE";
  dirty.fields.phone = "555-010-9999";
  const r = run(dirty, store);
  assert.strictEqual(r.status, "PII_REFUSED");
  assert.strictEqual(r.technicianHandoff, null);
  assert.strictEqual(r.effectCounts.dispatches, 0);
  assert.strictEqual(r.piiEmitted, 0);
  assert.ok(r.statusReceipt.hits.indexOf("fields.operatorName") !== -1);
  const replay = run(dirty, store, { now: "2026-08-31T02:12:00Z" });
  assert.strictEqual(replay.status, "REPLAY_NOOP");
  assert.strictEqual(replay.technicianHandoff, null);
}

console.log("plant-downtime-handoff: 10 scenarios PASS");
