"use strict";
const assert = require("assert");
const permit = require("./permit-intake-receipt.js");
function base(overrides) {
  return Object.assign({
    applicationId: "PERMIT-2048",
    permitType: "residential-remodel",
    submittedAt: "2026-08-31T00:00:00Z",
    items: {
      applicant: "Ada Rivera", parcelId: "17-042-008", siteAddress: "100 Civic Commons Way",
      scope: "Kitchen remodel", estimatedCost: "24000", ownerConsent: "attached"
    }
  }, overrides || {});
}
function run(input, journal, options) {
  return permit.processApplication(input, journal, Object.assign({ now: "2026-08-31T00:00:00Z" }, options || {}));
}
{
  const journal = permit.createJournal(), r = run(base(), journal);
  assert.strictEqual(r.status, "ROUTED_FOR_REVIEW");
  assert.strictEqual(r.queueRoute.queue, "RESIDENTIAL_BUILDING_REVIEW");
  assert.strictEqual(r.missingItemNotice, null);
  assert.deepStrictEqual(r.effectCounts, { checklists: 1, missingNotices: 0, queueRoutes: 1, applicantReceipts: 1 });
  assert.strictEqual(r.approvals, 0); assert.strictEqual(r.denials, 0);
}
{
  const journal = permit.createJournal(), input = base();
  input.items.ownerConsent = "";
  const r = run(input, journal);
  assert.strictEqual(r.status, "MISSING_ITEMS");
  assert.deepStrictEqual(r.missingItemNotice.missing, ["ownerConsent"]);
  assert.strictEqual(r.queueRoute.completeness, "INCOMPLETE");
  assert.deepStrictEqual(r.effectCounts, { checklists: 1, missingNotices: 1, queueRoutes: 1, applicantReceipts: 1 });
}
{
  const matrix = {
    "residential-remodel": "RESIDENTIAL_BUILDING_REVIEW",
    "commercial-tenant": "COMMERCIAL_PLAN_REVIEW",
    "sign": "ZONING_SIGN_REVIEW",
    "demolition": "SAFETY_DEMOLITION_REVIEW"
  };
  Object.keys(matrix).forEach(function(type, i){
    const items = {};
    permit.RULES[type].required.forEach(function(key){ items[key] = "present"; });
    const r = run(base({ applicationId: "P-"+i, permitType: type, items: items }), permit.createJournal());
    assert.strictEqual(r.queueRoute.queue, matrix[type]);
  });
}
{
  const journal = permit.createJournal(), first = run(base(), journal), replay = run(base(), journal, { now: "2026-08-31T00:01:00Z" });
  assert.strictEqual(replay.status, "REPLAY_NOOP");
  assert.strictEqual(replay.queueRoute.id, first.queueRoute.id);
  assert.strictEqual(replay.applicantReceipt.id, first.applicantReceipt.id);
  assert.deepStrictEqual(replay.effectCounts, { checklists: 1, missingNotices: 0, queueRoutes: 1, applicantReceipts: 1 });
}
{
  const journal = permit.createJournal(), crashed = run(base(), journal, { crashAt: "after_checklist" });
  assert.strictEqual(crashed.status, "CRASHED_AFTER_CHECKLIST");
  assert.deepStrictEqual(crashed.effectCounts, { checklists: 1, missingNotices: 0, queueRoutes: 0, applicantReceipts: 0 });
  const resumed = run(base(), journal, { now: "2026-08-31T00:02:00Z" });
  assert.strictEqual(resumed.status, "ROUTED_FOR_REVIEW");
  assert.deepStrictEqual(resumed.effectCounts, { checklists: 1, missingNotices: 0, queueRoutes: 1, applicantReceipts: 1 });
}
{
  const journal = permit.createJournal(), input = base(); input.items.ownerConsent = "";
  const crashed = run(input, journal, { crashAt: "after_notice" });
  assert.strictEqual(crashed.status, "CRASHED_AFTER_NOTICE");
  assert.deepStrictEqual(crashed.effectCounts, { checklists: 1, missingNotices: 1, queueRoutes: 0, applicantReceipts: 0 });
  const resumed = run(input, journal, { now: "2026-08-31T00:03:00Z" });
  assert.strictEqual(resumed.status, "MISSING_ITEMS");
  assert.deepStrictEqual(resumed.effectCounts, { checklists: 1, missingNotices: 1, queueRoutes: 1, applicantReceipts: 1 });
}
{
  const journal = permit.createJournal();
  run(base(), journal, { crashAt: "after_checklist" });
  const rolled = permit.rollback("PERMIT-2048", journal, { now: "2026-08-31T00:04:00Z" });
  assert.strictEqual(rolled.status, "ROLLED_BACK");
  assert.deepStrictEqual(rolled.effectCounts, { checklists: 0, missingNotices: 0, queueRoutes: 0, applicantReceipts: 0 });
  const rerun = run(base(), journal, { now: "2026-08-31T00:05:00Z" });
  assert.strictEqual(rerun.status, "ROUTED_FOR_REVIEW");
}
{
  const journal = permit.createJournal(), first = run(base(), journal);
  const conflict = run(base({ permitType: "sign" }), journal);
  assert.strictEqual(conflict.status, "APPLICATION_CONFLICT");
  assert.strictEqual(conflict.storedFingerprint, first.fingerprint);
  assert.deepStrictEqual(conflict.effectCounts, { checklists: 1, missingNotices: 0, queueRoutes: 1, applicantReceipts: 1 });
}
console.log("permit-intake-receipt: 8 scenarios PASS");
