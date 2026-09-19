"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { parseDraft, MAX_DRAFT_BYTES } = require("./handoff_import.js");

function fixture(softwareDimension = "software") {
  const report = {
    mode: "UNTRUSTED_INSPECTION",
    receipt_sha256: "a".repeat(64),
    aggregate_state: "HOLD_TRUSTED_AUTHORITY_REQUIRED",
    trust: { current_evidence_review_authority: false, authority_root_supplied_out_of_band: false },
    assessment_matrix: []
  };
  for (const group of ["ESS", "RIS", "IAM"]) {
    for (const dimension of [softwareDimension, "security", "deployment", "ai_readiness"]) {
      report.assessment_matrix.push({ group, dimension, status: "UNTRUSTED_EVIDENCE_CONSISTENT" });
    }
  }
  const draft = {
    schema: "uiowa-rfq18649-analyst-handoff-draft/v1",
    status: "DRAFT_NON_AUTHORITATIVE",
    report_receipt_sha256: report.receipt_sha256,
    report_mode: report.mode,
    aggregate_state: report.aggregate_state,
    synthetic_demo: false,
    cell_notes: report.assessment_matrix.map(cell => ({
      group: cell.group, dimension: cell.dimension, compiler_status: cell.status,
      disposition: "UNREVIEWED", analyst_note: ""
    })),
    authority: {
      buyer_approved: false, prime_approved: false, current_evidence_review_authority: false,
      submission_authorized: false, signature_authorized: false,
      invoice_or_payment_authorized: false, recognized_revenue: false
    }
  };
  return { report, draft };
}

test("restores every cell independent of export row order without mutating the report", () => {
  const { report, draft } = fixture();
  const original = JSON.stringify(report);
  draft.cell_notes[0].analyst_note = "Unicode café 📝; literal {\"key\":1}, backslash \\, newline\nsecond line";
  draft.cell_notes[0].disposition = "DISCUSS_WITH_PRIME";
  draft.cell_notes.reverse();
  const result = parseDraft(JSON.stringify(draft), report);
  assert.equal(result.notes.size, 12);
  assert.equal(result.dispositions.size, 12);
  assert.equal(result.notes.get("ESS|software"), draft.cell_notes[11].analyst_note);
  assert.equal(result.dispositions.get("ESS|software"), "DISCUSS_WITH_PRIME");
  assert.equal(JSON.stringify(report), original);
});

test("supports the existing synthetic demo dimension and requires its exact marker", () => {
  const { report, draft } = fixture("software_development");
  report.synthetic_demo = true;
  draft.synthetic_demo = true;
  assert.equal(parseDraft(JSON.stringify(draft), report).notes.size, 12);
  draft.synthetic_demo = false;
  assert.throws(() => parseDraft(JSON.stringify(draft), report), /synthetic marker/);
});

test("requires exact report receipt, mode, aggregate, and synthetic context", () => {
  for (const [key, value] of [
    ["report_receipt_sha256", "b".repeat(64)], ["report_mode", "CURRENT_TRUSTED_HOST"],
    ["aggregate_state", "READY"], ["synthetic_demo", "false"]
  ]) {
    const { report, draft } = fixture();
    draft[key] = value;
    assert.throws(() => parseDraft(JSON.stringify(draft), report), /receipt|context/);
  }
});

test("rejects duplicate JSON keys including escaped spellings and nested cells", () => {
  const { report, draft } = fixture();
  const text = JSON.stringify(draft);
  for (const altered of [
    text.replace('"status":"DRAFT_NON_AUTHORITATIVE"', '"status":"DRAFT_NON_AUTHORITATIVE","status":"DRAFT_NON_AUTHORITATIVE"'),
    text.replace('"buyer_approved":false', '"buyer_approved":true,"buyer_approved":false'),
    text.replace('"analyst_note":""', '"analyst_note":"first","analyst_note":"second"'),
    text.replace('"status":"DRAFT_NON_AUTHORITATIVE"', '"sta\\u0074us":"DRAFT_NON_AUTHORITATIVE","status":"DRAFT_NON_AUTHORITATIVE"')
  ]) assert.throws(() => parseDraft(altered, report), /duplicate JSON key/);
});

test("rejects missing or unknown properties at every schema level", () => {
  for (const level of ["root", "authority", "cell"]) {
    for (const action of ["extra", "missing"]) {
      const { report, draft } = fixture();
      const target = level === "root" ? draft : level === "authority" ? draft.authority : draft.cell_notes[0];
      if (action === "extra") target.unexpected = "not carried forward";
      else delete target[Object.keys(target)[0]];
      assert.throws(() => parseDraft(JSON.stringify(draft), report), /unexpected or missing/);
    }
  }
});

test("rejects every non-false authority flag including false-looking strings and numbers", () => {
  const { draft: template } = fixture();
  for (const flag of Object.keys(template.authority)) {
    for (const invalid of [true, "false", 0, null]) {
      const { report, draft } = fixture();
      draft.authority[flag] = invalid;
      assert.throws(() => parseDraft(JSON.stringify(draft), report), /authority flag.*false/);
    }
  }
});

test("rejects unknown, repeated, missing, and status-mismatched cells", () => {
  for (const mutate of [
    draft => { draft.cell_notes[0].group = "UNKNOWN"; },
    draft => { draft.cell_notes[0].dimension = "software|security"; },
    draft => { draft.cell_notes[1] = { ...draft.cell_notes[0] }; },
    draft => { draft.cell_notes.pop(); },
    draft => { draft.cell_notes[0].compiler_status = "READY"; }
  ]) {
    const { report, draft } = fixture();
    mutate(draft);
    assert.throws(() => parseDraft(JSON.stringify(draft), report));
  }
});

test("validates dispositions and note bounds before returning any state", () => {
  const { report, draft } = fixture();
  draft.cell_notes[0].analyst_note = "x".repeat(4000);
  assert.equal(parseDraft(JSON.stringify(draft), report).notes.get("ESS|software").length, 4000);
  draft.cell_notes[11].analyst_note = "x".repeat(4001);
  assert.throws(() => parseDraft(JSON.stringify(draft), report), /4000/);
  draft.cell_notes[11].analyst_note = 7;
  assert.throws(() => parseDraft(JSON.stringify(draft), report), /must be strings/);
  draft.cell_notes[11].analyst_note = "";
  draft.cell_notes[11].disposition = "APPROVED";
  assert.throws(() => parseDraft(JSON.stringify(draft), report), /disposition/);
});

test("enforces UTF-8 byte size and a bounded parse depth", () => {
  const { report } = fixture();
  assert.throws(() => parseDraft(" ".repeat(MAX_DRAFT_BYTES + 1), report), /1 MiB/);
  assert.throws(() => parseDraft('"' + "é".repeat(MAX_DRAFT_BYTES / 2) + '"', report), /1 MiB/);
  assert.throws(() => parseDraft("[".repeat(66) + "0" + "]".repeat(66), report), /nesting/);
});

test("rejects malformed JSON, trailing text and non-finite JSON values", () => {
  const { report, draft } = fixture();
  for (const text of ["", "{", "[1,]", "{\"x\":1,}", '"unterminated', '{"x":01}', '{"x":truefalse}',
    JSON.stringify(draft) + " false", '{"x":1e400}', '{"x":NaN}', '"bad\\q"']) {
    assert.throws(() => parseDraft(text, report));
  }
});

test("requires an active untrusted report with unique cell identities", () => {
  const { report, draft } = fixture();
  assert.throws(() => parseDraft(JSON.stringify(draft), null), /Compiler report|untrusted inspection/);
  report.trust.current_evidence_review_authority = true;
  assert.throws(() => parseDraft(JSON.stringify(draft), report), /Compiler report|untrusted inspection/);
  report.trust.current_evidence_review_authority = false;
  report.assessment_matrix[1] = { ...report.assessment_matrix[0] };
  assert.throws(() => parseDraft(JSON.stringify(draft), report), /duplicate.*assessment/);
});
