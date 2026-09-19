"use strict";
// Node's standard-library tests run the actual app.js; this DOM double is not
// browser/print evidence. The separate Chromium rehearsal checks those surfaces.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, "comparison.json"), "utf8"));
class Element {
  constructor(tag = "div") { this.tagName = tag; this.children = []; this.dataset = {}; this.value = ""; this._text = ""; this.attributes = {}; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(c => c.textContent).join(""); }
  get childElementCount() { return this.children.length; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this._text = ""; this.children = children; }
  setAttribute(k, v) { this.attributes[k] = v; }
  addEventListener() {} click() {} remove() {}
}
function setup() {
  const elements = new Map();
  const context = vm.createContext({
    document: {
      getElementById: id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); },
      createElement: tag => new Element(tag), body: new Element("body")
    },
    Option: class extends Element { constructor(label, value) { super("option"); this.textContent = label; this.value = value; } },
    URLSearchParams, location: { search: "" },
    URL: { createObjectURL: () => "blob:fixture", revokeObjectURL: () => {} },
    Blob: class { constructor(parts) { context.lastExport = parts.join(""); } }
  });
  vm.runInContext(app, context, { filename: "app.js" });
  return { context, elements };
}
for (const [status, kind, label] of [
  ["UNTRUSTED_EVIDENCE_CONSISTENT", "consistent", "Internally consistent"],
  ["HOLD_MISSING_EVIDENCE", "missing", "Missing evidence"],
  ["HOLD_CONFLICT", "conflict", "Conflicting evidence"],
  ["HOLD_STALE_EVIDENCE", "stale", "Stale evidence"],
  ["NOT_ASSESSED", "unassessed", "Not assessed"],
  ["NOT_APPLICABLE", "inapplicable", "Not applicable"],
  ["UNKNOWN", "unknown", "Unknown"],
  ["FUTURE_SCHEMA_STATUS", "unrecognized", "Unrecognized status"],
  ["HOLD_CONFLICTING_EVIDENCE", "unrecognized", "Unrecognized status"],
  ["constructor", "unrecognized", "Unrecognized status"],
  ["__proto__", "unrecognized", "Unrecognized status"]
]) test(`exact status ${status} retains its own meaning`, () => {
  const { context } = setup();
  const actual = context.cellPresentation(Object.freeze({ status }));
  assert.equal(actual.kind, kind); assert.ok(actual.label.includes(label));
});
for (const [name, cell, expected] of [
  ["absent", {}, "Not supplied (field absent)"],
  ["null", { maturity: null }, "Not determined (null)"],
  ["withheld", { status: "UNTRUSTED_EVIDENCE_CONSISTENT", maturity: null }, "Not reported in untrusted inspection (null)"],
  ["zero", { maturity: 0 }, "Supplied value: 0 (display only)"],
  ["negative zero", { maturity: -0 }, "Supplied value: -0 (display only)"],
  ["positive", { maturity: 3 }, "Supplied value: 3 (display only)"],
  ["false", { maturity: false }, "Non-numeric or invalid value; inspect original record"],
  ["empty string", { maturity: "" }, "Non-numeric or invalid value; inspect original record"],
  ["numeric string", { maturity: "0" }, "Non-numeric or invalid value; inspect original record"],
  ["NaN", { maturity: NaN }, "Non-numeric or invalid value; inspect original record"],
  ["Infinity", { maturity: Infinity }, "Non-numeric or invalid value; inspect original record"],
  ["array", { maturity: [] }, "Non-numeric or invalid value; inspect original record"],
  ["object", { maturity: {} }, "Non-numeric or invalid value; inspect original record"]
]) test(`numeric availability: ${name}`, () => {
  const { context } = setup(); assert.equal(context.valuePresentation(Object.freeze(cell), "maturity"), expected);
});
test("inherited numeric property stays absent", () => {
  const { context } = setup();
  assert.equal(context.valuePresentation(Object.create({ maturity: 0 }), "maturity"), "Not supplied (field absent)");
});
test("all twelve actual app cards retain raw status and source report bytes", () => {
  const { context, elements } = setup(); const original = JSON.stringify(fixture.report);
  context.installReport(fixture.report);
  assert.equal(elements.get("matrix").childElementCount, 12);
  assert.equal(elements.get("matrix").dataset.renderedCells, "12");
  fixture.report.assessment_matrix.forEach((cell, i) => {
    const card = elements.get("matrix").children[i];
    assert.ok(card.textContent.includes(`Source status: ${cell.status}`));
    assert.ok(card.textContent.includes(context.cellPresentation(cell).label));
  });
  assert.equal(JSON.stringify(fixture.report), original);
});
test("zero alongside conflict does not resolve conflict", () => {
  const { context, elements } = setup(); context.installReport(fixture.report);
  const card = elements.get("matrix").children[9];
  assert.equal(card.dataset.evidenceState, "conflict");
  assert.ok(card.textContent.includes("Supplied value: 0 (display only)"));
  assert.ok(card.textContent.includes("unresolved"));
});
test("detail explicitly names missing values without replacing raw values", () => {
  const { context, elements } = setup(); context.installReport(fixture.report);
  context.selectCell("ESS|security");
  let detail = JSON.parse(elements.get("detail").textContent);
  assert.equal(detail.display_only.maturity_availability, "Not supplied (field absent)");
  assert.equal(Object.hasOwn(detail, "maturity"), false);
  context.selectCell("ESS|software"); detail = JSON.parse(elements.get("detail").textContent);
  assert.equal(detail.maturity, 0); assert.equal(detail.confidence_bp, 0);
});
test("filters retain raw status and clear correctly", () => {
  const { context, elements } = setup(); context.installReport(fixture.report);
  elements.get("statusFilter").value = "HOLD_CONFLICT"; context.renderMatrix();
  assert.equal(elements.get("matrix").childElementCount, 2);
  elements.get("statusFilter").value = ""; context.renderMatrix();
  assert.equal(elements.get("matrix").childElementCount, 12);
});
test("source-like markup is text, not a new DOM subtree", () => {
  const { context, elements } = setup(); const copy = structuredClone(fixture.report);
  copy.assessment_matrix[0].status = "<b>not a finding</b>"; context.installReport(copy);
  const status = elements.get("matrix").children[0].children.find(c => c.className === "status");
  assert.equal(status.children.length, 0); assert.ok(status.textContent.includes("<b>not a finding</b>"));
});
test("handoff contract and source codes remain unchanged", () => {
  const { context } = setup(); context.installReport(fixture.report);
  vm.runInContext('state.notes.set("ESS|software", "Literal note \\n retained"); state.dispositions.set("ESS|software", "NEEDS_EVIDENCE")', context);
  context.exportDraft(); const exported = JSON.parse(context.lastExport);
  assert.equal(exported.schema, "uiowa-rfq18649-analyst-handoff-draft/v1");
  assert.equal(exported.cell_notes.length, 12);
  assert.equal(exported.cell_notes[0].analyst_note, "Literal note \n retained");
  assert.equal(exported.cell_notes[0].disposition, "NEEDS_EVIDENCE");
  assert.deepEqual(exported.cell_notes.map(c => c.compiler_status), fixture.report.assessment_matrix.map(c => c.status));
  assert.equal(exported.synthetic_demo, true);
  assert.equal(Object.keys(exported.authority).length, 7);
  assert.ok(Object.values(exported.authority).every(v => v === false));
  assert.ok(exported.cell_notes.every(c => !Object.hasOwn(c, "display_only")));
});
test("reset removes all data cards and disables export", () => {
  const { context, elements } = setup(); context.installReport(fixture.report); context.resetWorkbench();
  assert.equal(elements.get("matrix").childElementCount, 0);
  assert.equal(elements.get("exportBtn").disabled, true);
});
