(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.CsAnalyticalExpansionCrossline = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var DEMAND_ID = "csanalytical-expansion-crossline-evidence-lims-01";
  var TRUTH_GATE = "HOLD / BUILD-AND-VERIFY";
  var LINES = {
    CCIT: ["VACUUM-DECAY", "HVLD"],
    RAW_MATERIAL: ["USP-661", "FTIR"],
    GAS: ["HS-GC", "O2-HEADSPACE"],
    MICRO: ["USP-71", "BIOBURDEN"]
  };
  var LINE_NAMES = ["CCIT", "RAW_MATERIAL", "GAS", "MICRO"];
  var MISROUTE = [
    ["CCIT", "USP-71"], ["CCIT", "HS-GC"], ["RAW_MATERIAL", "VACUUM-DECAY"],
    ["GAS", "HVLD"], ["GAS", "BIOBURDEN"], ["MICRO", "FTIR"], ["MICRO", "O2-HEADSPACE"]
  ];
  var GOLDEN_COUNTS = {
    input_rows: 120, ready: 90, held: 30, scheduled_holds: 0,
    released_reports: 0, staged_reports: 90
  };

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function text(value) { return String(value == null ? "" : value).trim(); }
  function pad(n, width) {
    var s = String(n);
    while (s.length < width) s = "0" + s;
    return s;
  }
  function lineFor(index) { return LINE_NAMES[(index - 1) % LINE_NAMES.length]; }
  function methodFor(line, index) {
    var names = LINES[line];
    return names[(index - 1) % names.length];
  }
  function methodOk(line, method) {
    return !!LINES[line] && LINES[line].indexOf(method) !== -1;
  }

  function buildAcceptanceFixture() {
    var rows = [];
    var i;
    for (i = 1; i <= 90; i += 1) {
      var line = lineFor(i);
      rows.push({
        row_id: "R" + pad(i, 3),
        study_id: "CSA-STU-" + pad(i, 3),
        sample_id: "CSA-SMP-" + pad(i, 3),
        lot_id: "CSA-LOT-" + pad(i, 3),
        package_id: "PKG-" + pad(i, 3),
        line: line,
        method: methodFor(line, i),
        qc_ok: true,
        source_ok: true,
        expected_hold: null
      });
    }
    for (i = 0; i < 8; i += 1) {
      var target = i + 1;
      rows.push({
        row_id: "R" + pad(91 + i, 3),
        study_id: "CSA-STU-" + pad(target, 3),
        sample_id: "CSA-SMP-" + pad(target, 3),
        lot_id: "CSA-LOT-" + pad(target, 3),
        package_id: "PKG-HDUP" + pad(i + 1, 2),
        line: lineFor(target),
        method: methodFor(lineFor(target), target),
        qc_ok: true,
        source_ok: true,
        expected_hold: "DUPLICATE_ID"
      });
    }
    for (i = 0; i < 7; i += 1) {
      rows.push({
        row_id: "R" + pad(99 + i, 3),
        study_id: "CSA-STU-HMIS" + pad(i + 1, 2),
        sample_id: "CSA-SMP-HMIS" + pad(i + 1, 2),
        lot_id: "CSA-LOT-HMIS" + pad(i + 1, 2),
        package_id: "PKG-HMIS" + pad(i + 1, 2),
        line: MISROUTE[i][0],
        method: MISROUTE[i][1],
        qc_ok: true,
        source_ok: true,
        expected_hold: "WRONG_LINE_METHOD"
      });
    }
    var missing = ["study_id", "package_id", "study_id", "package_id", "lot_id"];
    for (i = 0; i < 5; i += 1) {
      var row = {
        row_id: "R" + pad(106 + i, 3),
        study_id: "CSA-STU-HMETA" + pad(i + 1, 2),
        sample_id: "CSA-SMP-HMETA" + pad(i + 1, 2),
        lot_id: "CSA-LOT-HMETA" + pad(i + 1, 2),
        package_id: "PKG-HMETA" + pad(i + 1, 2),
        line: "CCIT",
        method: "VACUUM-DECAY",
        qc_ok: true,
        source_ok: true,
        expected_hold: "MISSING_STUDY_PACKAGE"
      };
      row[missing[i]] = "";
      rows.push(row);
    }
    for (i = 0; i < 5; i += 1) {
      var qcLine = lineFor(91 + i);
      rows.push({
        row_id: "R" + pad(111 + i, 3),
        study_id: "CSA-STU-HQC" + pad(i + 1, 2),
        sample_id: "CSA-SMP-HQC" + pad(i + 1, 2),
        lot_id: "CSA-LOT-HQC" + pad(i + 1, 2),
        package_id: "PKG-HQC" + pad(i + 1, 2),
        line: qcLine,
        method: methodFor(qcLine, 91 + i),
        qc_ok: false,
        source_ok: true,
        expected_hold: "INSTRUMENT_QC_FAILURE"
      });
    }
    for (i = 0; i < 5; i += 1) {
      var srcLine = lineFor(i + 1);
      rows.push({
        row_id: "R" + pad(116 + i, 3),
        study_id: "CSA-STU-HSRC" + pad(i + 1, 2),
        sample_id: "CSA-SMP-HSRC" + pad(i + 1, 2),
        lot_id: "CSA-LOT-HSRC" + pad(i + 1, 2),
        package_id: "PKG-HSRC" + pad(i + 1, 2),
        line: srcLine,
        method: methodFor(srcLine, i + 1),
        qc_ok: true,
        source_ok: false,
        expected_hold: "SOURCE_HASH_MISMATCH"
      });
    }
    return rows;
  }

  function classify(row, seen) {
    var key = [text(row.study_id), text(row.sample_id), text(row.lot_id)].join("|");
    if (text(row.study_id) && text(row.sample_id) && text(row.lot_id) && seen[key]) {
      return { ok: false, code: "DUPLICATE_ID" };
    }
    if (!methodOk(row.line, row.method)) return { ok: false, code: "WRONG_LINE_METHOD" };
    if (!text(row.study_id) || !text(row.package_id) || !text(row.lot_id) || !text(row.sample_id)) {
      return { ok: false, code: "MISSING_STUDY_PACKAGE" };
    }
    if (row.qc_ok === false) return { ok: false, code: "INSTRUMENT_QC_FAILURE" };
    if (row.source_ok === false) return { ok: false, code: "SOURCE_HASH_MISMATCH" };
    return { ok: true, key: key, study_id: text(row.study_id) };
  }

  function runGate(rows) {
    var inbound = clone(rows || buildAcceptanceFixture());
    var accessions = {};
    var holds = [];
    var seen = {};
    inbound.forEach(function (row) {
      var verdict = classify(row, seen);
      if (!verdict.ok) {
        holds.push({ study_id: row.study_id || null, code: verdict.code, state: "HOLD", scheduled: false });
        return;
      }
      accessions[verdict.study_id] = { study_id: verdict.study_id, state: "READY", released: false };
      seen[verdict.key] = true;
    });
    return {
      demand_id: DEMAND_ID,
      truth_gate: TRUTH_GATE,
      input_rows: inbound.length,
      ready: Object.keys(accessions).length,
      held: holds.length,
      scheduled_holds: 0,
      released_reports: 0,
      staged_reports: Object.keys(accessions).length,
      interface_live: false,
      interfaces: "SIMULATED",
      autonomous_release: false,
      compliance_decision: false,
      production_writes: 0,
      pre_sale_transport: "NONE",
      official_binary: "python3 test_csanalytical_expansion_crossline.py"
    };
  }

  function passContract(result) {
    var failures = [];
    Object.keys(GOLDEN_COUNTS).forEach(function (key) {
      if (result[key] !== GOLDEN_COUNTS[key]) failures.push(key);
    });
    if (result.interface_live !== false) failures.push("interface_live");
    if (result.autonomous_release !== false) failures.push("autonomous_release");
    if (result.compliance_decision !== false) failures.push("compliance_decision");
    return failures;
  }

  return {
    DEMAND_ID: DEMAND_ID,
    GOLDEN_COUNTS: GOLDEN_COUNTS,
    buildAcceptanceFixture: buildAcceptanceFixture,
    runGate: runGate,
    passContract: passContract
  };
});
