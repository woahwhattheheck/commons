import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const here = new URL('./', import.meta.url);
const read = async (name) => readFile(new URL(name, here), 'utf8');

test('mobile UI exposes the promised customer and staff surfaces', async () => {
  const html = await read('index.html');
  for (const token of [
    'name="contactName"', 'name="vin"', 'name="plate"', 'name="symptoms"',
    'name="requestedWork"', 'name="dropoffMode"', 'name="attachments"',
    'id="queue"', 'id="export"', 'width=device-width',
  ]) assert.ok(html.includes(token), `missing UI token ${token}`);
});

test('runtime UI does not inject record fields as HTML', async () => {
  const app = await read('app.mjs');
  for (const forbidden of ['innerHTML', 'outerHTML', 'insertAdjacentHTML', 'document.write', 'eval(']) {
    assert.equal(app.includes(forbidden), false, `forbidden sink ${forbidden}`);
  }
  assert.ok(app.includes('textContent'));
  assert.ok(app.includes('createTextNode'));
});

test('runtime has no outbound network transport', async () => {
  const runtime = (await read('app.mjs')) + (await read('engine.mjs'));
  for (const forbidden of ['fetch(', 'XMLHttpRequest', 'WebSocket', 'EventSource', 'sendBeacon']) {
    assert.equal(runtime.includes(forbidden), false, `unexpected network primitive ${forbidden}`);
  }
});

test('browser attachment path hashes bytes before custody metadata is stored', async () => {
  const app = await read('app.mjs');
  assert.ok(app.includes("crypto.subtle.digest('SHA-256'"));
  assert.ok(app.includes('attachEvidence'));
});

test('commercial manifest remains sent-not-accepted and authority-free', async () => {
  const manifest = JSON.parse(await read('PACKAGE_MANIFEST.json'));
  assert.equal(manifest.commercial_offer_usd, 4000);
  assert.equal(manifest.commercial_offer_status, 'SENT_NOT_ACCEPTED');
  assert.ok(Object.values(manifest.authority).every((value) => value === false));
  assert.equal(manifest.production_integration, false);
  assert.equal(manifest.buyer_data_included, false);
});

test('responsive stylesheet includes narrow and wide breakpoints', async () => {
  const css = await read('styles.css');
  assert.ok(css.includes('@media (min-width: 760px)'));
  assert.ok(css.includes('@media (max-width: 520px)'));
});
