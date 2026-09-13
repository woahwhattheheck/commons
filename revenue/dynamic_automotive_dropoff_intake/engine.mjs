export const SCHEMA_VERSION = 'dynamic-automotive-dropoff-intake/v1';
export const STATUSES = Object.freeze([
  'NEEDS_CLARIFICATION',
  'AWAITING_ARRIVAL',
  'ARRIVED',
  'DIAGNOSIS',
  'ESTIMATE_READY',
]);
export const AUTHORITY = Object.freeze({
  diagnoseVehicle: false,
  authorizeRepair: false,
  approveEstimate: false,
  initiateCharge: false,
  contactCustomer: false,
});

const DROP_MODES = new Set(['AFTER_HOURS_KEYBOX', 'BUSINESS_HOURS_FRONT_DESK']);
const ARRIVAL_CHANNELS = new Set(['DOOR_QR', 'CUSTOMER_TEXT', 'STAFF_CONFIRMATION']);
const CONTACT_METHODS = new Set(['PHONE', 'EMAIL']);
const TRANSITIONS = new Map([
  ['ARRIVED', new Set(['NEEDS_CLARIFICATION', 'DIAGNOSIS'])],
  ['NEEDS_CLARIFICATION', new Set(['ARRIVED'])],
  ['DIAGNOSIS', new Set(['NEEDS_CLARIFICATION', 'ESTIMATE_READY'])],
]);
const MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024;
const MAX_ATTACHMENTS = 12;
const SHA256 = /^[0-9a-f]{64}$/;
const VIN = /^[A-HJ-NPR-Z0-9]{17}$/;
const STATE = /^[A-Z]{2}$/;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE = /^\+?[0-9][0-9() .-]{6,24}$/;

export class IntakeError extends Error {
  constructor(code, message = code) {
    super(message);
    this.name = 'IntakeError';
    this.code = code;
  }
}

function fail(code, message = code) {
  throw new IntakeError(code, message);
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype;
}

function exactKeys(value, allowed, label) {
  if (!isPlainObject(value)) fail('INVALID_OBJECT', `${label} must be an object`);
  const extra = Object.keys(value).filter((key) => !allowed.has(key));
  if (extra.length) fail('UNKNOWN_FIELD', `${label} contains unknown fields: ${extra.sort().join(',')}`);
}

function text(value, label, max = 200) {
  if (typeof value !== 'string') fail('INVALID_TEXT', `${label} must be text`);
  const out = value.trim().replace(/\s+/g, ' ');
  if (!out || out.length > max) fail('INVALID_TEXT', `${label} must be 1..${max} characters`);
  return out;
}

function optionalText(value, label, max = 200) {
  if (value === null || value === undefined || value === '') return null;
  return text(value, label, max);
}

function integer(value, label, min, max) {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < min || value > max) {
    fail('INVALID_INTEGER', `${label} must be an integer in [${min}, ${max}]`);
  }
  return value;
}

function timestamp(value, label) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value)) {
    fail('INVALID_TIMESTAMP', `${label} must be an explicit UTC ISO timestamp`);
  }
  const ms = Date.parse(value);
  if (!Number.isFinite(ms) || new Date(ms).toISOString().replace('.000Z', 'Z') !== value.replace('.000Z', 'Z')) {
    fail('INVALID_TIMESTAMP', `${label} is not a valid UTC timestamp`);
  }
  return value;
}

function deepClone(value) {
  return structuredClone(value);
}

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (isPlainObject(value)) {
    const out = {};
    for (const key of Object.keys(value).sort()) out[key] = canonicalize(value[key]);
    return out;
  }
  return value;
}

export function canonicalJson(value) {
  return JSON.stringify(canonicalize(value));
}

export function sha256(value) {
  // Dependency-free SHA-256 keeps the exact engine usable in both Node tests and a
  // static browser page.  The algorithm operates on UTF-8 bytes and returns the
  // conventional lowercase 64-hex digest.
  const input = typeof value === 'string' ? value : canonicalJson(value);
  const bytes = new TextEncoder().encode(input);
  const bitLength = bytes.length * 8;
  const paddedLength = Math.ceil((bytes.length + 9) / 64) * 64;
  const padded = new Uint8Array(paddedLength);
  padded.set(bytes);
  padded[bytes.length] = 0x80;
  const view = new DataView(padded.buffer);
  const high = Math.floor(bitLength / 0x100000000);
  const low = bitLength >>> 0;
  view.setUint32(paddedLength - 8, high, false);
  view.setUint32(paddedLength - 4, low, false);

  const K = [
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2,
  ];
  const rotr = (x, n) => (x >>> n) | (x << (32 - n));
  let h0=0x6a09e667,h1=0xbb67ae85,h2=0x3c6ef372,h3=0xa54ff53a,h4=0x510e527f,h5=0x9b05688c,h6=0x1f83d9ab,h7=0x5be0cd19;
  const w = new Uint32Array(64);
  for (let offset = 0; offset < paddedLength; offset += 64) {
    for (let i = 0; i < 16; i++) w[i] = view.getUint32(offset + i * 4, false);
    for (let i = 16; i < 64; i++) {
      const s0 = rotr(w[i-15],7) ^ rotr(w[i-15],18) ^ (w[i-15] >>> 3);
      const s1 = rotr(w[i-2],17) ^ rotr(w[i-2],19) ^ (w[i-2] >>> 10);
      w[i] = (w[i-16] + s0 + w[i-7] + s1) >>> 0;
    }
    let a=h0,b=h1,c=h2,d=h3,e=h4,f=h5,g=h6,h=h7;
    for (let i = 0; i < 64; i++) {
      const S1 = rotr(e,6) ^ rotr(e,11) ^ rotr(e,25);
      const ch = (e & f) ^ (~e & g);
      const t1 = (h + S1 + ch + K[i] + w[i]) >>> 0;
      const S0 = rotr(a,2) ^ rotr(a,13) ^ rotr(a,22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const t2 = (S0 + maj) >>> 0;
      h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;
    }
    h0=(h0+a)>>>0;h1=(h1+b)>>>0;h2=(h2+c)>>>0;h3=(h3+d)>>>0;
    h4=(h4+e)>>>0;h5=(h5+f)>>>0;h6=(h6+g)>>>0;h7=(h7+h)>>>0;
  }
  return [h0,h1,h2,h3,h4,h5,h6,h7].map((n)=>n.toString(16).padStart(8,'0')).join('');
}

function normalizeContact(raw = {}) {
  exactKeys(raw, new Set(['name', 'method', 'value']), 'contact');
  const name = raw.name === undefined || raw.name === null || raw.name === '' ? null : text(raw.name, 'contact.name', 120);
  const method = raw.method === undefined || raw.method === null || raw.method === '' ? null : text(raw.method, 'contact.method', 16).toUpperCase();
  let value = raw.value === undefined || raw.value === null || raw.value === '' ? null : text(raw.value, 'contact.value', 160);
  if (method !== null && !CONTACT_METHODS.has(method)) fail('INVALID_CONTACT_METHOD');
  if (method === 'EMAIL' && value !== null) {
    value = value.toLowerCase();
    if (!EMAIL.test(value)) fail('INVALID_CONTACT_VALUE', 'contact.value is not a valid email');
  }
  if (method === 'PHONE' && value !== null && !PHONE.test(value)) fail('INVALID_CONTACT_VALUE', 'contact.value is not a valid phone');
  return { name, method, value };
}

function normalizeVehicle(raw = {}) {
  exactKeys(raw, new Set(['vin', 'plate', 'state', 'year', 'make', 'model']), 'vehicle');
  const vin = raw.vin === undefined || raw.vin === null || raw.vin === '' ? null : text(raw.vin, 'vehicle.vin', 32).toUpperCase().replace(/[\s-]/g, '');
  const plate = raw.plate === undefined || raw.plate === null || raw.plate === '' ? null : text(raw.plate, 'vehicle.plate', 16).toUpperCase();
  const state = raw.state === undefined || raw.state === null || raw.state === '' ? null : text(raw.state, 'vehicle.state', 2).toUpperCase();
  const year = raw.year === undefined || raw.year === '' || raw.year === null ? null : integer(Number(raw.year), 'vehicle.year', 1886, 2100);
  const make = raw.make === undefined || raw.make === null || raw.make === '' ? null : text(raw.make, 'vehicle.make', 80);
  const model = raw.model === undefined || raw.model === null || raw.model === '' ? null : text(raw.model, 'vehicle.model', 80);
  if (vin !== null && !VIN.test(vin)) fail('INVALID_VIN');
  if (state !== null && !STATE.test(state)) fail('INVALID_STATE');
  if ((plate === null) !== (state === null)) fail('PLATE_STATE_PAIR_REQUIRED');
  const identity = vin !== null ? `VIN:${vin}` : (plate !== null ? `PLATE:${state}:${plate}` : null);
  const fingerprint = identity === null ? null : sha256(identity);
  return { vin, plate, state, year, make, model, fingerprint };
}

function normalizeRequestedWork(value) {
  if (value === undefined || value === null) return [];
  if (!Array.isArray(value) || value.length > 12) fail('INVALID_REQUESTED_WORK');
  const out = value.map((item, i) => text(item, `requestedWork[${i}]`, 120));
  if (new Set(out.map((x) => x.toLowerCase())).size !== out.length) fail('DUPLICATE_REQUESTED_WORK');
  return out;
}

function normalizeIntake(raw) {
  exactKeys(raw, new Set(['sourceKey', 'contact', 'vehicle', 'symptoms', 'requestedWork', 'dropoffMode', 'note']), 'intake');
  const sourceKey = text(raw.sourceKey, 'sourceKey', 160);
  const contact = normalizeContact(raw.contact ?? {});
  const vehicle = normalizeVehicle(raw.vehicle ?? {});
  const symptoms = raw.symptoms === undefined || raw.symptoms === null || raw.symptoms === '' ? null : text(raw.symptoms, 'symptoms', 2000);
  const requestedWork = normalizeRequestedWork(raw.requestedWork);
  const dropoffMode = raw.dropoffMode === undefined || raw.dropoffMode === null || raw.dropoffMode === '' ? null : text(raw.dropoffMode, 'dropoffMode', 40).toUpperCase();
  if (dropoffMode !== null && !DROP_MODES.has(dropoffMode)) fail('INVALID_DROPOFF_MODE');
  const note = optionalText(raw.note, 'note', 1000);
  return { sourceKey, contact, vehicle, symptoms, requestedWork, dropoffMode, note };
}

function missingFields(normalized) {
  const missing = [];
  if (!normalized.contact.name) missing.push('contact.name');
  if (!normalized.contact.method) missing.push('contact.method');
  if (!normalized.contact.value) missing.push('contact.value');
  if (!normalized.vehicle.fingerprint) missing.push('vehicle.identity');
  if (!normalized.vehicle.year) missing.push('vehicle.year');
  if (!normalized.vehicle.make) missing.push('vehicle.make');
  if (!normalized.vehicle.model) missing.push('vehicle.model');
  if (!normalized.symptoms) missing.push('symptoms');
  if (normalized.requestedWork.length === 0) missing.push('requestedWork');
  if (!normalized.dropoffMode) missing.push('dropoffMode');
  return missing;
}

export function emptyStore() {
  return {
    schemaVersion: SCHEMA_VERSION,
    revision: 0,
    sequence: 0,
    records: {},
    sourceIndex: {},
    operationIndex: {},
  };
}

function ensureStore(raw) {
  if (!isPlainObject(raw)) fail('INVALID_STORE');
  exactKeys(raw, new Set(['schemaVersion', 'revision', 'sequence', 'records', 'sourceIndex', 'operationIndex']), 'store');
  if (raw.schemaVersion !== SCHEMA_VERSION) fail('INVALID_STORE_SCHEMA');
  integer(raw.revision, 'store.revision', 0, Number.MAX_SAFE_INTEGER);
  integer(raw.sequence, 'store.sequence', 0, Number.MAX_SAFE_INTEGER);
  if (!isPlainObject(raw.records) || !isPlainObject(raw.sourceIndex) || !isPlainObject(raw.operationIndex)) fail('INVALID_STORE');
  for (const [sourceKey, intakeId] of Object.entries(raw.sourceIndex)) {
    if (typeof sourceKey !== 'string' || typeof intakeId !== 'string' || !raw.records[intakeId] || raw.records[intakeId].sourceKey !== sourceKey) fail('INVALID_STORE_INDEX');
  }
  for (const [intakeId, record] of Object.entries(raw.records)) {
    if (!isPlainObject(record) || record.intakeId !== intakeId || raw.sourceIndex[record.sourceKey] !== intakeId) fail('INVALID_STORE_INDEX');
    if (!STATUSES.includes(record.status) || !Array.isArray(record.history) || !Array.isArray(record.attachments)) fail('INVALID_STORE_RECORD');
    if (record.vehicle?.fingerprint !== null && record.vehicle?.fingerprint !== undefined && !SHA256.test(record.vehicle.fingerprint)) fail('INVALID_STORE_RECORD');
  }
  return raw;
}

function nextEvent(store, intakeId, type, at, detail = {}) {
  store.sequence += 1;
  const event = { seq: store.sequence, at: timestamp(at, 'event.at'), type, ...detail };
  store.records[intakeId].history.push(event);
  store.records[intakeId].updatedAt = at;
  return event;
}

function registerOperation(store, operationId, semantic) {
  operationId = text(operationId, 'operationId', 160);
  const digest = sha256(semantic);
  const existing = store.operationIndex[operationId];
  if (existing) {
    if (existing.digest !== digest) fail('IDEMPOTENCY_CONFLICT', `operationId ${operationId} was reused with changed content`);
    return { replay: true, prior: existing };
  }
  store.operationIndex[operationId] = { digest };
  return { replay: false, digest };
}

function storeOperationResult(store, operationId, intakeId, eventSeq) {
  store.operationIndex[operationId] = { ...store.operationIndex[operationId], intakeId, eventSeq };
}

function intakeReceipt(store, record, replay = false) {
  const publicCore = {
    schemaVersion: SCHEMA_VERSION,
    intakeId: record.intakeId,
    sourceKey: record.sourceKey,
    status: record.status,
    vehicleFingerprint: record.vehicle.fingerprint,
    missingFields: record.missingFields,
    attachmentCount: record.attachments.length,
    arrivedAt: record.arrival?.at ?? null,
    revision: store.revision,
    replay,
    authority: AUTHORITY,
  };
  return { ...publicCore, receiptSha256: sha256(publicCore) };
}

export function ingest(rawStore, rawInput, { at }) {
  ensureStore(rawStore);
  const normalized = normalizeIntake(rawInput);
  const digest = sha256(normalized);
  const existingId = rawStore.sourceIndex[normalized.sourceKey];
  if (existingId) {
    const existing = rawStore.records[existingId];
    if (existing.sourceDigest !== digest) fail('IDEMPOTENCY_CONFLICT', 'sourceKey reused with changed intake');
    return { store: deepClone(rawStore), receipt: intakeReceipt(rawStore, existing, true) };
  }

  const store = deepClone(rawStore);
  const intakeId = `INT-${sha256(`dynamic-auto:${normalized.sourceKey}`).slice(0, 20).toUpperCase()}`;
  if (store.records[intakeId]) fail('INTAKE_ID_COLLISION');
  const missing = missingFields(normalized);
  const record = {
    intakeId,
    sourceKey: normalized.sourceKey,
    sourceDigest: digest,
    currentInputDigest: digest,
    contact: normalized.contact,
    vehicle: normalized.vehicle,
    symptoms: normalized.symptoms,
    requestedWork: normalized.requestedWork,
    dropoffMode: normalized.dropoffMode,
    note: normalized.note,
    missingFields: missing,
    status: missing.length ? 'NEEDS_CLARIFICATION' : 'AWAITING_ARRIVAL',
    arrival: null,
    attachments: [],
    history: [],
    createdAt: timestamp(at, 'at'),
    updatedAt: at,
  };
  store.records[intakeId] = record;
  store.sourceIndex[normalized.sourceKey] = intakeId;
  nextEvent(store, intakeId, 'INTAKE_CREATED', at, { status: record.status, missingFields: [...missing] });
  store.revision += 1;
  return { store, receipt: intakeReceipt(store, record, false) };
}

function normalizedRecordInput(record, patch) {
  exactKeys(patch, new Set(['contact', 'vehicle', 'symptoms', 'requestedWork', 'dropoffMode', 'note']), 'clarification.patch');
  const base = {
    sourceKey: record.sourceKey,
    contact: record.contact,
    vehicle: {
      vin: record.vehicle.vin,
      plate: record.vehicle.plate,
      state: record.vehicle.state,
      year: record.vehicle.year,
      make: record.vehicle.make,
      model: record.vehicle.model,
    },
    symptoms: record.symptoms,
    requestedWork: record.requestedWork,
    dropoffMode: record.dropoffMode,
    note: record.note,
  };
  for (const [key, value] of Object.entries(patch)) base[key] = value;
  return normalizeIntake(base);
}

export function clarify(rawStore, { operationId, intakeId, patch }, { at }) {
  ensureStore(rawStore);
  const record = rawStore.records[intakeId];
  if (!record) fail('UNKNOWN_INTAKE');
  const semantic = { type: 'CLARIFY', intakeId, patch };
  const preview = deepClone(rawStore);
  const op = registerOperation(preview, operationId, semantic);
  if (op.replay) return { store: preview, receipt: intakeReceipt(preview, preview.records[intakeId], true) };
  if (!['NEEDS_CLARIFICATION', 'AWAITING_ARRIVAL', 'ARRIVED', 'DIAGNOSIS'].includes(record.status)) fail('INVALID_STATE');

  const normalized = normalizedRecordInput(record, patch);
  if (record.arrival && normalized.vehicle.fingerprint !== record.vehicle.fingerprint) fail('ARRIVED_VEHICLE_IDENTITY_IMMUTABLE');
  const store = preview;
  const next = store.records[intakeId];
  next.contact = normalized.contact;
  next.vehicle = normalized.vehicle;
  next.symptoms = normalized.symptoms;
  next.requestedWork = normalized.requestedWork;
  next.dropoffMode = normalized.dropoffMode;
  next.note = normalized.note;
  next.missingFields = missingFields(normalized);
  if (next.missingFields.length) {
    next.status = 'NEEDS_CLARIFICATION';
  } else if (next.arrival) {
    next.status = record.status === 'DIAGNOSIS' ? 'DIAGNOSIS' : 'ARRIVED';
  } else {
    next.status = 'AWAITING_ARRIVAL';
  }
  next.currentInputDigest = sha256(normalized);
  const event = nextEvent(store, intakeId, 'CLARIFICATION_RECORDED', at, { status: next.status, missingFields: [...next.missingFields] });
  storeOperationResult(store, operationId, intakeId, event.seq);
  store.revision += 1;
  return { store, receipt: intakeReceipt(store, next, false) };
}

export function attachEvidence(rawStore, raw, { at }) {
  ensureStore(rawStore);
  exactKeys(raw, new Set(['operationId', 'intakeId', 'attachmentId', 'filename', 'mimeType', 'sizeBytes', 'sha256']), 'attachment');
  const operationId = text(raw.operationId, 'operationId', 160);
  const intakeId = text(raw.intakeId, 'intakeId', 80);
  const attachmentId = text(raw.attachmentId, 'attachmentId', 120);
  const filename = text(raw.filename, 'filename', 180);
  const mimeType = text(raw.mimeType, 'mimeType', 120).toLowerCase();
  const sizeBytes = integer(raw.sizeBytes, 'sizeBytes', 1, MAX_ATTACHMENT_BYTES);
  const digest = text(raw.sha256, 'sha256', 64).toLowerCase();
  if (!SHA256.test(digest)) fail('INVALID_ATTACHMENT_HASH');
  const semantic = { type: 'ATTACHMENT', intakeId, attachmentId, filename, mimeType, sizeBytes, sha256: digest };
  const store = deepClone(rawStore);
  const op = registerOperation(store, operationId, semantic);
  if (op.replay) return { store, receipt: intakeReceipt(store, store.records[intakeId], true) };
  const record = store.records[intakeId];
  if (!record) fail('UNKNOWN_INTAKE');
  if (record.attachments.length >= MAX_ATTACHMENTS) fail('ATTACHMENT_LIMIT');
  const existing = record.attachments.find((item) => item.attachmentId === attachmentId);
  if (existing) fail('ATTACHMENT_ID_CONFLICT');
  record.attachments.push({ attachmentId, filename, mimeType, sizeBytes, sha256: digest, attachedAt: timestamp(at, 'at') });
  record.attachments.sort((a, b) => a.attachmentId.localeCompare(b.attachmentId));
  const event = nextEvent(store, intakeId, 'ATTACHMENT_BOUND', at, { attachmentId, sha256: digest });
  storeOperationResult(store, operationId, intakeId, event.seq);
  store.revision += 1;
  return { store, receipt: intakeReceipt(store, record, false) };
}

export function recordArrival(rawStore, raw, { at }) {
  ensureStore(rawStore);
  exactKeys(raw, new Set(['operationId', 'intakeId', 'vehicleFingerprint', 'channel', 'keyTag']), 'arrival');
  const operationId = text(raw.operationId, 'operationId', 160);
  const intakeId = text(raw.intakeId, 'intakeId', 80);
  const vehicleFingerprint = text(raw.vehicleFingerprint, 'vehicleFingerprint', 64).toLowerCase();
  if (!SHA256.test(vehicleFingerprint)) fail('INVALID_VEHICLE_FINGERPRINT');
  const channel = text(raw.channel, 'channel', 40).toUpperCase();
  if (!ARRIVAL_CHANNELS.has(channel)) fail('INVALID_ARRIVAL_CHANNEL');
  const keyTag = optionalText(raw.keyTag, 'keyTag', 80);
  const semantic = { type: 'ARRIVAL', intakeId, vehicleFingerprint, channel, keyTag };
  const store = deepClone(rawStore);
  const op = registerOperation(store, operationId, semantic);
  if (op.replay) return { store, receipt: intakeReceipt(store, store.records[intakeId], true) };
  const record = store.records[intakeId];
  if (!record) fail('UNKNOWN_INTAKE');
  if (record.arrival) fail('ARRIVAL_ALREADY_RECORDED');
  if (record.missingFields.length) fail('INTAKE_BLOCKED', `missing: ${record.missingFields.join(',')}`);
  if (!record.vehicle.fingerprint || record.vehicle.fingerprint !== vehicleFingerprint) fail('VEHICLE_MISMATCH');
  if (record.dropoffMode === 'AFTER_HOURS_KEYBOX' && !keyTag) fail('KEY_TAG_REQUIRED');
  record.arrival = { at: timestamp(at, 'at'), channel, keyTag, vehicleFingerprint };
  record.status = 'ARRIVED';
  const event = nextEvent(store, intakeId, 'ARRIVAL_BOUND', at, { channel, keyTag, vehicleFingerprint });
  storeOperationResult(store, operationId, intakeId, event.seq);
  store.revision += 1;
  return { store, receipt: intakeReceipt(store, record, false) };
}

export function transition(rawStore, raw, { at }) {
  ensureStore(rawStore);
  exactKeys(raw, new Set(['operationId', 'intakeId', 'toStatus', 'reason']), 'transition');
  const operationId = text(raw.operationId, 'operationId', 160);
  const intakeId = text(raw.intakeId, 'intakeId', 80);
  const toStatus = text(raw.toStatus, 'toStatus', 40).toUpperCase();
  if (!STATUSES.includes(toStatus)) fail('INVALID_STATUS');
  const reason = optionalText(raw.reason, 'reason', 500);
  const semantic = { type: 'TRANSITION', intakeId, toStatus, reason };
  const store = deepClone(rawStore);
  const op = registerOperation(store, operationId, semantic);
  if (op.replay) return { store, receipt: intakeReceipt(store, store.records[intakeId], true) };
  const record = store.records[intakeId];
  if (!record) fail('UNKNOWN_INTAKE');
  const allowed = TRANSITIONS.get(record.status);
  if (!allowed || !allowed.has(toStatus)) fail('INVALID_TRANSITION', `${record.status} -> ${toStatus} not allowed`);
  if (toStatus !== 'NEEDS_CLARIFICATION' && record.missingFields.length) fail('INTAKE_BLOCKED');
  if (['ARRIVED', 'DIAGNOSIS', 'ESTIMATE_READY'].includes(toStatus) && !record.arrival) fail('ARRIVAL_REQUIRED');
  record.status = toStatus;
  const event = nextEvent(store, intakeId, 'QUEUE_TRANSITION', at, { fromStatus: rawStore.records[intakeId].status, toStatus, reason });
  storeOperationResult(store, operationId, intakeId, event.seq);
  store.revision += 1;
  return { store, receipt: intakeReceipt(store, record, false) };
}

export function exportSnapshot(rawStore) {
  ensureStore(rawStore);
  const queues = Object.fromEntries(STATUSES.map((status) => [status, []]));
  const records = [];
  for (const intakeId of Object.keys(rawStore.records).sort()) {
    const record = deepClone(rawStore.records[intakeId]);
    queues[record.status].push(intakeId);
    records.push(record);
  }
  const core = {
    schemaVersion: SCHEMA_VERSION,
    storeRevision: rawStore.revision,
    storeSequence: rawStore.sequence,
    generatedFromStateSha256: sha256({
      schemaVersion: rawStore.schemaVersion,
      revision: rawStore.revision,
      sequence: rawStore.sequence,
      records: rawStore.records,
      sourceIndex: rawStore.sourceIndex,
      operationIndex: rawStore.operationIndex,
    }),
    authority: AUTHORITY,
    queues,
    records,
  };
  return { ...core, exportSha256: sha256(core) };
}

export function verifySnapshot(snapshot) {
  if (!isPlainObject(snapshot) || typeof snapshot.exportSha256 !== 'string' || !SHA256.test(snapshot.exportSha256)) return false;
  const core = deepClone(snapshot);
  const claimed = core.exportSha256;
  delete core.exportSha256;
  return sha256(core) === claimed && canonicalJson(core.authority) === canonicalJson(AUTHORITY);
}
