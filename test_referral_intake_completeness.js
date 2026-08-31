"use strict";
const assert = require("assert");
const intake = require("./referral-intake-completeness.js");

function base(overrides) {
  return Object.assign({
    referralId: "REF-SYN-4401",
    referralClass: "imaging-slot",
    submittedAt: "2026-08-31T02:00:00Z",
    fields: {
      referringClinicId: "CLINIC-NORTHBRIDGE-DEMO",
      destinationClinicId: "CLINIC-CEDAR-HOLLOW-DEMO",
      laterality: "LEFT",
      insuranceAuthFlag: "ATTACHED",
      preferredWindow: "2026-09-08/AM"
    }
  }, overrides || {});
}

function run(input, journal, options) {
  return intake.processReferral(input, journal, Object.assign({ now: "2026-08-31T02:00:00Z" }, options || {}));
}

{
  const journal = intake.createJournal();
  const r = run(base(), journal);
  assert.strictEqual(r.status, "QUEUED_COMPLETE");
  assert.strictEqual(r.queueEntry.lane, "IMAGING_SCHEDULING");
  assert.strictEqual(r.queueEntry.id, "REF-SYN-4401:queue");
  assert.strictEqual(r.intakeReceipt.kind, "REFERRAL_INTAKE_RECEIPT");
  assert.deepStrictEqual(r.effectCounts, { checklists: 1, queueEntries: 1, intakeReceipts: 1, progressReceipts: 1 });
  assert.strictEqual(r.clinicalDecision, "NONE_INTAKE_ONLY");
  assert.strictEqual(r.diagnoses, 0);
  assert.strictEqual(r.careApprovals, 0);
  assert.strictEqual(r.careDenials, 0);
  assert.strictEqual(r.treatmentAdvice, 0);
  assert.strictEqual(r.phiEmitted, 0);
  assert.strictEqual(r.cashUsd, 0);
}

{
  const journal = intake.createJournal();
  const input = base();
  input.fields.insuranceAuthFlag = "MISSING";
  const r = run(input, journal);
  assert.strictEqual(r.status, "QUEUED_INCOMPLETE");
  assert.strictEqual(r.queueEntry.lane, "INCOMPLETE_INTAKE");
  assert.deepStrictEqual(r.intakeReceipt.operationalHold, ["insuranceAuthFlag"]);
  assert.strictEqual(r.queueEntry.completeness, "INCOMPLETE");
}

{
  const expected = {
    "imaging-slot": "IMAGING_SCHEDULING",
    "specialist-consult": "SPECIALIST_INTAKE",
    "procedure-slot": "PROCEDURE_SCHEDULING",
    "records-transfer": "RECORDS_INTAKE"
  };
  Object.keys(expected).forEach(function (cls, i) {
    const fields = {};
    intake.CLASSES[cls].required.forEach(function (key) {
      if (key === "referringClinicId") fields[key] = "CLINIC-NORTHBRIDGE-DEMO";
      else if (key === "destinationClinicId") fields[key] = "CLINIC-CEDAR-HOLLOW-DEMO";
      else if (key === "preferredWindow") fields[key] = "2026-09-08/AM";
      else fields[key] = intake.ENUMS[key][0];
    });
    const r = run(base({ referralId: "REF-SYN-M" + i, referralClass: cls, fields: fields }), intake.createJournal());
    assert.strictEqual(r.status, "QUEUED_COMPLETE", cls);
    assert.strictEqual(r.queueEntry.lane, expected[cls], cls);
  });
}

{
  const journal = intake.createJournal();
  const first = run(base(), journal);
  const replay = run(base(), journal, { now: "2026-08-31T02:01:00Z" });
  assert.strictEqual(replay.status, "REPLAY_NOOP");
  assert.strictEqual(replay.queueEntry.id, first.queueEntry.id);
  assert.strictEqual(replay.intakeReceipt.id, first.intakeReceipt.id);
  assert.deepStrictEqual(replay.effectCounts, { checklists: 1, queueEntries: 1, intakeReceipts: 1, progressReceipts: 1 });
  assert.strictEqual(Object.keys(journal.referrals).length, 1);
}

{
  const journal = intake.createJournal();
  const crashed = run(base(), journal, { crashAt: "after_checklist" });
  assert.strictEqual(crashed.status, "CRASHED_AFTER_CHECKLIST");
  assert.deepStrictEqual(crashed.effectCounts, { checklists: 1, queueEntries: 0, intakeReceipts: 0, progressReceipts: 1 });
  assert.ok(crashed.progressReceipt.createdAt);
  const resumed = run(base(), journal, { now: "2026-08-31T02:02:00Z" });
  assert.strictEqual(resumed.status, "QUEUED_COMPLETE");
  assert.deepStrictEqual(resumed.effectCounts, { checklists: 1, queueEntries: 1, intakeReceipts: 1, progressReceipts: 1 });
  assert.strictEqual(resumed.queueEntry.id, "REF-SYN-4401:queue");
}

{
  const journal = intake.createJournal();
  const crashed = run(base(), journal, { crashAt: "after_queue" });
  assert.strictEqual(crashed.status, "CRASHED_AFTER_QUEUE");
  assert.deepStrictEqual(crashed.effectCounts, { checklists: 1, queueEntries: 1, intakeReceipts: 0, progressReceipts: 1 });
  const resumed = run(base(), journal, { now: "2026-08-31T02:03:00Z" });
  assert.strictEqual(resumed.status, "QUEUED_COMPLETE");
  assert.strictEqual(resumed.queueEntry.id, crashed.queueEntry.id);
  assert.deepStrictEqual(resumed.effectCounts, { checklists: 1, queueEntries: 1, intakeReceipts: 1, progressReceipts: 1 });
}

{
  const journal = intake.createJournal();
  run(base(), journal, { crashAt: "after_queue" });
  const rolled = intake.rollback("REF-SYN-4401", journal, { now: "2026-08-31T02:04:00Z" });
  assert.strictEqual(rolled.status, "ROLLED_BACK");
  assert.strictEqual(rolled.queueEntry, null);
  assert.ok(rolled.progressReceipt.createdAt);
  assert.deepStrictEqual(rolled.effectCounts, { checklists: 0, queueEntries: 0, intakeReceipts: 0, progressReceipts: 1 });
  const rerun = run(base(), journal, { now: "2026-08-31T02:05:00Z" });
  assert.strictEqual(rerun.status, "QUEUED_COMPLETE");
  assert.strictEqual(rerun.queueEntry.id, "REF-SYN-4401:queue");
}

{
  const journal = intake.createJournal();
  const first = run(base(), journal);
  const conflict = run(base({ referralClass: "records-transfer", fields: {
    referringClinicId: "CLINIC-NORTHBRIDGE-DEMO",
    destinationClinicId: "CLINIC-CEDAR-HOLLOW-DEMO",
    recordsSetFlag: "PACKET-INDEX-ONLY",
    releaseAttestation: "SYNTHETIC-ATTESTED"
  } }), journal);
  assert.strictEqual(conflict.status, "REFERRAL_CONFLICT");
  assert.strictEqual(conflict.storedFingerprint, first.fingerprint);
  assert.deepStrictEqual(conflict.effectCounts, { checklists: 1, queueEntries: 1, intakeReceipts: 1, progressReceipts: 1 });
  assert.strictEqual(conflict.careApprovals, 0);
}

{
  const journal = intake.createJournal();
  const dirty = base();
  dirty.fields.patientName = "DO_NOT_USE";
  dirty.fields.diagnosis = "invented";
  const r = run(dirty, journal);
  assert.strictEqual(r.status, "PHI_REFUSED");
  assert.strictEqual(r.queueEntry, null);
  assert.strictEqual(r.phiEmitted, 0);
  assert.ok(r.intakeReceipt.hits.indexOf("fields.patientName") !== -1);
  const replay = run(dirty, journal, { now: "2026-08-31T02:06:00Z" });
  assert.strictEqual(replay.status, "REPLAY_NOOP");
  assert.strictEqual(replay.queueEntry, null);
}

console.log("referral-intake-completeness: 9 scenarios PASS");
