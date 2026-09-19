"use strict";

// Executes the actual app and handoff scripts with a small DOM/event adapter.
// This is a dependency-free JavaScript state/interaction test, not a browser,
// layout, accessibility, HTTP-server or browser-download acceptance claim.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { execFileSync } = require("node:child_process");

const ROOT = __dirname;
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const handoffScript = fs.readFileSync(path.join(ROOT, "handoff.js"), "utf8");
const importerScript = fs.readFileSync(path.join(ROOT, "handoff_import.js"), "utf8");
const appScript = fs.readFileSync(path.join(ROOT, "app.js"), "utf8");

// Both generations come from the real checked-in CompilerAdapter and synthetic
// evidence fixtures. The second has a valid, distinct authority generation.
const fixture = JSON.parse(execFileSync(process.env.PYTHON || "python3", ["-c", `
import copy, json
from pathlib import Path
import server
p = Path("../uiowa_rfq_18649_workshare/fixtures")
candidate = json.loads((p / "synthetic_packet.json").read_text())
authority = json.loads((p / "synthetic_authority.json").read_text())
adapter = server.CompilerAdapter()
report = adapter.inspect(candidate, authority)
candidate2, authority2 = copy.deepcopy(candidate), copy.deepcopy(authority)
candidate2["authority_generation"] = "node-app-followup-generation"
authority2["generation"] = candidate2["authority_generation"]
for source in authority2["sources"]:
    source["authority_generation"] = authority2["generation"]
report2 = adapter.inspect(candidate2, authority2)
print(json.dumps({"candidate":candidate,"authority":authority,"report":report,"report2":report2}))
`], { cwd: ROOT, encoding: "utf8", maxBuffer: 4 * 1024 * 1024 }));

function deferred() {
  let resolve;
  const promise = new Promise(yes => { resolve = yes; });
  return { promise, resolve };
}

function jsonFile(value) {
  const contents = JSON.stringify(value);
  return { size: Buffer.byteLength(contents), text: async () => contents, arrayBuffer: async () => new TextEncoder().encode(contents).buffer };
}

function delayedFile(value) {
  const wait = deferred();
  const bytes = new TextEncoder().encode(JSON.stringify(value));
  return { file: { size: bytes.byteLength, arrayBuffer: () => wait.promise }, finish: () => wait.resolve(bytes.buffer) };
}

function response(report) { return { ok: true, status: 200, json: async () => ({ report }) }; }

function harness() {
  const downloads = [];
  const objectUrls = new Map();
  const requests = [];
  let nextObjectUrl = 0;
  let fetchHandler = () => Promise.resolve(response(fixture.report));

  class Element {
    constructor(tagName, id = "") {
      this.tagName = tagName.toLowerCase(); this.id = id;
      this.nodeType = 1; this.className = "";
      this.children = []; this.parent = null; this.dataset = {}; this.attributes = {};
      this.listeners = new Map(); this.value = ""; this.textContent = "";
      this.disabled = false; this.files = [];
    }
    get childElementCount() { return this.children.filter(child => child.nodeType === 1).length; }
    append(...children) { for (const child of children) { child.parent = this; this.children.push(child); } }
    replaceChildren(...children) {
      if (this.children.some(child => child === document.activeElement || child.contains?.(document.activeElement))) document.activeElement = document.body;
      this.children.forEach(child => { child.parent = null; });
      this.children = []; this.append(...children);
      if (this.tagName === "select") this.value = children[0]?.value || "";
    }
    contains(node) { return this === node || this.children.some(child => child === node || child.contains?.(node)); }
    querySelectorAll(selector) {
      if (!/^\.[\w-]+$/.test(selector)) throw new Error(`Unsupported fixture selector: ${selector}`);
      const matches = [];
      for (const child of this.children) {
        if (child.nodeType !== 1) continue;
        if (child.className.split(/\s+/).includes(selector.slice(1))) matches.push(child);
        matches.push(...child.querySelectorAll(selector));
      }
      return matches;
    }
    focus() { if (!this.disabled) document.activeElement = this; }
    setAttribute(name, value) { this.attributes[name] = value; }
    addEventListener(type, listener) {
      if (!this.listeners.has(type)) this.listeners.set(type, []);
      this.listeners.get(type).push(listener);
    }
    async emit(type) {
      for (const listener of this.listeners.get(type) || []) await listener({ target: this });
    }
    click() {
      if (this.disabled) return Promise.resolve();
      if (this.tagName === "a") downloads.push({ filename: this.download, blob: objectUrls.get(this.href) });
      return this.emit("click");
    }
    remove() {
      if (this.parent) this.parent.children = this.parent.children.filter(child => child !== this);
      this.parent = null;
    }
  }

  const elements = new Map([...html.matchAll(/<([a-z][a-z0-9-]*)\b[^>]*\bid="([^"]+)"[^>]*>/g)]
    .map(([, tag, id]) => [id, new Element(tag, id)]));
  const body = new Element("body");
  const document = {
    getElementById: id => elements.get(id) || null,
    createElement: tag => new Element(tag),
    createTextNode: value => ({ nodeType: 3, textContent: String(value), parent: null }),
    body, activeElement: body
  };
  const sandbox = {
    document,
    Option: function (label, value) { const option = new Element("option"); option.textContent = label; option.value = value; return option; },
    Blob, TextDecoder, TextEncoder, URLSearchParams, location: { search: "" },
    URL: {
      createObjectURL(blob) { const url = `blob:node-test-${++nextObjectUrl}`; objectUrls.set(url, blob); return url; },
      revokeObjectURL(url) { objectUrls.delete(url); }
    },
    setTimeout,
    fetch: (url, options) => { requests.push({ url, options }); return fetchHandler(url, options); }
  };
  sandbox.window = sandbox;
  const context = vm.createContext(sandbox);
  vm.runInContext(handoffScript, context, { filename: "handoff.js" });
  vm.runInContext(importerScript, context, { filename: "handoff_import.js" });
  vm.runInContext(appScript, context, { filename: "app.js" });
  const evaluate = expression => vm.runInContext(expression, context);

  return {
    el: id => elements.get(id), downloads, requests, evaluate,
    setFetch(handler) { fetchHandler = handler; },
    setReport(report) { sandbox.testReport = report; evaluate("installReport(testReport)"); delete sandbox.testReport; },
    inputs() {
      elements.get("candidateFile").files = [jsonFile(fixture.candidate)];
      elements.get("authorityFile").files = [jsonFile(fixture.authority)];
    },
    inspect() { this.inputs(); return elements.get("inspectBtn").click(); },
    async select(key = "ESS|software") {
      const cell = elements.get("matrix").children.find(button => button.dataset.key === key);
      assert.ok(cell, `Expected rendered cell ${key}`); await cell.click();
    },
    async note(value) { elements.get("note").value = value; await elements.get("note").emit("input"); },
    async disposition(value) { elements.get("disposition").value = value; await elements.get("disposition").emit("change"); },
    snapshot() { return JSON.parse(evaluate("JSON.stringify({receipt:state.report?.receipt_sha256 || null,notes:[...state.notes],dispositions:[...state.dispositions]})")); },
    async draft() {
      await elements.get("exportBtn").click();
      const download = downloads.at(-1);
      assert.ok(download?.filename.endsWith(".json"));
      assert.ok(download.blob instanceof Blob);
      return JSON.parse(await download.blob.text());
    }
  };
}

async function fetchStarted(h, count = 1) {
  // Advance pending Promise callbacks; no clocks or external polling are involved.
  for (let i = 0; i < 12 && h.requests.length < count; i += 1) await new Promise(setImmediate);
  assert.equal(h.requests.length, count);
}

test("actual exported v1 download restores notes in a new tab after compiling the same evidence", async () => {
  let h = harness();
  await h.inspect();
  assert.equal(h.el("matrix").dataset.renderedCells, "12");
  assert.equal(h.requests[0].url, "/api/inspect");
  assert.deepEqual(JSON.parse(h.requests[0].options.body), { candidate: fixture.candidate, authority: fixture.authority });
  await h.select(); await h.note("Delivery review from real compiler report."); await h.disposition("DISCUSS_WITH_PRIME");
  const draft = await h.draft();
  assert.equal(draft.schema, "uiowa-rfq18649-analyst-handoff-draft/v1");
  assert.equal(draft.report_receipt_sha256, fixture.report.receipt_sha256);
  assert.equal(draft.synthetic_demo, false);
  await h.el("resetBtn").click();
  // A new tab has no memory cache; the original file-import contract remains.
  h = harness();
  await h.inspect(); await h.select();
  assert.equal(h.el("note").value, "");
  h.el("handoffFile").files = [jsonFile(draft)];
  await h.el("importDraftBtn").click();
  assert.equal(h.el("note").value, "Delivery review from real compiler report.");
  assert.equal(h.el("disposition").value, "DISCUSS_WITH_PRIME");
  assert.equal(h.snapshot().notes.length, 12);
  assert.deepEqual(await h.draft(), draft);
  await h.el("markdownBtn").click();
  const markdown = await h.downloads.at(-1).blob.text();
  assert.ok(h.downloads.at(-1).filename.endsWith(".md"));
  assert.ok(markdown.includes(fixture.report.receipt_sha256));
  assert.ok(markdown.includes("Delivery review from real compiler report\\."));
  assert.equal((markdown.match(/^### /gm) || []).length, 12);
});

test("mismatched draft receipt leaves current notes and dispositions intact", async () => {
  const h = harness(); await h.inspect(); await h.select();
  await h.note("Keep this current work."); await h.disposition("NEEDS_EVIDENCE");
  const draft = await h.draft(); const before = h.snapshot();
  draft.report_receipt_sha256 = fixture.report2.receipt_sha256;
  h.el("handoffFile").files = [jsonFile(draft)]; await h.el("importDraftBtn").click();
  assert.deepEqual(h.snapshot(), before);
  assert.equal(h.el("note").value, "Keep this current work.");
  assert.ok(h.el("error").textContent.includes("does not match"));
  assert.equal(h.el("importDraftBtn").disabled, false);
});

test("invalid UTF-8 saved draft preserves the current report, notes and dispositions", async () => {
  const h = harness(); await h.inspect(); await h.select();
  await h.note("Keep this current work."); await h.disposition("NEEDS_EVIDENCE");
  const draft = await h.draft();
  const row = draft.cell_notes.find(cell => cell.group === "ESS" && cell.dimension === "software");
  assert.ok(row);
  row.analyst_note = "INVALID_UTF8_NOTE";
  row.disposition = "DISCUSS_WITH_PRIME";
  const bytes = Buffer.from(JSON.stringify(draft), "utf8");
  const noteOffset = bytes.indexOf("INVALID_UTF8_NOTE");
  assert.notEqual(noteOffset, -1);
  bytes[noteOffset] = 0xff;
  const before = h.snapshot();
  const reportBefore = h.evaluate("JSON.stringify(state.report)");
  h.el("handoffFile").files = [new Blob([bytes], { type: "application/json" })];
  await h.el("importDraftBtn").click();
  assert.deepEqual(h.snapshot(), before);
  assert.equal(h.evaluate("JSON.stringify(state.report)"), reportBefore);
  assert.equal(h.el("note").value, "Keep this current work.");
  assert.equal(h.el("disposition").value, "NEEDS_EVIDENCE");
  assert.match(h.el("error").textContent, /UTF-8/);
  for (const id of ["importDraftBtn", "exportBtn", "markdownBtn"]) assert.equal(h.el(id).disabled, false);
});

test("late inspect response cannot repopulate a cleared workbench", async () => {
  const h = harness(); const wait = deferred(); h.setFetch(() => wait.promise);
  const pending = h.inspect(); await fetchStarted(h);
  await h.el("resetBtn").click();
  wait.resolve(response(fixture.report)); await pending;
  assert.equal(h.snapshot().receipt, null);
  assert.equal(h.el("matrix").dataset.renderedCells, "0");
  assert.equal(h.el("exportBtn").disabled, true);
  assert.equal(h.el("importDraftBtn").disabled, true);
  assert.equal(h.el("markdownBtn").disabled, true);
  assert.equal(h.el("inspectBtn").disabled, false);
});

test("an older inspect response cannot replace a newer successfully compiled generation", async () => {
  const h = harness(); const wait = deferred(); h.setFetch(() => wait.promise);
  const pending = h.inspect(); await fetchStarted(h);
  await h.el("resetBtn").click();
  h.setFetch(() => Promise.resolve(response(fixture.report2)));
  await h.inspect(); await h.select(); await h.note("Belongs to the new generation.");
  const before = h.snapshot();
  wait.resolve(response(fixture.report)); await pending;
  assert.deepEqual(h.snapshot(), before);
  assert.equal(h.snapshot().receipt, fixture.report2.receipt_sha256);
  assert.equal(h.el("note").value, "Belongs to the new generation.");
  assert.equal(h.el("inspectBtn").disabled, false);
});

test("late saved-draft read cannot overwrite an intervening analyst edit", async () => {
  const h = harness(); await h.inspect(); await h.select(); await h.note("Saved note.");
  const draft = await h.draft(); const delayed = delayedFile(draft);
  h.el("handoffFile").files = [delayed.file];
  const pending = h.el("importDraftBtn").click();
  await h.note("Newer edit while file reading."); await h.disposition("TECHNICAL_DRAFT_NOTE");
  const before = h.snapshot(); delayed.finish(); await pending;
  assert.deepEqual(h.snapshot(), before);
  assert.equal(h.el("note").value, "Newer edit while file reading.");
  assert.ok(h.el("error").textContent.includes("Notes changed"));
  assert.equal(h.el("importDraftBtn").disabled, false);
});

test("late saved-draft read cannot overwrite a replacement generation", async () => {
  const h = harness(); await h.inspect(); await h.select(); await h.note("Old generation draft.");
  const draft = await h.draft(); const delayed = delayedFile(draft);
  h.el("handoffFile").files = [delayed.file];
  const pending = h.el("importDraftBtn").click();
  h.setFetch(() => Promise.resolve(response(fixture.report2)));
  await h.inspect(); await h.select(); await h.note("Replacement generation note.");
  const before = h.snapshot(); delayed.finish(); await pending;
  assert.deepEqual(h.snapshot(), before);
  assert.equal(h.el("note").value, "Replacement generation note.");
  assert.equal(h.el("error").textContent, "");
  assert.equal(h.el("importDraftBtn").disabled, false);
});


test("same receipt reinspection automatically restores exact tab draft and explicitly emptied work stays empty", async () => {
  const h = harness(); await h.inspect(); await h.select();
  await h.note("Keep this across reinspection."); await h.disposition("NEEDS_EVIDENCE");
  const original = await h.draft();
  assert.equal(h.evaluate("state.savedDrafts.size"), 1);
  await h.inspect(); await h.select();
  assert.match(h.el("exportStatus").textContent, /same report receipt/);
  assert.deepEqual(await h.draft(), original);
  await h.note(""); await h.disposition("UNREVIEWED");
  await h.inspect(); await h.select();
  assert.equal(h.el("note").value, "");
  assert.equal(h.el("disposition").value, "UNREVIEWED");
  assert.equal(h.evaluate("state.savedDrafts.size"), 1);
  assert.equal(h.evaluate("[...state.savedDrafts.values()][0].notesCount"), 0);
  assert.equal(h.evaluate("[...state.savedDrafts.values()][0].dispositionCount"), 0);
});

test("changed receipt stays separate and saved download does not reopen a cleared report", async () => {
  const h = harness(); await h.inspect(); await h.select();
  await h.note("First receipt only.");
  const original = await h.draft();
  h.setFetch(() => Promise.resolve(response(fixture.report2)));
  await h.inspect(); await h.select();
  assert.equal(h.el("note").value, "");
  await h.note("Second receipt only.");
  assert.equal(h.evaluate("state.savedDrafts.size"), 2);
  h.el("savedDraftSelect").value = fixture.report.receipt_sha256;
  await h.el("savedDraftSelect").emit("change");
  assert.equal(h.el("restoreTabDraftBtn").disabled, true);
  const before = h.snapshot();
  h.evaluate("restoreTabDraft()");
  assert.deepEqual(h.snapshot(), before);
  assert.match(h.el("error").textContent, /does not match/);
  await h.el("resetBtn").click();
  assert.equal(h.snapshot().receipt, null);
  assert.equal(h.el("downloadTabDraftBtn").disabled, false);
  await h.el("downloadTabDraftBtn").click();
  assert.deepEqual(JSON.parse(await h.downloads.at(-1).blob.text()), original);
  assert.equal(h.snapshot().receipt, null);
  assert.equal(h.el("exportBtn").disabled, true);
  assert.equal(h.el("restoreTabDraftBtn").disabled, true);
});

test("failed inspection clears active authority while retaining a draft for later matching inspection", async () => {
  const h = harness(); await h.inspect(); await h.select(); await h.note("Recover after rejection.");
  h.setFetch(() => Promise.resolve({ ok: false, status: 400, json: async () => ({ error: "Fixture compiler refusal" }) }));
  await h.inspect();
  assert.equal(h.snapshot().receipt, null);
  assert.equal(h.el("exportBtn").disabled, true);
  assert.equal(h.el("importDraftBtn").disabled, true);
  assert.equal(h.evaluate("state.savedDrafts.size"), 1);
  assert.equal(h.el("downloadTabDraftBtn").disabled, false);
  h.setFetch(() => Promise.resolve(response(fixture.report)));
  await h.inspect(); await h.select();
  assert.equal(h.el("note").value, "Recover after rejection.");
});

test("unserializable current work blocks clear, demo and inspection without destroying the last valid snapshot", async () => {
  const h = harness(); await h.inspect(); await h.select(); await h.note("Last valid note.");
  const saved = h.evaluate("JSON.stringify([...state.savedDrafts])");
  await h.note("x".repeat(4001));
  const before = h.snapshot();
  for (const id of ["resetBtn", "demoBtn", "inspectBtn", "restoreTabDraftBtn"]) {
    await h.el(id).click();
    assert.deepEqual(h.snapshot(), before);
    assert.equal(h.evaluate("JSON.stringify([...state.savedDrafts])"), saved);
    assert.equal(h.el("note").value.length, 4001);
    assert.match(h.el("error").textContent, /4000/);
  }
  assert.equal(h.requests.length, 1);
  assert.equal(h.el("inspectBtn").disabled, false);
});

test("a receipt match alone cannot restore altered synthetic identity or cell statuses", async () => {
  for (const change of ["draft.synthetic_demo = true", "draft.cell_notes[0].compiler_status = 'HOLD_CONFLICT'"]) {
    const h = harness(); await h.inspect(); await h.select(); await h.note("Bound to full report.");
    await h.el("resetBtn").click();
    h.evaluate(`{
      const [receipt, saved] = [...state.savedDrafts][0];
      const draft = JSON.parse(saved.text);
      ${change};
      state.savedDrafts.set(receipt, Object.freeze({...saved, text: JSON.stringify(draft)}));
    }`);
    assert.throws(() => h.setReport(fixture.report));
    assert.equal(h.snapshot().receipt, null);
    assert.equal(h.el("exportBtn").disabled, true);
  }
});

test("a saved-draft read begun before Clear cannot restore work after the generation changes", async () => {
  const h = harness(); await h.inspect(); await h.select(); await h.note("Current cached draft.");
  const draft = await h.draft(); const delayed = delayedFile(draft);
  h.el("handoffFile").files = [delayed.file];
  const pending = h.el("importDraftBtn").click();
  await h.el("resetBtn").click();
  delayed.finish(); await pending;
  assert.equal(h.snapshot().receipt, null);
  assert.equal(h.snapshot().notes.length, 0);
  assert.equal(h.el("exportBtn").disabled, true);
  assert.equal(h.evaluate("state.savedDrafts.size"), 1);
});
