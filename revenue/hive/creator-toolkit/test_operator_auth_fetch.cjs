'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(process.argv[2] || 'operator_auth.js', 'utf8');

function makeHeaders(seed = {}) {
  const pairs = new Map();
  const add = (key, value) => pairs.set(String(key).toLowerCase(), String(value));
  if (seed && typeof seed.forEach === 'function') seed.forEach((value, key) => add(key, value));
  else if (Array.isArray(seed)) seed.forEach(([key, value]) => add(key, value));
  else Object.entries(seed || {}).forEach(([key, value]) => add(key, value));
  return {
    set: add,
    get(key) { return pairs.get(String(key).toLowerCase()) || null; },
    has(key) { return pairs.has(String(key).toLowerCase()); },
    forEach(fn) { pairs.forEach((value, key) => fn(value, key)); },
  };
}

function loadHarness(key = 'op-secret') {
  const calls = [];
  const storage = new Map([['creator-desk.operator.v1', key]]);
  async function originalFetch(input, init) {
    calls.push({input, init});
    return {status: 200, ok: true, json: async () => ({operator: true})};
  }
  const window = {fetch: originalFetch};
  const context = {
    window,
    location: {origin: 'https://creator.example', href: 'https://creator.example/app'},
    localStorage: {
      getItem(name) { return storage.has(name) ? storage.get(name) : null; },
      setItem(name, value) { storage.set(name, value); },
      removeItem(name) { storage.delete(name); },
    },
    Headers: function Headers(seed) { return makeHeaders(seed); },
    URL,
    document: {
      addEventListener() {},
      querySelectorAll() { return []; },
      getElementById() { return null; },
      createElement() { throw new Error('DOM creation not expected in transport tests'); },
    },
    console,
  };
  vm.createContext(context);
  vm.runInContext(source, context, {filename: 'operator_auth.js'});
  return {fetch: context.window.fetch, calls};
}

function authHeader(call) {
  const headers = call.init && call.init.headers;
  return headers && typeof headers.get === 'function' ? headers.get('authorization') : null;
}

test('same-origin protected relative and absolute requests receive bearer auth', async () => {
  const h = loadHarness();
  await h.fetch('/api/dashboard');
  await h.fetch('https://creator.example/workspace.sqlite3');
  assert.equal(authHeader(h.calls[0]), 'Bearer op-secret');
  assert.equal(authHeader(h.calls[1]), 'Bearer op-secret');
});

test('protocol-relative hostile origin never receives bearer auth', async () => {
  const h = loadHarness();
  await h.fetch('//attacker.example/api/dashboard');
  assert.equal(authHeader(h.calls[0]), null);
});

test('absolute hostile origin never receives bearer auth', async () => {
  const h = loadHarness();
  await h.fetch('https://attacker.example/api/dashboard', {headers: {'X-Caller': 'kept'}});
  assert.equal(authHeader(h.calls[0]), null);
  assert.equal(h.calls[0].init.headers['X-Caller'], 'kept');
});

test('same-origin public GET does not receive operator bearer auth', async () => {
  const h = loadHarness();
  await h.fetch('/api/catalog', {headers: {'X-Public': 'yes'}});
  assert.equal(authHeader(h.calls[0]), null);
  assert.equal(h.calls[0].init.headers['X-Public'], 'yes');
});

test('Request-like same-origin protected input keeps inherited headers', async () => {
  const h = loadHarness();
  const request = {url: 'https://creator.example/api/dashboard', headers: makeHeaders({'X-Caller': 'kept'})};
  await h.fetch(request);
  assert.equal(authHeader(h.calls[0]), 'Bearer op-secret');
  assert.equal(h.calls[0].init.headers.get('x-caller'), 'kept');
});

test('explicit init headers remain authoritative while auth is added', async () => {
  const h = loadHarness();
  const request = {url: 'https://creator.example/api/dashboard', headers: makeHeaders({'X-Request': 'old'})};
  await h.fetch(request, {headers: {'X-Init': 'new'}});
  assert.equal(authHeader(h.calls[0]), 'Bearer op-secret');
  assert.equal(h.calls[0].init.headers.get('x-init'), 'new');
  assert.equal(h.calls[0].init.headers.get('x-request'), null);
});
