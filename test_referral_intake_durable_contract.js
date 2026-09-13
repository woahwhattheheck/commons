"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");

const root = __dirname;
const html = fs.readFileSync(path.join(root, "referral-intake-completeness.html"), "utf8");
const contract = JSON.parse(fs.readFileSync(path.join(root, "revenue", "referral_intake_completeness", "contract.json"), "utf8"));
const checkout = "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c";

assert.strictEqual(contract.id, "referral-intake-completeness");
assert.strictEqual(contract.version, 3);
assert.strictEqual(contract.commercial.diagnostic_usd, 199);
assert.strictEqual(contract.commercial.optional_pilot_usd, 2500);
assert.strictEqual(contract.commercial.cash_usd, 0);
assert.strictEqual(contract.runner.path, "host/referral_intake_durable_runner.js");
assert.strictEqual(contract.runner.injected_crash_exit, 75);
assert.strictEqual(contract.runner.journal_schema, "commons-referral-intake-durable-journal-v1");
assert.strictEqual(contract.runner.receipt_schema, "commons-referral-intake-durable-receipt-v1");
assert.strictEqual(contract.runner.verification_schema, "commons-referral-intake-journal-verification-v1");
assert.ok(contract.acceptance.some((row) => row.includes("fresh Node process")));
assert.ok(contract.acceptance.some((row) => row.includes("PHI-refused state")));
assert.ok(contract.data_boundary.includes("no server submission"));

assert.strictEqual(html.split(checkout).length - 1, 2, "existing live checkout URL must remain exactly twice");
assert.ok(html.includes('data-durable-runner="1"'));
assert.ok(html.includes('./host/referral_intake_durable_runner.js'));
assert.ok(html.includes("browser-local checkpoint preview"));
assert.ok(html.includes("paid delivery proof uses an atomically persisted local journal and a fresh process restart"));
assert.ok(html.includes("PHI-refused state is not persisted"));
assert.ok(html.includes("$199 · one business day"));
assert.ok(html.includes("$2,500 after-fit pilot"));
assert.ok(html.includes("If the accepted diagnostic is not delivered inside the one-business-day window"));

console.log("referral-intake-durable-contract: PASS");
