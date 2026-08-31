"use strict";
const assert = require("assert");
const rescue = require("./dealer-service-lead-rescue.js");

function base(overrides) {
  const extra = overrides || {};
  const fieldsIn = extra.fields || {};
  const fields = Object.assign({
    dealerId: "DEALER-RIVERVIEW-DEMO",
    vehicleSlot: "VEH-SYN-F150-04-DEMO",
    concernCode: "OIL_CHANGE",
    preferredWindow: "AM",
    mileageBand: "5K_15K"
  }, fieldsIn);
  const packet = Object.assign({
    leadId: "LEAD-SYN-1101",
    leadClass: "oil-change",
    source: "WEB_FORM",
    inquiryId: "FORM-SYN-2001",
    submittedAt: "2026-08-31T03:00:00Z"
  }, extra);
  packet.fields = fields;
  return packet;
}

function run(input, store, options) {
  return rescue.processLead(input, store, Object.assign({ now: "2026-08-31T03:00:00Z" }, options || {}));
}

{
  const store = rescue.createStore();
  const r = run(base(), store);
  assert.strictEqual(r.status, "RESCUED");
  assert.strictEqual(r.idempotencyKey, "LEAD-SYN-1101");
  assert.strictEqual(r.followUp.id, "LEAD-SYN-1101:followup");
  assert.strictEqual(r.followUp.lane, "FOLLOWUP_EXPRESS");
  assert.strictEqual(r.appointment.id, "LEAD-SYN-1101:appt");
  assert.strictEqual(r.appointment.kind, "BOOKED_SERVICE_CRM_RECORD");
  assert.strictEqual(r.appointment.lane, "APPT_QUICK_LANE");
  assert.strictEqual(r.statusReceipt.kind, "RESCUE_STATUS_RECEIPT");
  assert.deepStrictEqual(r.effectCounts, {
    classifications: 1,
    followUps: 1,
    appointments: 1,
    crmRecords: 1,
    statusReceipts: 1,
    progressReceipts: 1,
    dispatches: 1
  });
  assert.strictEqual(r.liveCrmWrites, 0);
  assert.strictEqual(r.realDealerships, 0);
  assert.strictEqual(r.outreach, 0);
  assert.strictEqual(r.piiEmitted, 0);
  assert.strictEqual(r.cashUsd, 0);
}

{
  const store = rescue.createStore();
  const input = base();
  input.fields.preferredWindow = "UNKNOWN";
  const r = run(input, store);
  assert.strictEqual(r.status, "HELD_INCOMPLETE");
  assert.strictEqual(r.followUp, null);
  assert.strictEqual(r.appointment, null);
  assert.strictEqual(r.effectCounts.dispatches, 0);
  assert.deepStrictEqual(r.statusReceipt.operationalHold, ["preferredWindow"]);
}

{
  const expected = {
    "oil-change": ["FOLLOWUP_EXPRESS", "APPT_QUICK_LANE"],
    "brake-service": ["FOLLOWUP_ADVISOR", "APPT_SHOP_BAY"],
    "recall-campaign": ["FOLLOWUP_RECALL", "APPT_RECALL_LANE"],
    "check-engine": ["FOLLOWUP_DIAG", "APPT_DIAG_BAY"]
  };
  const codes = ["OIL_CHANGE", "BRAKE_SERVICE", "RECALL", "CHECK_ENGINE"];
  Object.keys(expected).forEach(function (cls, i) {
    const r = run(base({
      leadId: "LEAD-SYN-M" + i,
      leadClass: cls,
      inquiryId: "FORM-SYN-M" + i,
      fields: {
        dealerId: "DEALER-RIVERVIEW-DEMO",
        vehicleSlot: "VEH-SYN-F150-04-DEMO",
        concernCode: codes[i],
        preferredWindow: "AM",
        mileageBand: "5K_15K"
      }
    }), rescue.createStore());
    assert.strictEqual(r.status, "RESCUED", cls);
    assert.strictEqual(r.followUp.lane, expected[cls][0], cls);
    assert.strictEqual(r.appointment.lane, expected[cls][1], cls);
    assert.strictEqual(r.effectCounts.appointments, 1, cls);
  });
}

{
  const store = rescue.createStore();
  const form = base({ source: "WEB_FORM", inquiryId: "FORM-SYN-2001" });
  const first = run(form, store);
  const dupForm = run(form, store, { now: "2026-08-31T03:01:00Z" });
  const afterHours = run(base({ source: "AFTER_HOURS", inquiryId: "AFT-SYN-3001" }), store, {
    now: "2026-08-31T03:02:00Z"
  });
  assert.strictEqual(first.status, "RESCUED");
  assert.strictEqual(dupForm.status, "REPLAY_NOOP");
  assert.strictEqual(afterHours.status, "REPLAY_NOOP");
  assert.strictEqual(dupForm.appointment.id, first.appointment.id);
  assert.strictEqual(afterHours.appointment.id, first.appointment.id);
  assert.strictEqual(afterHours.followUp.id, first.followUp.id);
  assert.strictEqual(afterHours.effectCounts.appointments, 1);
  assert.strictEqual(afterHours.effectCounts.followUps, 1);
  assert.strictEqual(Object.keys(store.leads).length, 1);
  assert.strictEqual(afterHours.inquiries.length, 2);
}

{
  const store = rescue.createStore();
  const crashed = run(base(), store, { crashAt: "after_classify" });
  assert.strictEqual(crashed.status, "CRASHED_AFTER_CLASSIFY");
  assert.strictEqual(crashed.effectCounts.dispatches, 0);
  assert.ok(crashed.progressReceipt.createdAt);
  const resumed = run(base(), store, { now: "2026-08-31T03:03:00Z" });
  assert.strictEqual(resumed.status, "RESCUED");
  assert.strictEqual(resumed.effectCounts.appointments, 1);
  assert.strictEqual(resumed.appointment.id, "LEAD-SYN-1101:appt");
}

{
  const worker1 = rescue.createWorker();
  assert.strictEqual(worker1.generation, 1);
  const crashed = worker1.processLead(base({ source: "WEB_FORM", inquiryId: "FORM-SYN-2001" }), {
    crashAt: "after_followup",
    now: "2026-08-31T03:04:00Z"
  });
  assert.strictEqual(crashed.status, "CRASHED_AFTER_FOLLOWUP");
  assert.strictEqual(crashed.effectCounts.followUps, 1);
  assert.strictEqual(crashed.effectCounts.appointments, 0);
  assert.strictEqual(crashed.effectCounts.dispatches, 0);
  const worker2 = rescue.createWorker(worker1.snapshot());
  assert.strictEqual(worker2.generation, 2);
  assert.notStrictEqual(worker2.store, worker1.store);
  const dupForm = worker2.processLead(base({ source: "WEB_FORM", inquiryId: "FORM-SYN-2001" }), {
    now: "2026-08-31T03:05:00Z"
  });
  assert.strictEqual(dupForm.status, "RESCUED");
  assert.strictEqual(dupForm.followUp.id, crashed.followUp.id);
  const afterHours = worker2.processLead(base({ source: "AFTER_HOURS", inquiryId: "AFT-SYN-3001" }), {
    now: "2026-08-31T03:06:00Z"
  });
  assert.strictEqual(afterHours.status, "REPLAY_NOOP");
  assert.strictEqual(afterHours.effectCounts.appointments, 1);
  assert.strictEqual(afterHours.effectCounts.followUps, 1);
  assert.strictEqual(afterHours.effectCounts.crmRecords, 1);
  assert.strictEqual(Object.keys(worker2.store.leads).length, 1);
  const worker3 = rescue.createWorker(worker2.snapshot());
  assert.strictEqual(worker3.generation, 3);
  const afterRestart = worker3.processLead(base({ source: "AFTER_HOURS", inquiryId: "AFT-SYN-3001" }), {
    now: "2026-08-31T03:07:00Z"
  });
  assert.strictEqual(afterRestart.status, "REPLAY_NOOP");
  assert.strictEqual(afterRestart.effectCounts.appointments, 1);
  assert.strictEqual(afterRestart.appointment.id, dupForm.appointment.id);
}

{
  const worker1 = rescue.createWorker();
  const crashed = worker1.processLead(base(), { crashAt: "after_appointment", now: "2026-08-31T03:08:00Z" });
  assert.strictEqual(crashed.status, "CRASHED_AFTER_APPOINTMENT");
  assert.strictEqual(crashed.effectCounts.appointments, 1);
  assert.strictEqual(crashed.statusReceipt, null);
  const worker2 = rescue.createWorker(worker1.snapshot());
  const resumed = worker2.processLead(base(), { now: "2026-08-31T03:09:00Z" });
  assert.strictEqual(resumed.status, "RESCUED");
  assert.strictEqual(resumed.followUp.id, crashed.followUp.id);
  assert.strictEqual(resumed.appointment.id, crashed.appointment.id);
  assert.strictEqual(resumed.effectCounts.appointments, 1);
}

{
  const store = rescue.createStore();
  run(base(), store, { crashAt: "after_followup" });
  const rolled = rescue.rollback("LEAD-SYN-1101", store, { now: "2026-08-31T03:10:00Z" });
  assert.strictEqual(rolled.status, "ROLLED_BACK");
  assert.strictEqual(rolled.followUp, null);
  assert.strictEqual(rolled.appointment, null);
  assert.strictEqual(rolled.effectCounts.dispatches, 0);
  assert.ok(rolled.progressReceipt.createdAt);
  const rerun = run(base(), store, { now: "2026-08-31T03:11:00Z" });
  assert.strictEqual(rerun.status, "RESCUED");
  assert.strictEqual(rerun.appointment.id, "LEAD-SYN-1101:appt");
  assert.strictEqual(rerun.effectCounts.appointments, 1);
  const keep = rescue.rollback("LEAD-SYN-1101", store);
  assert.strictEqual(keep.status, "NOT_ROLLBACKABLE");
  assert.strictEqual(keep.effectCounts.appointments, 1);
}

{
  const store = rescue.createStore();
  const first = run(base(), store);
  const conflict = run(base({
    leadClass: "brake-service",
    fields: {
      dealerId: "DEALER-RIVERVIEW-DEMO",
      vehicleSlot: "VEH-SYN-F150-04-DEMO",
      concernCode: "BRAKE_SERVICE",
      preferredWindow: "AM",
      mileageBand: "5K_15K"
    }
  }), store);
  assert.strictEqual(conflict.status, "LEAD_CONFLICT");
  assert.strictEqual(conflict.storedFingerprint, first.fingerprint);
  assert.strictEqual(conflict.effectCounts.appointments, 1);
  assert.strictEqual(conflict.appointment.id, first.appointment.id);
  assert.strictEqual(conflict.cashUsd, 0);
}

{
  const store = rescue.createStore();
  const dirty = base();
  dirty.fields.customerName = "DO_NOT_USE";
  dirty.fields.phone = "555-010-9999";
  const r = run(dirty, store);
  assert.strictEqual(r.status, "PII_REFUSED");
  assert.strictEqual(r.followUp, null);
  assert.strictEqual(r.appointment, null);
  assert.strictEqual(r.effectCounts.dispatches, 0);
  assert.strictEqual(r.piiEmitted, 0);
  assert.ok(r.statusReceipt.hits.indexOf("fields.customerName") !== -1);
  const replay = run(dirty, store, { now: "2026-08-31T03:12:00Z" });
  assert.strictEqual(replay.status, "REPLAY_NOOP");
  assert.strictEqual(replay.appointment, null);
}

console.log("dealer-service-lead-rescue: 10 scenarios PASS");
