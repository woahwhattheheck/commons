import {
  IntakeError, attachEvidence, emptyStore, exportSnapshot, ingest, recordArrival,
  transition,
} from './engine.mjs';

const STORAGE_KEY = 'dynamic-automotive-dropoff-intake-v1';
const form = document.querySelector('#intake-form');
const result = document.querySelector('#result');
const queueRoot = document.querySelector('#queue');
const exportButton = document.querySelector('#export');
const resetButton = document.querySelector('#reset-demo');

let store = loadStore();
let sourceKey = newSourceKey();
render();

function loadStore() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return emptyStore();
  try {
    const parsed = JSON.parse(raw);
    exportSnapshot(parsed); // structural validation before any UI renders it
    return parsed;
  } catch { return emptyStore(); }
}

function saveStore(next) {
  store = next;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  render();
}

function newSourceKey() {
  const uuid = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `web-${uuid}`;
}

function now() { return new Date().toISOString(); }
function op(prefix) { return `${prefix}-${globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`}`; }

function show(message, kind = 'ok') {
  result.textContent = message;
  result.dataset.kind = kind;
  result.hidden = false;
}

function errMessage(error) {
  return error instanceof IntakeError ? `${error.code}: ${error.message}` : String(error?.message ?? error);
}

function field(name) { return form.elements.namedItem(name); }

function inputPayload() {
  return {
    sourceKey,
    contact: { name: field('contactName').value, method: field('contactMethod').value, value: field('contactValue').value },
    vehicle: {
      vin: field('vin').value, plate: field('plate').value, state: field('state').value,
      year: field('year').value, make: field('make').value, model: field('model').value,
    },
    symptoms: field('symptoms').value,
    requestedWork: field('requestedWork').value.split(',').map((x) => x.trim()).filter(Boolean),
    dropoffMode: field('dropoffMode').value,
    note: field('note').value,
  };
}

async function browserHash(file) {
  const bytes = await file.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    let out = ingest(store, inputPayload(), { at: now() });
    let next = out.store;
    const files = [...field('attachments').files];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const digest = await browserHash(file);
      out = attachEvidence(next, {
        operationId: op('upload'), intakeId: out.receipt.intakeId,
        attachmentId: `web-${i + 1}-${digest.slice(0, 12)}`,
        filename: file.name, mimeType: file.type || 'application/octet-stream',
        sizeBytes: file.size, sha256: digest,
      }, { at: now() });
      next = out.store;
    }
    saveStore(next);
    show(out.receipt.status === 'NEEDS_CLARIFICATION'
      ? `Saved and visibly blocked. Missing: ${out.receipt.missingFields.join(', ')}`
      : `Intake ${out.receipt.intakeId} saved. Keep this receipt with the vehicle drop-off.`);
    sourceKey = newSourceKey();
    form.reset();
  } catch (error) {
    show(errMessage(error), 'error');
  }
});

function button(label, onClick, className = '') {
  const el = document.createElement('button');
  el.type = 'button';
  el.textContent = label;
  if (className) el.className = className;
  el.addEventListener('click', onClick);
  return el;
}

function line(label, value) {
  const p = document.createElement('p');
  const strong = document.createElement('strong');
  strong.textContent = `${label}: `;
  p.append(strong, document.createTextNode(value));
  return p;
}

function renderCard(record) {
  const card = document.createElement('article');
  card.className = 'job-card';
  card.append(line('Intake', record.intakeId));
  card.append(line('Vehicle', `${record.vehicle.year ?? '—'} ${record.vehicle.make ?? '—'} ${record.vehicle.model ?? '—'}`));
  card.append(line('Status', record.status));
  card.append(line('Missing', record.missingFields.length ? record.missingFields.join(', ') : 'none'));
  card.append(line('Evidence', `${record.attachments.length} attachment hash record(s)`));

  const actions = document.createElement('div');
  actions.className = 'actions';
  const run = (fn) => {
    try { const out = fn(); saveStore(out.store); show(`${record.intakeId}: ${out.receipt.status}`); }
    catch (error) { show(errMessage(error), 'error'); }
  };

  if (record.status === 'AWAITING_ARRIVAL') {
    actions.append(button('Confirm arrival', () => {
      const keyTag = record.dropoffMode === 'AFTER_HOURS_KEYBOX' ? prompt('Key-box tag / envelope ID (required)') : null;
      if (record.dropoffMode === 'AFTER_HOURS_KEYBOX' && !keyTag) return;
      run(() => recordArrival(store, {
        operationId: op('arrival'), intakeId: record.intakeId,
        vehicleFingerprint: record.vehicle.fingerprint, channel: 'STAFF_CONFIRMATION', keyTag,
      }, { at: now() }));
    }));
  }
  if (record.status === 'ARRIVED') {
    actions.append(button('Needs clarification', () => run(() => transition(store, {
      operationId: op('hold'), intakeId: record.intakeId, toStatus: 'NEEDS_CLARIFICATION', reason: 'Staff marked clarification required',
    }, { at: now() }))));
    actions.append(button('Start diagnosis queue', () => run(() => transition(store, {
      operationId: op('diagnosis'), intakeId: record.intakeId, toStatus: 'DIAGNOSIS', reason: 'Staff queue move; no diagnosis encoded',
    }, { at: now() }))));
  }
  if (record.status === 'NEEDS_CLARIFICATION' && record.arrival && record.missingFields.length === 0) {
    actions.append(button('Clarification received', () => run(() => transition(store, {
      operationId: op('clarified'), intakeId: record.intakeId, toStatus: 'ARRIVED', reason: 'Staff confirmed clarification received',
    }, { at: now() }))));
  }
  if (record.status === 'DIAGNOSIS') {
    actions.append(button('Needs clarification', () => run(() => transition(store, {
      operationId: op('diag-hold'), intakeId: record.intakeId, toStatus: 'NEEDS_CLARIFICATION', reason: 'Staff marked clarification required',
    }, { at: now() }))));
    actions.append(button('Estimate ready', () => run(() => transition(store, {
      operationId: op('estimate'), intakeId: record.intakeId, toStatus: 'ESTIMATE_READY', reason: 'Human-authored estimate is ready; no approval granted',
    }, { at: now() }))));
  }
  card.append(actions);
  return card;
}

function render() {
  const snapshot = exportSnapshot(store);
  queueRoot.replaceChildren();
  const order = ['NEEDS_CLARIFICATION', 'AWAITING_ARRIVAL', 'ARRIVED', 'DIAGNOSIS', 'ESTIMATE_READY'];
  for (const status of order) {
    const section = document.createElement('section');
    section.className = 'queue-column';
    const h = document.createElement('h3');
    h.textContent = `${status.replaceAll('_', ' ')} · ${snapshot.queues[status].length}`;
    section.append(h);
    for (const intakeId of snapshot.queues[status]) section.append(renderCard(store.records[intakeId]));
    queueRoot.append(section);
  }
}

exportButton.addEventListener('click', () => {
  try {
    const snapshot = exportSnapshot(store);
    const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `dynamic-automotive-intake-${store.revision}.json`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  } catch (error) { show(errMessage(error), 'error'); }
});

resetButton.addEventListener('click', () => {
  if (!confirm('Erase this browser-local demo queue?')) return;
  localStorage.removeItem(STORAGE_KEY);
  store = emptyStore(); sourceKey = newSourceKey(); render(); show('Browser-local demo queue reset.');
});
