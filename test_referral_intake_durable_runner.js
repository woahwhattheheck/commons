"use strict";
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const runner = path.resolve(__dirname, "host", "referral_intake_durable_runner.js");

function packet(overrides) {
  const base = {
    referralId: "REF-SYN-4401",
    referralClass: "imaging-slot",
    submittedAt: "2026-09-13T08:00:00Z",
    fields: {
      referringClinicId: "CLINIC-NORTHBRIDGE-DEMO",
      destinationClinicId: "CLINIC-CEDAR-HOLLOW-DEMO",
      laterality: "LEFT",
      insuranceAuthFlag: "ATTACHED",
      preferredWindow: "2026-09-14/AM"
    }
  };
  return Object.assign(base, overrides || {});
}

function write(filePath, value) {
  fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + "\n");
}

function invoke(args) {
  const out = spawnSync(process.execPath, [runner].concat(args), { encoding: "utf8" });
  let body;
  try {
    body = JSON.parse(out.stdout);
  } catch (_error) {
    throw new Error("runner emitted non-JSON stdout; status=" + out.status + " stdout=" + out.stdout + " stderr=" + out.stderr);
  }
  return { status: out.status, body, stderr: out.stderr };
}

function fresh() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "referral-durable-"));
}

function setup(dir, value) {
  const packetPath = path.join(dir, "packet.json");
  write(packetPath, value || packet());
  return { packet: packetPath, journal: path.join(dir, "journal.json") };
}

{
  const dir = fresh();
  const files = setup(dir);
  const crashed = invoke(["run", "--packet", files.packet, "--journal", files.journal, "--now", "2026-09-13T08:00:00Z", "--crash-at", "after_checklist"]);
  assert.strictEqual(crashed.status, 75);
  assert.strictEqual(crashed.body.core.status, "CRASHED_AFTER_CHECKLIST");
  assert.strictEqual(crashed.body.durability.generationAfter, 1);
  const disk = fs.readFileSync(files.journal, "utf8");
  assert.ok(!disk.includes("CLINIC-NORTHBRIDGE-DEMO"));
  assert.ok(!disk.includes("2026-09-14/AM"));
  const resumed = invoke(["run", "--packet", files.packet, "--journal", files.journal, "--now", "2026-09-13T08:01:00Z"]);
  assert.strictEqual(resumed.status, 0);
  assert.strictEqual(resumed.body.core.status, "QUEUED_COMPLETE");
  assert.strictEqual(resumed.body.core.queueEntry.id, "REF-SYN-4401:queue");
  assert.deepStrictEqual(resumed.body.core.effectCounts, { checklists: 1, queueEntries: 1, intakeReceipts: 1, progressReceipts: 1 });
  assert.strictEqual(resumed.body.durability.generationAfter, 2);
  fs.rmSync(dir, { recursive: true, force: true });
}

{
  const dir = fresh();
  const files = setup(dir);
  const crashed = invoke(["run", "--packet", files.packet, "--journal", files.journal, "--crash-at", "after_queue"]);
  assert.strictEqual(crashed.status, 75);
  assert.strictEqual(crashed.body.core.status, "CRASHED_AFTER_QUEUE");
  assert.strictEqual(crashed.body.core.effectCounts.queueEntries, 1);
  const resumed = invoke(["run", "--packet", files.packet, "--journal", files.journal]);
  assert.strictEqual(resumed.status, 0);
  assert.strictEqual(resumed.body.core.status, "QUEUED_COMPLETE");
  assert.strictEqual(resumed.body.core.queueEntry.id, crashed.body.core.queueEntry.id);
  fs.rmSync(dir, { recursive: true, force: true });
}

{
  const dir = fresh();
  const files = setup(dir);
  assert.strictEqual(invoke(["run", "--packet", files.packet, "--journal", files.journal, "--crash-at", "after_queue"]).status, 75);
  const rolled = invoke(["rollback", "--referral-id", "REF-SYN-4401", "--journal", files.journal, "--now", "2026-09-13T08:02:00Z"]);
  assert.strictEqual(rolled.status, 0);
  assert.strictEqual(rolled.body.core.status, "ROLLED_BACK");
  assert.strictEqual(rolled.body.core.queueEntry, null);
  const rerun = invoke(["run", "--packet", files.packet, "--journal", files.journal, "--now", "2026-09-13T08:03:00Z"]);
  assert.strictEqual(rerun.body.core.status, "QUEUED_COMPLETE");
  assert.strictEqual(rerun.body.core.effectCounts.queueEntries, 1);
  fs.rmSync(dir, { recursive: true, force: true });
}

{
  const dir = fresh();
  const files = setup(dir);
  assert.strictEqual(invoke(["run", "--packet", files.packet, "--journal", files.journal]).status, 0);
  const before = fs.readFileSync(files.journal);
  const changed = packet();
  changed.fields.laterality = "RIGHT";
  write(files.packet, changed);
  const conflict = invoke(["run", "--packet", files.packet, "--journal", files.journal]);
  assert.strictEqual(conflict.status, 1);
  assert.strictEqual(conflict.body.error.code, "DURABLE_PACKET_CONFLICT");
  assert.deepStrictEqual(fs.readFileSync(files.journal), before);
  fs.rmSync(dir, { recursive: true, force: true });
}

{
  const dir = fresh();
  const files = setup(dir);
  assert.strictEqual(invoke(["run", "--packet", files.packet, "--journal", files.journal]).status, 0);
  const journal = JSON.parse(fs.readFileSync(files.journal, "utf8"));
  journal.generation += 9;
  write(files.journal, journal);
  const tampered = fs.readFileSync(files.journal);
  const run = invoke(["run", "--packet", files.packet, "--journal", files.journal]);
  assert.strictEqual(run.status, 1);
  assert.strictEqual(run.body.error.code, "JOURNAL_INTEGRITY_MISMATCH");
  assert.deepStrictEqual(fs.readFileSync(files.journal), tampered);
  fs.rmSync(dir, { recursive: true, force: true });
}

{
  const dir = fresh();
  const dirty = packet();
  dirty.fields.patientName = "DO_NOT_PERSIST";
  dirty.fields.diagnosis = "DO_NOT_PERSIST";
  const files = setup(dir, dirty);
  const refused = invoke(["run", "--packet", files.packet, "--journal", files.journal]);
  assert.strictEqual(refused.status, 0);
  assert.strictEqual(refused.body.core.status, "PHI_REFUSED");
  assert.strictEqual(refused.body.durability.statePersisted, false);
  const disk = fs.readFileSync(files.journal, "utf8");
  assert.ok(!disk.includes("DO_NOT_PERSIST"));
  assert.ok(!disk.includes("patientName"));
  assert.ok(!disk.includes("diagnosis"));
  const state = JSON.parse(disk);
  assert.deepStrictEqual(state.referrals, {});
  assert.deepStrictEqual(state.packetBindings, {});
  fs.rmSync(dir, { recursive: true, force: true });
}

{
  const dir = fresh();
  const files = setup(dir);
  const real = path.join(dir, "real.json");
  write(real, {});
  fs.symlinkSync(real, files.journal);
  const refused = invoke(["run", "--packet", files.packet, "--journal", files.journal]);
  assert.strictEqual(refused.status, 1);
  assert.strictEqual(refused.body.error.code, "SYMLINK_REFUSED");
  fs.rmSync(dir, { recursive: true, force: true });
}

{
  const dir = fresh();
  const files = setup(dir);
  fs.mkdirSync(files.journal + ".lock");
  write(path.join(files.journal + ".lock", "owner.json"), { pid: 99999999 });
  const recovered = invoke(["run", "--packet", files.packet, "--journal", files.journal]);
  assert.strictEqual(recovered.status, 0);
  assert.strictEqual(recovered.body.core.status, "QUEUED_COMPLETE");
  assert.ok(!fs.existsSync(files.journal + ".lock"));
  fs.rmSync(dir, { recursive: true, force: true });
}

{
  const dir = fresh();
  const files = setup(dir);
  fs.mkdirSync(files.journal + ".lock");
  write(path.join(files.journal + ".lock", "owner.json"), { pid: process.pid });
  const busy = invoke(["run", "--packet", files.packet, "--journal", files.journal]);
  assert.strictEqual(busy.status, 1);
  assert.strictEqual(busy.body.error.code, "JOURNAL_BUSY");
  fs.rmSync(dir, { recursive: true, force: true });
}

{
  const dir = fresh();
  const files = setup(dir);
  invoke(["run", "--packet", files.packet, "--journal", files.journal]);
  const verify = invoke(["verify", "--journal", files.journal]);
  assert.strictEqual(verify.status, 0);
  assert.strictEqual(verify.body.valid, true);
  assert.strictEqual(verify.body.referralCount, 1);
  assert.strictEqual(verify.body.packetBindingCount, 1);
  const copy = Object.assign({}, verify.body);
  const claimed = copy.verificationSha256;
  delete copy.verificationSha256;
  const lib = require(runner);
  assert.strictEqual(claimed, lib.sha256Text(lib.canonical(copy)));
  fs.rmSync(dir, { recursive: true, force: true });
}

console.log("referral-intake-durable-runner: 10 scenarios PASS");
