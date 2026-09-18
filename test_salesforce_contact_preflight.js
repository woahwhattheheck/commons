"use strict";
const assert = require("assert");
const preflight = require("./salesforce-contact-preflight.js");

const events = [
  { event_id: "e1", operation: "create", fields: { external_id: "A-1", email: "Ada@Example.org", first_name: "Ada", department: "Programs" } },
  { event_id: "e2", operation: "create", fields: { external_id: "B-2", email: "Grace@example.org", first_name: "Grace", department: "Operations" } },
  { event_id: "e3", operation: "update", match_key: "external_id:a-1", fields: { last_name: "Lovelace", department: "Programs" } },
  { event_id: "e4", operation: "create", fields: { external_id: "A-1", email: "Ada@Example.org" } },
  { event_id: "e5", operation: "create", fields: { external_id: "A-1", email: "other@example.org" } },
  { event_id: "e6", operation: "create", fields: { email: "ada.alt@example.org", first_name: "Ada" } },
  { event_id: "e7", operation: "merge", source_key: "email:ada.alt@example.org", target_key: "external_id:a-1" },
  { event_id: "e3", operation: "update", match_key: "external_id:a-1", fields: { last_name: "Lovelace", department: "Programs" } },
  { event_id: "e3", operation: "update", match_key: "external_id:a-1", fields: { last_name: "Byron" } },
  { event_id: "e10", operation: "update", match_key: "email:missing@example.org", fields: { department: "Finance" } }
];

const first = preflight.run(events);
const second = preflight.run(JSON.parse(JSON.stringify(events)));
assert.deepStrictEqual(first, second, "same bytes must produce the same run");
assert.strictEqual(first.contacts.length, 2);
assert.strictEqual(first.dashboard.canonical_contacts, 2);
assert.deepStrictEqual(first.dashboard.department_counts, { operations: 1, programs: 1 });
assert.strictEqual(first.dashboard.reconciles, true);
assert.strictEqual(new Set(first.contacts.map(c => c.id)).size, first.contacts.length);
assert.strictEqual(first.totals.accepted + first.totals.rejected + first.totals.replayed, events.length);
assert.strictEqual(first.totals.submitted, events.length);
assert.strictEqual(first.receipts[0].reason, "CREATED");
assert.strictEqual(first.receipts[3].reason, "CREATE_NOOP");
assert.strictEqual(first.receipts[4].reason, "DUPLICATE_CONFLICT");
assert.strictEqual(first.receipts[6].reason, "MERGED");
assert.strictEqual(first.receipts[7].status, "REPLAYED");
assert.strictEqual(first.receipts[7].reason, "EXACT_REPLAY");
for (const item of first.receipts) {
  const core = Object.assign({}, item);
  delete core.receipt_hash;
  assert.strictEqual(item.receipt_hash, preflight.hash(core), "receipt hash must cover visible receipt bytes");
}
assert.strictEqual(first.receipts[8].reason, "EVENT_ID_CONFLICT");
assert.strictEqual(first.receipts[9].reason, "CONTACT_NOT_FOUND");
assert.throws(() => preflight.run({}), /events must be an array/);

const invalid = preflight.run([
  null,
  { event_id: "", operation: "create", fields: {} },
  { event_id: "x", operation: "delete", fields: { email: "x@example.org" } },
  { event_id: "y", operation: "create", fields: {} }
]);
assert.deepStrictEqual(invalid.receipts.map(r => r.reason), [
  "INVALID_EVENT", "MISSING_EVENT_ID", "INVALID_OPERATION", "MISSING_MATCH_KEY"
]);
assert.strictEqual(invalid.dashboard.reconciles, true);
console.log("salesforce-contact-preflight: 14 scenarios PASS");
