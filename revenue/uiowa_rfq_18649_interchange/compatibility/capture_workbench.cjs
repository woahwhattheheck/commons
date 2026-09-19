#!/usr/bin/env node
/* Exercise the checked-in workbench itself; no copied exporter and no network.
 * This is a DOM-contract rehearsal, not a rendered-browser accessibility test.
 */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');

async function main() {
  const [appPath, outDir, reportPath] = process.argv.slice(2);
  if (!appPath || !outDir) throw new Error('usage: node capture_workbench.cjs APP_JS NEW_OUTPUT_DIR [COMPILER_REPORT_JSON]');
  const source = fs.readFileSync(appPath);
  const exports = [];
  class Element {
    constructor() { this.children = []; this.dataset = {}; this.value = ''; this.events = {}; this.textContent = ''; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    addEventListener(name, callback) { this.events[name] = callback; }
    setAttribute() {}
    click() { if (this.events.click) this.events.click(); }
    remove() {}
    get childElementCount() { return this.children.length; }
  }
  const elements = new Map();
  const sandbox = {
    document: { body: new Element(), createElement: () => new Element(),
      getElementById: id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); } },
    Option: function(label, value) { this.text = label; this.value = value; },
    Blob, URLSearchParams, location: { search: '' },
    URL: { createObjectURL: blob => { exports.push(blob); return 'blob:synthetic-local'; }, revokeObjectURL() {} },
    fetch: async () => { throw new Error('NETWORK_DISABLED_IN_REHEARSAL'); }
  };
  vm.createContext(sandbox);
  vm.runInContext(source.toString('utf8'), sandbox, { filename: appPath, timeout: 5000 });
  const report = reportPath ? JSON.parse(fs.readFileSync(reportPath, 'utf8')) : vm.runInContext('syntheticReport()', sandbox);
  sandbox.suppliedReport = report;
  sandbox.testNotes = [
    'SYNTHETIC: café / Δ / 日本語 / e\u0301 / é',
    'SYNTHETIC line one\r\nline two\nthird line\twith tab',
    '=1+1', '+1', '-1', '@example', "'literal apostrophe",
    '2026-09-19T09:15:00-04:00', '0000123', '',
    'SYNTHETIC evidence://long-locator/' + 'segment/'.repeat(45) + 'record#L12-L18',
    'SYNTHETIC quote "comma,pipe|" and slash/tilde~'
  ];
  vm.runInContext(`
    installReport(suppliedReport);
    state.cells.forEach((cell, i) => {
      selectCell(keyFor(cell));
      el.note.value = testNotes[i];
      el.note.events.input();
    });
    el.search.value = 'no-cell-matches-this-query'; renderMatrix();
    exportDraft();
  `, sandbox, { timeout: 5000 });
  const handoffText = await exports[0].text();
  const handoff = JSON.parse(handoffText);
  assert.equal(handoff.cell_notes.length, 12, 'filter must not discard unshown cells');
  handoff.cell_notes.forEach((row, i) => assert.equal(row.analyst_note, sandbox.testNotes[i]));
  assert.ok(Object.values(handoff.authority).every(value => value === false));
  assert.ok(handoff.cell_notes.every(row => !('source_ids' in row)), 'source evidence belongs in the paired report');
  vm.runInContext('installReport(suppliedReport); exportDraft();', sandbox, { timeout: 5000 });
  const reset = JSON.parse(await exports[1].text());
  assert.ok(reset.cell_notes.every(row => row.analyst_note === '' && row.disposition === 'UNREVIEWED'));
  // Parsing failure must invalidate the prior generation, not leave its export active.
  vm.runInContext(`el.candidateFile.files = [{size: 1, text: async () => '{'}];
    el.authorityFile.files = [{size: 2, text: async () => '{}'}];`, sandbox);
  await vm.runInContext('inspectFiles()', sandbox, { timeout: 5000 });
  vm.runInContext('exportDraft()', sandbox);
  assert.equal(exports.length, 2, 'failed replacement must not export the previous generation');
  assert.equal(elements.get('exportBtn').disabled, true);
  const bytes = Buffer.concat([Buffer.from(`blob ${source.length}\0`), source]);
  const receipt = {
    schema: 'uiowa-096-workbench-capture/v1', synthetic_note_inputs: true,
    report_synthetic_label: report.synthetic_demo === true,
    runtime: process.version, execution: 'actual-app-js-with-minimal-dom-no-network',
    source_git_blob_sha1: crypto.createHash('sha1').update(bytes).digest('hex'),
    source_sha256: crypto.createHash('sha256').update(source).digest('hex'),
    report_origin: reportPath ? 'supplied-report-see-operator-provenance' : 'actual-built-in-ui-demo-NOT-compiler-output',
    report_sha256: crypto.createHash('sha256').update(JSON.stringify(report, null, 2) + '\n').digest('hex'),
    handoff_sha256: crypto.createHash('sha256').update(handoffText).digest('hex'),
    checks: ['12-cell-export-despite-empty-filter', '12-note-exact-string-preservation',
      'all-handoff-authorities-literal-false', 'report-required-for-source-evidence',
      'reimport-clears-notes-and-dispositions', 'invalid-replacement-clears-export'],
    result: 'PASS', visual_browser_validation: 'NOT_RUN'
  };
  fs.mkdirSync(outDir); // Refuse overwriting a prior capture directory.
  fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  fs.writeFileSync(path.join(outDir, 'handoff.json'), handoffText);
  fs.writeFileSync(path.join(outDir, 'capture_receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
  console.log(JSON.stringify(receipt, null, 2));
}
main().catch(error => { console.error(error.stack); process.exitCode = 1; });
