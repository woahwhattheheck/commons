"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { buildDraft, validateDraft, renderMarkdown } = require("./handoff.js");
const { parseDraft } = require("./handoff_import.js");

function fixture(synthetic = false) {
  const dimensions = [synthetic ? "software_development" : "software", "security", "deployment", "ai_readiness"];
  const assessment_matrix = ["ESS", "RIS", "IAM"].flatMap(group => dimensions.map(dimension => ({
    group, dimension,
    status: "UNTRUSTED_EVIDENCE_CONSISTENT",
    source_ids: [`source-${group}-${dimension}`],
    source_record_sha256s: ["1".repeat(64)],
    reason_codes: ["TRUSTED_AUTHORITY_ROOT_REQUIRED"], maturity: null, confidence_bp: null
  })));
  assessment_matrix[1] = { ...assessment_matrix[1], status: "HOLD_MISSING_EVIDENCE", source_ids: [], source_record_sha256s: [], reason_codes: ["NO_ROOTED_SOURCE_RECORD"] };
  assessment_matrix[6] = { ...assessment_matrix[6], status: "HOLD_STALE_EVIDENCE", reason_codes: ["STALE_ROOTED_SOURCE:source-RIS-deployment"] };
  assessment_matrix[10] = { ...assessment_matrix[10], status: "HOLD_CONFLICT", reason_codes: ["ROOTED_MATURITY_CONFLICT"] };
  return {
    mode: "UNTRUSTED_INSPECTION", aggregate_state: "HOLD_TRUSTED_AUTHORITY_REQUIRED",
    receipt_sha256: "a".repeat(64), evaluated_at: "2026-09-19T12:00:00Z",
    authority_root_sha256: "b".repeat(64), evidence_authority: { generation: "fixture-generation-1" },
    trust: { current_evidence_review_authority: false, authority_root_supplied_out_of_band: false },
    ...(synthetic ? { synthetic_demo: true } : {}), assessment_matrix,
    source_receipts: assessment_matrix.flatMap(cell => cell.source_ids.map(source_id => ({
      source_id, source_record_sha256: "1".repeat(64), source_content_sha256: "2".repeat(64)
    })))
  };
}

const clone = value => JSON.parse(JSON.stringify(value));

test("draft round trip restores all notes in report order without mutating inputs", () => {
  const report = fixture();
  const before = JSON.stringify(report);
  const notes = new Map([["ESS|software", "Observed delivery process.\nNext question: source age."]]);
  const dispositions = new Map([["ESS|software", "DISCUSS_WITH_PRIME"]]);
  const draft = buildDraft(report, notes, dispositions);
  const shuffled = clone(draft);
  shuffled.cell_notes.reverse();
  assert.deepEqual(validateDraft(shuffled, report), draft.cell_notes);
  assert.equal(draft.cell_notes[0].analyst_note, notes.get("ESS|software"));
  assert.equal(draft.cell_notes[0].disposition, "DISCUSS_WITH_PRIME");
  assert.equal(draft.cell_notes.length, 12);
  assert.equal(JSON.stringify(report), before);
  assert.deepEqual([...notes], [["ESS|software", "Observed delivery process.\nNext question: source age."]]);
  assert.ok(Object.values(draft.authority).every(flag => flag === false));
  const restored = validateDraft(draft, report);
  restored[0].analyst_note = "changed copy";
  assert.notEqual(draft.cell_notes[0].analyst_note, "changed copy");
});

test("v1 draft metadata and authority must match the exact report", () => {
  const report = fixture();
  const original = buildDraft(report);
  const mutations = [
    draft => { draft.report_receipt_sha256 = "b".repeat(64); },
    draft => { draft.report_mode = "CURRENT_TRUSTED_HOST"; },
    draft => { draft.aggregate_state = "READY_FOR_PRIME_TEAMING_REVIEW"; },
    draft => { draft.synthetic_demo = true; },
    draft => { draft.synthetic_demo = "false"; },
    draft => { draft.status = "FINAL"; },
    draft => { draft.authority.buyer_approved = true; },
    draft => { draft.authority.recognized_revenue = 0; },
    draft => { delete draft.authority.prime_approved; },
    draft => { draft.authority.extra_authority = false; },
    draft => { draft.schema = "unknown"; },
    draft => { draft.extra = "silently ignored"; }
  ];
  for (const mutate of mutations) {
    const draft = clone(original); mutate(draft);
    assert.throws(() => validateDraft(draft, report));
  }
});

test("missing, duplicate, unexpected and altered cells cannot be restored", () => {
  const report = fixture();
  const original = buildDraft(report);
  const mutations = [
    draft => draft.cell_notes.pop(),
    draft => { draft.cell_notes[11] = clone(draft.cell_notes[0]); },
    draft => { draft.cell_notes[0].group = "OTHER"; },
    draft => { draft.cell_notes[0].dimension = "software_development"; },
    draft => { draft.cell_notes[0].compiler_status = "READY"; },
    draft => { draft.cell_notes[0].disposition = "APPROVED"; },
    draft => { draft.cell_notes[0].analyst_note = 42; },
    draft => { draft.cell_notes[0].analyst_note = "x".repeat(4001); },
    draft => { delete draft.cell_notes[0].analyst_note; }
  ];
  for (const mutate of mutations) {
    const draft = clone(original); mutate(draft);
    assert.throws(() => validateDraft(draft, report));
  }
});

test("build rejects oversized notes, unknown keys and authority-bearing reports", () => {
  const report = fixture();
  assert.equal(buildDraft(report, new Map([["ESS|software", "x".repeat(4000)]])).cell_notes[0].analyst_note.length, 4000);
  assert.throws(() => buildDraft(report, new Map([["ESS|software", "x".repeat(4001)]])));
  assert.throws(() => buildDraft(report, new Map([["OTHER|software", "lost"]])));
  assert.throws(() => buildDraft(report, new Map(), new Map([["ESS|software", "APPROVED"]])));
  assert.throws(() => buildDraft(report, {}));
  for (const field of ["current_evidence_review_authority", "authority_root_supplied_out_of_band"]) {
    const invalid = clone(report); invalid.trust[field] = true;
    assert.throws(() => buildDraft(invalid));
  }
  const duplicate = clone(report); duplicate.assessment_matrix[11] = duplicate.assessment_matrix[0];
  assert.throws(() => buildDraft(duplicate));
});

test("Markdown preserves traceability, all cells, counts, HOLD follow-ups and analyst notes", () => {
  const report = fixture();
  const draft = buildDraft(report, new Map([["ESS|software", "Check source | record\n<b>draft</b>"]]), new Map([["ESS|software", "NEEDS_EVIDENCE"]]));
  const before = JSON.stringify({ report, draft });
  const markdown = renderMarkdown(report, draft);
  assert.equal((markdown.match(/^### /gm) || []).length, 12);
  assert.ok(markdown.includes(report.receipt_sha256));
  assert.ok(markdown.includes("source\\-ESS\\-software"));
  assert.ok(markdown.includes("1".repeat(64)));
  assert.ok(markdown.includes("2".repeat(64)));
  assert.ok(markdown.includes("STALE\\_ROOTED\\_SOURCE"));
  assert.ok(markdown.includes("Check source \\| record"));
  assert.ok(markdown.includes("&lt;b&gt;draft&lt;/b&gt;"));
  assert.ok(markdown.includes("Obtain source evidence"));
  assert.ok(markdown.includes("Refresh the stale source"));
  assert.ok(markdown.includes("Reconcile the conflicting source"));
  assert.ok(markdown.includes("UNREVIEWED: 11"));
  assert.ok(markdown.includes("HOLD\\_MISSING\\_EVIDENCE: 1"));
  assert.ok(markdown.includes("does not perform currentness verification"));
  assert.ok(markdown.includes("authority flag is false"));
  assert.equal(JSON.stringify({ report, draft }), before);
});

test("synthetic drafts remain separately marked and cannot restore onto real reports", () => {
  const demo = fixture(true);
  const draft = buildDraft(demo);
  assert.equal(validateDraft(draft, demo).length, 12);
  assert.ok(renderMarkdown(demo, draft).includes("YES — not compiler output"));
  assert.throws(() => validateDraft(draft, fixture()));
});

test("draft creation rejects isolated surrogate code units and malformed pair adjacency", () => {
  const report = fixture();
  const before = JSON.stringify(report);
  for (let unit = 0xD800; unit <= 0xDFFF; unit++) {
    const note = String.fromCharCode(unit);
    assert.throws(() => buildDraft(report, new Map([["ESS|software", note]])), /unpaired surrogate/);
  }
  for (const note of ["\uD800x\uDC00", "\uDC00\uD800", "\uD800\uD800", "\uDC00\uDC00"]) {
    assert.throws(() => buildDraft(report, new Map([["ESS|software", note]])), /unpaired surrogate/);
  }
  assert.equal(JSON.stringify(report), before);
});

test("ASCII escaped surrogate in the final row cannot restore or render a tampered draft", () => {
  const report = fixture();
  const draft = buildDraft(report, new Map([["ESS|software", "Keep the existing note."]]));
  const reportBefore = JSON.stringify(report);
  for (const note of ["\uD800", "\uDFFF", "before\uD800after", "\uDC00\uD800"]) {
    draft.cell_notes[11].analyst_note = note;
    const raw = JSON.stringify(draft);
    assert.ok(/\\u[dD][89a-fA-F][0-9a-fA-F]{2}/.test(raw));
    assert.equal(new TextDecoder("utf-8", { fatal: true }).decode(new TextEncoder().encode(raw)), raw);
    assert.throws(() => parseDraft(raw, report), /unpaired surrogate/);
    assert.throws(() => validateDraft(draft, report), /unpaired surrogate/);
    assert.throws(() => renderMarkdown(report, draft), /unpaired surrogate/);
    assert.equal(JSON.stringify(draft), raw);
  }
  assert.equal(JSON.stringify(report), reportBefore);
});

test("valid scalar notes retain exact JSON and UTF-8 Blob text within the existing length limit", async () => {
  const report = fixture();
  const notes = ["café 📝 \uFFFD e\u0301", "\uD800\uDC00\uDBFF\uDFFF", "literal \\ud800 text", "📝".repeat(2000)];
  for (const note of notes) {
    const draft = buildDraft(report, new Map([["ESS|software", note]]));
    const raw = await new Blob([JSON.stringify(draft)], { type: "application/json" }).text();
    assert.equal(parseDraft(raw, report).notes.get("ESS|software"), note);
    const markdown = renderMarkdown(report, draft);
    assert.equal(await new Blob([markdown], { type: "text/markdown;charset=utf-8" }).text(), markdown);
  }
  assert.throws(() => buildDraft(report, new Map([["ESS|software", "📝".repeat(2000) + "x"]])), /4000/);
});
