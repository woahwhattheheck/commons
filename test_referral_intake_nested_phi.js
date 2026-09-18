"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const runner = path.resolve(__dirname, "host", "referral_intake_durable_runner.js");

function packet(extraFields) {
  return {
    referralId: "REF-SYN-9913",
    referralClass: "imaging-slot",
    submittedAt: "2026-09-13T08:13:00Z",
    fields: Object.assign({
      referringClinicId: "CLINIC-NORTHBRIDGE-DEMO",
      destinationClinicId: "CLINIC-CEDAR-HOLLOW-DEMO",
      laterality: "LEFT",
      insuranceAuthFlag: "ATTACHED",
      preferredWindow: "2026-09-14/AM"
    }, extraFields || {})
  };
}

function write(filePath, value) {
  fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + "\n");
}

function invoke(packetValue) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "referral-nested-phi-"));
  const packetPath = path.join(dir, "packet.json");
  const journalPath = path.join(dir, "journal.json");
  write(packetPath, packetValue);
  const proc = spawnSync(process.execPath, [
    runner, "run", "--packet", packetPath, "--journal", journalPath,
    "--now", "2026-09-13T08:13:00Z"
  ], { encoding: "utf8" });
  let body;
  try {
    body = JSON.parse(proc.stdout);
  } catch (_error) {
    throw new Error("runner emitted non-JSON stdout: " + proc.stdout + " stderr=" + proc.stderr);
  }
  const journal = fs.existsSync(journalPath) ? JSON.parse(fs.readFileSync(journalPath, "utf8")) : null;
  const journalText = fs.existsSync(journalPath) ? fs.readFileSync(journalPath, "utf8") : "";
  fs.rmSync(dir, { recursive: true, force: true });
  return { status: proc.status, body, journal, journalText };
}

function assertRefused(value, forbiddenFragments) {
  const out = invoke(value);
  assert.strictEqual(out.status, 0);
  assert.strictEqual(out.body.core.status, "PHI_REFUSED");
  assert.strictEqual(out.body.durability.statePersisted, false);
  assert.ok(out.journal);
  assert.deepStrictEqual(out.journal.referrals, {});
  assert.deepStrictEqual(out.journal.packetBindings, {});
  (forbiddenFragments || []).forEach((fragment) => {
    assert.ok(!out.journalText.includes(fragment), "journal must not persist " + fragment);
  });
}

assertRefused(packet({
  note: { patientName: "DO_NOT_PERSIST", diagnosis: "DO_NOT_PERSIST" }
}), ["DO_NOT_PERSIST", "patientName", "diagnosis"]);

assertRefused(packet({
  note: [{ contact: { ssn: "123-45-6789" } }]
}), ["123-45-6789", "ssn"]);

assertRefused(packet({
  note: { harmless: "still an unsupported nested shape" }
}), ["unsupported nested shape"]);

const oversized = {};
for (let i = 0; i < 300; i += 1) oversized["extra" + i] = "synthetic-" + i;
assertRefused(packet(oversized), ["synthetic-299"]);

console.log("referral-intake-nested-phi: 4 fail-closed scenarios PASS");
