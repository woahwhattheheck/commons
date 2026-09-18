"use strict";
const assert = require("assert");
const rescue = require("./catering-deposit-rescue.js");

function inquiry(overrides) {
  return Object.assign({
    eventId: "CAT-1042",
    customer: "Riverside Robotics",
    eventDate: "2026-09-18",
    menu: "buffet",
    guests: 50,
    budgetCents: 160000,
    notes: "synthetic"
  }, overrides || {});
}
function run(input, journal, options) {
  return rescue.processInquiry(input, journal, Object.assign({ now: "2026-08-31T00:00:00Z" }, options || {}));
}

{
  const journal = rescue.createJournal();
  const result = run(inquiry(), journal);
  assert.strictEqual(result.status, "READY");
  assert.strictEqual(result.quote.totalCents, 137500);
  assert.strictEqual(result.quote.depositCents, 34375);
  assert.deepStrictEqual(result.effectCounts, { followups: 1, depositIntents: 1, staffExceptions: 0 });
  assert.strictEqual(result.paymentsProcessed, 0);
}
{
  const journal = rescue.createJournal();
  const first = run(inquiry(), journal);
  const replay = run(inquiry(), journal, { now: "2026-08-31T00:01:00Z" });
  assert.strictEqual(replay.status, "REPLAY_NOOP");
  assert.strictEqual(replay.effects.followup.id, first.effects.followup.id);
  assert.strictEqual(replay.effects.depositIntent.id, first.effects.depositIntent.id);
  assert.deepStrictEqual(replay.effectCounts, { followups: 1, depositIntents: 1, staffExceptions: 0 });
}
{
  const journal = rescue.createJournal();
  const result = run(inquiry({ menu: "invented-menu" }), journal);
  assert.strictEqual(result.status, "STAFF_EXCEPTION");
  assert.strictEqual(result.quote, null);
  assert.strictEqual(result.effects.staffException.reason, "UNKNOWN_MENU_RULE");
  assert.deepStrictEqual(result.effectCounts, { followups: 0, depositIntents: 0, staffExceptions: 1 });
}
{
  const journal = rescue.createJournal();
  const result = run(inquiry({ budgetCents: 100000 }), journal);
  assert.strictEqual(result.status, "STAFF_EXCEPTION");
  assert.strictEqual(result.effects.staffException.reason, "BUDGET_BELOW_RULES_TOTAL");
  assert.deepStrictEqual(result.effectCounts, { followups: 0, depositIntents: 0, staffExceptions: 1 });
}
{
  const journal = rescue.createJournal();
  const crashed = run(inquiry(), journal, { crashAt: "after_quote" });
  assert.strictEqual(crashed.status, "CRASHED_AFTER_QUOTE");
  assert.deepStrictEqual(crashed.effectCounts, { followups: 0, depositIntents: 0, staffExceptions: 0 });
  const resumed = run(inquiry(), journal, { now: "2026-08-31T00:02:00Z" });
  assert.strictEqual(resumed.status, "READY");
  assert.deepStrictEqual(resumed.effectCounts, { followups: 1, depositIntents: 1, staffExceptions: 0 });
}
{
  const journal = rescue.createJournal();
  const crashed = run(inquiry(), journal, { crashAt: "after_followup" });
  assert.strictEqual(crashed.status, "CRASHED_AFTER_FOLLOWUP");
  assert.deepStrictEqual(crashed.effectCounts, { followups: 1, depositIntents: 0, staffExceptions: 0 });
  const followupId = crashed.effects.followup.id;
  const resumed = run(inquiry(), journal, { now: "2026-08-31T00:03:00Z" });
  assert.strictEqual(resumed.status, "READY");
  assert.strictEqual(resumed.effects.followup.id, followupId);
  assert.deepStrictEqual(resumed.effectCounts, { followups: 1, depositIntents: 1, staffExceptions: 0 });
}
{
  const journal = rescue.createJournal();
  run(inquiry(), journal, { crashAt: "after_followup" });
  const rolled = rescue.rollback("CAT-1042", journal, { now: "2026-08-31T00:04:00Z" });
  assert.strictEqual(rolled.status, "ROLLED_BACK");
  assert.deepStrictEqual(rolled.effectCounts, { followups: 0, depositIntents: 0, staffExceptions: 0 });
  const retried = run(inquiry(), journal, { now: "2026-08-31T00:05:00Z" });
  assert.strictEqual(retried.status, "READY");
  assert.deepStrictEqual(retried.effectCounts, { followups: 1, depositIntents: 1, staffExceptions: 0 });
}
{
  const journal = rescue.createJournal();
  const first = run(inquiry(), journal);
  const conflict = run(inquiry({ customer: "Different bytes" }), journal);
  assert.strictEqual(conflict.status, "EVENT_CONFLICT");
  assert.strictEqual(conflict.storedFingerprint, first.fingerprint);
  assert.deepStrictEqual(conflict.effectCounts, { followups: 1, depositIntents: 1, staffExceptions: 0 });
}
console.log("catering-deposit-rescue: 8 scenarios PASS");
