#!/usr/bin/env node
import assert from 'node:assert/strict';
import {
  attachEvidence, emptyStore, exportSnapshot, ingest, recordArrival, transition, verifySnapshot,
} from './engine.mjs';

const baseMs = Date.parse('2026-09-13T09:00:00Z');
let ti = 0;
const now = () => new Date(baseMs + (ti++ * 60_000)).toISOString().replace('.000Z', 'Z');

function input(sourceKey, n, { complete = true } = {}) {
  return {
    sourceKey,
    contact: complete ? { name: `Synthetic Customer ${n}`, method: 'EMAIL', value: `synthetic${n}@example.test` } : { name: '', method: '', value: '' },
    vehicle: complete
      ? { vin: `1HGCM82633A00${String(4351 + n).padStart(4, '0')}`, plate: '', state: '', year: 2016 + n, make: 'Synthetic', model: `Model-${n}` }
      : { vin: '', plate: '', state: '', year: '', make: '', model: '' },
    symptoms: complete ? `Synthetic symptom ${n}` : '',
    requestedWork: complete ? ['Diagnostic inspection'] : [],
    dropoffMode: complete ? 'AFTER_HOURS_KEYBOX' : '',
    note: 'Synthetic acceptance fixture; no live customer data.',
  };
}

let store = emptyStore();
const one = ingest(store, input('accept-001', 1), { at: now() }); store = one.store;
const two = ingest(store, input('accept-002', 2, { complete: false }), { at: now() }); store = two.store;
const three = ingest(store, input('accept-003', 3), { at: now() }); store = three.store;
const four = ingest(store, input('accept-004', 4), { at: now() }); store = four.store;

// Exact source replay must not create another intake or history event.
const replay = ingest(store, input('accept-001', 1), { at: now() });
assert.equal(replay.receipt.replay, true);
assert.equal(replay.store.revision, store.revision);
store = replay.store;

const arrivalOne = recordArrival(store, {
  operationId: 'accept-arrival-1', intakeId: one.receipt.intakeId,
  vehicleFingerprint: one.receipt.vehicleFingerprint, channel: 'DOOR_QR', keyTag: 'BOX-01',
}, { at: now() }); store = arrivalOne.store;

const evidenceOne = attachEvidence(store, {
  operationId: 'accept-photo-1', intakeId: one.receipt.intakeId,
  attachmentId: 'walkaround-front', filename: 'synthetic-front.jpg', mimeType: 'image/jpeg',
  sizeBytes: 4096, sha256: 'a'.repeat(64),
}, { at: now() }); store = evidenceOne.store;

const arrivalThree = recordArrival(store, {
  operationId: 'accept-arrival-3', intakeId: three.receipt.intakeId,
  vehicleFingerprint: three.receipt.vehicleFingerprint, channel: 'STAFF_CONFIRMATION', keyTag: 'BOX-03',
}, { at: now() }); store = arrivalThree.store;
const diagnosisThree = transition(store, {
  operationId: 'accept-diagnosis-3', intakeId: three.receipt.intakeId,
  toStatus: 'DIAGNOSIS', reason: 'Synthetic staff queue transition only.',
}, { at: now() }); store = diagnosisThree.store;

const arrivalFour = recordArrival(store, {
  operationId: 'accept-arrival-4', intakeId: four.receipt.intakeId,
  vehicleFingerprint: four.receipt.vehicleFingerprint, channel: 'CUSTOMER_TEXT', keyTag: 'BOX-04',
}, { at: now() }); store = arrivalFour.store;
const diagnosisFour = transition(store, {
  operationId: 'accept-diagnosis-4', intakeId: four.receipt.intakeId,
  toStatus: 'DIAGNOSIS', reason: 'Synthetic staff queue transition only.',
}, { at: now() }); store = diagnosisFour.store;
const estimateFour = transition(store, {
  operationId: 'accept-estimate-4', intakeId: four.receipt.intakeId,
  toStatus: 'ESTIMATE_READY', reason: 'Synthetic human-authored estimate state only.',
}, { at: now() }); store = estimateFour.store;

const snapshot = exportSnapshot(store);
assert.equal(snapshot.records.length, 4);
assert.deepEqual(snapshot.queues.ARRIVED, [one.receipt.intakeId]);
assert.deepEqual(snapshot.queues.NEEDS_CLARIFICATION, [two.receipt.intakeId]);
assert.deepEqual(snapshot.queues.DIAGNOSIS, [three.receipt.intakeId]);
assert.deepEqual(snapshot.queues.ESTIMATE_READY, [four.receipt.intakeId]);
assert.equal(snapshot.queues.AWAITING_ARRIVAL.length, 0);
assert.equal(snapshot.records.find((r) => r.intakeId === one.receipt.intakeId).attachments.length, 1);
assert.ok(verifySnapshot(snapshot));
assert.ok(Object.values(snapshot.authority).every((value) => value === false));

const second = exportSnapshot(structuredClone(store));
assert.equal(JSON.stringify(second), JSON.stringify(snapshot));

process.stdout.write(JSON.stringify({
  ok: true,
  syntheticRecords: snapshot.records.length,
  queues: Object.fromEntries(Object.entries(snapshot.queues).map(([k, v]) => [k, v.length])),
  attachmentEvidence: 1,
  sourceReplayDuplicates: 0,
  authorityGranted: false,
  exportSha256: snapshot.exportSha256,
}, null, 2) + '\n');
