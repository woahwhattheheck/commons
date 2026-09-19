"use strict";

// Draft notes are portable only within the exact report generation they annotate.
// This module never changes the report, emits evidence authority, or mutates UI state.
(function (root) {
  const MAX_DRAFT_BYTES = 1024 * 1024;
  const MAX_JSON_DEPTH = 64;
  const DRAFT_KEYS = [
    "schema", "status", "report_receipt_sha256", "report_mode",
    "aggregate_state", "synthetic_demo", "cell_notes", "authority"
  ];
  const CELL_KEYS = ["group", "dimension", "compiler_status", "disposition", "analyst_note"];
  const AUTHORITY_KEYS = [
    "buyer_approved", "prime_approved", "current_evidence_review_authority",
    "submission_authorized", "signature_authorized", "invoice_or_payment_authorized",
    "recognized_revenue"
  ];
  const DISPOSITIONS = new Set([
    "UNREVIEWED", "NEEDS_EVIDENCE", "DISCUSS_WITH_PRIME", "TECHNICAL_DRAFT_NOTE"
  ]);

  function fail(message) { throw new Error(message); }
  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }
  function exactKeys(value, keys, label) {
    if (!isObject(value) || Object.keys(value).length !== keys.length ||
        !keys.every(key => Object.prototype.hasOwnProperty.call(value, key))) {
      fail(`${label} has missing or unknown fields.`);
    }
  }

  // JSON.parse silently accepts duplicate object keys. A small bounded parser
  // preserves JSON string/number semantics while rejecting that information loss.
  function parseJson(input) {
    if (typeof input !== "string") fail("Draft content must be JSON text.");
    if (new TextEncoder().encode(input).length > MAX_DRAFT_BYTES) {
      fail("Draft exceeds the 1 MiB intake limit.");
    }
    let position = 0;
    function whitespace() {
      while (position < input.length && /[\x20\t\r\n]/.test(input[position])) position++;
    }
    function string() {
      const start = position++;
      while (position < input.length) {
        const char = input[position++];
        if (char === "\\") { position++; continue; }
        if (char === '"') {
          try { return JSON.parse(input.slice(start, position)); }
          catch { fail("Draft contains an invalid JSON string."); }
        }
      }
      fail("Draft contains an unterminated JSON string.");
    }
    function value(depth) {
      if (depth > MAX_JSON_DEPTH) fail("Draft JSON nesting exceeds the supported limit.");
      whitespace();
      const char = input[position];
      if (char === '"') return string();
      if (char === "{") {
        position++;
        const object = Object.create(null);
        const seen = new Set();
        whitespace();
        if (input[position] === "}") { position++; return object; }
        while (position < input.length) {
          whitespace();
          if (input[position] !== '"') fail("Draft contains an invalid JSON object.");
          const key = string();
          if (seen.has(key)) fail("Draft contains a duplicate JSON key.");
          seen.add(key);
          whitespace();
          if (input[position++] !== ":") fail("Draft contains an invalid JSON object.");
          object[key] = value(depth + 1);
          whitespace();
          const delimiter = input[position++];
          if (delimiter === "}") return object;
          if (delimiter !== ",") fail("Draft contains an invalid JSON object.");
        }
        fail("Draft contains an unterminated JSON object.");
      }
      if (char === "[") {
        position++;
        const array = [];
        whitespace();
        if (input[position] === "]") { position++; return array; }
        while (position < input.length) {
          array.push(value(depth + 1));
          whitespace();
          const delimiter = input[position++];
          if (delimiter === "]") return array;
          if (delimiter !== ",") fail("Draft contains an invalid JSON array.");
        }
        fail("Draft contains an unterminated JSON array.");
      }
      for (const [token, literal] of [["true", true], ["false", false], ["null", null]]) {
        if (input.startsWith(token, position)) { position += token.length; return literal; }
      }
      const match = input.slice(position).match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/);
      if (match) {
        position += match[0].length;
        const number = Number(match[0]);
        if (!Number.isFinite(number)) fail("Draft contains a non-finite JSON number.");
        return number;
      }
      fail("Draft is not valid JSON.");
    }
    const result = value(0);
    whitespace();
    if (position !== input.length) fail("Draft contains trailing or invalid JSON content.");
    return result;
  }

  function cellKey(cell) {
    if (typeof cell.group !== "string" || typeof cell.dimension !== "string" ||
        !cell.group || !cell.dimension || cell.group.includes("|") || cell.dimension.includes("|")) {
      fail("Assessment cell identity is invalid.");
    }
    return `${cell.group}|${cell.dimension}`;
  }

  function parseDraft(input, report) {
    if (!isObject(report) || report.mode !== "UNTRUSTED_INSPECTION" ||
        report.trust?.current_evidence_review_authority !== false ||
        report.trust?.authority_root_supplied_out_of_band !== false ||
        typeof report.receipt_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(report.receipt_sha256) ||
        typeof report.aggregate_state !== "string" ||
        !Array.isArray(report.assessment_matrix) || report.assessment_matrix.length !== 12) {
      fail("Load a valid untrusted inspection report before restoring a draft.");
    }
    const expected = new Map();
    for (const cell of report.assessment_matrix) {
      if (!isObject(cell) || typeof cell.status !== "string") fail("Active report cells are invalid.");
      const key = cellKey(cell);
      if (expected.has(key)) fail("Active report contains duplicate assessment cells.");
      expected.set(key, cell);
    }

    const draft = parseJson(input);
    exactKeys(draft, DRAFT_KEYS, "Draft");
    if (draft.schema !== "uiowa-rfq18649-analyst-handoff-draft/v1" ||
        draft.status !== "DRAFT_NON_AUTHORITATIVE") fail("Draft schema or status is unsupported.");
    if (draft.report_receipt_sha256 !== report.receipt_sha256) fail("Draft receipt does not match the active report.");
    if (draft.report_mode !== report.mode || draft.aggregate_state !== report.aggregate_state ||
        draft.synthetic_demo !== (report.synthetic_demo === true)) {
      fail("Draft report context does not match the active report.");
    }
    exactKeys(draft.authority, AUTHORITY_KEYS, "Draft authority");
    if (!AUTHORITY_KEYS.every(key => draft.authority[key] === false)) {
      fail("Draft authority flags must all be false.");
    }
    if (!Array.isArray(draft.cell_notes) || draft.cell_notes.length !== expected.size) {
      fail("Draft must contain exactly the active report's 12 assessment cells.");
    }

    // Build fresh maps, then return them together. Any error leaves callers'
    // existing notes, selected cell, and immutable report untouched.
    const notes = new Map();
    const dispositions = new Map();
    for (const cell of draft.cell_notes) {
      exactKeys(cell, CELL_KEYS, "Draft cell");
      const key = cellKey(cell);
      const reportCell = expected.get(key);
      if (!reportCell || notes.has(key)) fail("Draft contains an unknown or duplicate assessment cell.");
      if (cell.compiler_status !== reportCell.status) fail("Draft compiler status does not match the active report.");
      if (!DISPOSITIONS.has(cell.disposition)) fail("Draft contains an unsupported disposition.");
      if (typeof cell.analyst_note !== "string" || cell.analyst_note.length > 4000) {
        fail("Draft analyst notes must be text of at most 4000 characters.");
      }
      notes.set(key, cell.analyst_note);
      dispositions.set(key, cell.disposition);
    }
    return { notes, dispositions };
  }

  const api = Object.freeze({ parseDraft, MAX_DRAFT_BYTES });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.HandoffImport = api;
})(typeof window === "undefined" ? null : window);
