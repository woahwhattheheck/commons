"use strict";
// Executes the actual app.js file and its registered import handler. The DOM and
// response are controlled test doubles; this is not rendered-browser acceptance.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function element() {
  return { value: "", disabled: false, textContent: "", files: [], dataset: {},
    children: [], listeners: {},
    addEventListener(name, callback) { this.listeners[name] = callback; },
    replaceChildren(...children) { this.children = children; },
    append(...children) { this.children.push(...children); },
    setAttribute() {}, focus() {}, click() {}, remove() {},
    get childElementCount() { return this.children.length; } };
}
function file(bytes, size) {
  const blob = new Blob([bytes]);
  return { size: size ?? blob.size, arrayBuffer: () => blob.arrayBuffer(), text: () => blob.text() };
}
function makeApp(candidate, authority, options = {}) {
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  };
  const calls = [];
  const context = vm.createContext({
    document: { getElementById: get, createElement: element, body: element() },
    Option: function(label, value) { return { textContent: label, value }; },
    location: { search: "" }, URLSearchParams, TextDecoder, TextEncoder, Blob, URL,
    console,
    fetch: async (url, request) => {
      calls.push({ url, ...request });
      return { ok: false, status: 400, json: async () => ({ error: "test endpoint rejected input" }) };
    }
  });
  const appPath = options.appPath || process.env.WORKBENCH_APP || path.join(__dirname, "app.js");
  // Pending shared handoff helpers are loaded when present, preserving a single
  // test entry point when the adjacent restore/Markdown work is composed.
  for (const helper of ["handoff.js", "draft_import.js"]) {
    const helperPath = path.join(path.dirname(appPath), helper);
    if (fs.existsSync(helperPath)) vm.runInContext(fs.readFileSync(helperPath, "utf8"), context, { filename: helper });
  }
  vm.runInContext(fs.readFileSync(appPath, "utf8"), context, { filename: appPath });
  if (candidate !== null) get("candidateFile").files = [file(candidate, options.candidateSize)];
  if (authority !== null) get("authorityFile").files = [file(authority)];
  return { context, elements, get, calls, async inspect() { await get("inspectBtn").listeners.click(); } };
}
async function transmit(candidate, authority = "{}", options = {}) {
  const app = makeApp(candidate, authority, options);
  await app.inspect();
  return app;
}
function emitted(app) {
  assert.equal(app.calls.length, 1, app.get("error").textContent);
  return app.calls[0].body;
}
const tests = [];
function test(name, fn) { tests.push([name, fn]); }

test("actual handler sends the original whitespace, CRLF and Unicode", async () => {
  const candidate = ' \r\n{ "note" : "caf\u00e9 \u6771\u4eac \ud83d\ude42", "empty":"", "missing": null }\t\n';
  const authority = '\n{ "sources" : [] }\r\n';
  const app = await transmit(candidate, authority);
  assert.equal(emitted(app), `{"candidate":${candidate},"authority":${authority}}`);
});
test("unsafe integers are not rounded by browser transport", async () => {
  const candidate = '{"count":9007199254740993,"negative":-9007199254740993}';
  assert.equal(emitted(await transmit(candidate)), `{"candidate":${candidate},"authority":{}}`);
});
test("number spelling survives without a browser numeric conversion", async () => {
  const candidate = '{"a":-0,"b":1.2300,"c":1e+30,"d":1e400,"e":1e-400}';
  assert.equal(emitted(await transmit(candidate)), `{"candidate":${candidate},"authority":{}}`);
});
for (const [label, candidate, authority] of [
  ["candidate top-level", '{"same":1,"same":2}', '{}'],
  ["nested", '{"a":[{"same":1,"same":2}]}', '{}'],
  ["escaped key", '{"same":1,"s\\u0061me":2}', '{}'],
  ["authority", '{}', '{"sources":[],"sources":[1]}']
]) test(`duplicate ${label} members reach the strict server unchanged`, async () => {
  assert.equal(emitted(await transmit(candidate, authority)), `{"candidate":${candidate},"authority":${authority}}`);
});
test("string escapes, literal replacement characters and key order survive", async () => {
  const candidate = '{"z":"\\u0061","a":"\ufffd","v":"line\\nnext","q":"\\\""}';
  assert.equal(emitted(await transmit(candidate)), `{"candidate":${candidate},"authority":{}}`);
});
for (const [label, bytes] of [
  ["invalid continuation", Buffer.from([123,34,120,34,58,34,0xc3,0x28,34,125])],
  ["truncated sequence", Buffer.from([123,34,120,34,58,34,0xe2,0x82,34,125])],
  ["encoded surrogate", Buffer.from([123,34,120,34,58,34,0xed,0xa0,0x80,34,125])]
]) test(`${label} UTF-8 fails before fetch instead of replacing evidence`, async () => {
  const app = await transmit(bytes);
  assert.equal(app.calls.length, 0);
  assert.match(app.get("error").textContent, /valid UTF-8/);
});
test("UTF-8 BOM is rejected rather than silently stripped", async () => {
  const app = await transmit(Buffer.concat([Buffer.from([0xef,0xbb,0xbf]), Buffer.from('{}')]));
  assert.equal(app.calls.length, 0);
  assert.match(app.get("error").textContent, /valid JSON/);
});
for (const value of ["", "null", "[]", "true", '"object"', "42", '{} ,"authority":{}', '{}{}', '{"x":NaN}']) {
  test(`invalid shape or syntax ${JSON.stringify(value)} cannot alter the envelope`, async () => {
    const app = await transmit(value);
    assert.equal(app.calls.length, 0);
    assert.match(app.get("error").textContent, /JSON/);
    assert.equal(app.get("exportBtn").disabled, true);
    assert.equal(app.get("inspectBtn").disabled, false);
  });
}
test("missing candidate is a visible error without a request", async () => {
  const app = await transmit(null);
  assert.equal(app.calls.length, 0);
  assert.match(app.get("error").textContent, /Candidate file is required/);
});
test("invalid authority is also rejected before fetch", async () => {
  const app = await transmit('{}', 'null');
  assert.equal(app.calls.length, 0);
  assert.match(app.get("error").textContent, /Authority must be a JSON object/);
});
test("one file over the byte cap is rejected", async () => {
  const app = await transmit('{"a":"' + 'x'.repeat(1024*1024) + '"}');
  assert.equal(app.calls.length, 0);
  assert.match(app.get("error").textContent, /1 MiB/);
});
test("decoded bytes are independently bounded even with a wrong size declaration", async () => {
  const app = await transmit('{"a":"' + 'x'.repeat(1024*1024) + '"}', '{}', { candidateSize: 1 });
  assert.equal(app.calls.length, 0);
  assert.match(app.get("error").textContent, /1 MiB/);
});
function paddedObject(bytes) { return '{"x":"' + 'x'.repeat(bytes-8) + '"}'; }
test("two full-size files cannot overflow the server envelope limit", async () => {
  const one = paddedObject(1024*1024);
  const app = await transmit(one, one);
  assert.equal(app.calls.length, 0);
  assert.match(app.get("error").textContent, /Combined.*2 MiB/);
});
test("an exactly full server envelope is accepted by the byte check", async () => {
  const overhead = Buffer.byteLength('{"candidate":,"authority":}');
  const app = await transmit(paddedObject(1024*1024), paddedObject(1024*1024-overhead));
  assert.equal(Buffer.byteLength(emitted(app)), 2*1024*1024);
});
test("multibyte data is bounded in bytes rather than character count", async () => {
  const app = await transmit('{"x":"' + '\u6771'.repeat(350000) + '"}');
  assert.equal(app.calls.length, 0);
  assert.match(app.get("error").textContent, /1 MiB/);
});
test("request contract and cache/origin settings remain unchanged", async () => {
  const app = await transmit('{}');
  emitted(app);
  const request = app.calls[0];
  assert.equal(request.url, '/api/inspect');
  assert.equal(request.method, 'POST');
  assert.equal(request.headers['Content-Type'], 'application/json');
  assert.equal(request.credentials, 'same-origin');
  assert.equal(request.cache, 'no-store');
});
test("a failed replacement clears prior report, notes and export state", async () => {
  const app = makeApp(Buffer.from([0xff]), '{}');
  vm.runInContext('installReport(syntheticReport()); selectCell(keyFor(state.cells[0])); state.notes.set(state.selectedKey, "old note");', app.context);
  assert.equal(app.get('exportBtn').disabled, false);
  await app.inspect();
  assert.equal(vm.runInContext('state.report', app.context), null);
  assert.equal(vm.runInContext('state.notes.size', app.context), 0);
  assert.equal(app.get('exportBtn').disabled, true);
  assert.equal(app.get('inspectBtn').disabled, false);
  assert.equal(app.calls.length, 0);
});

async function main() {
  if (process.argv.includes('--bridge')) {
    const input = JSON.parse(fs.readFileSync(0, 'utf8'));
    const app = await transmit(Buffer.from(input.candidate_b64,'base64'), Buffer.from(input.authority_b64,'base64'));
    process.stdout.write(JSON.stringify({
      body_b64: app.calls.length ? Buffer.from(app.calls[0].body, 'utf8').toString('base64') : null,
      requests: app.calls.length, error: app.get('error').textContent
    }));
    return;
  }
  let failures = 0;
  for (const [name, fn] of tests) {
    try { await fn(); console.log(`PASS ${name}`); }
    catch (err) { failures++; console.error(`FAIL ${name}\n${err.stack}`); }
  }
  console.log(`INPUT_TRANSPORT_NODE tests=${tests.length} passed=${tests.length-failures} failed=${failures}`);
  process.exitCode = failures ? 1 : 0;
}
main().catch(err => { console.error(err); process.exitCode = 1; });
