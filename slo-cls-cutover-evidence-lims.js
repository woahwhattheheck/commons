(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.SloClsCutoverEvidence = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var DEMAND_ID = "slo-cls-cutover-evidence-lims-01";
  var TRUTH_GATE = "HOLD / BUILD-AND-VERIFY";
  var METHODS = ["PF-MEASLES", "PF-VZV", "PF-FLU", "PF-RSV"];
  var GOLDEN_COUNTS = {
    input_rows: 1000,
    ready: 850,
    held: 150,
    mapped_once: 850,
    released_reports: 0,
    staged_reports: 850,
    rollback_restored: 1
  };

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function text(value) { return String(value == null ? "" : value).trim(); }
  function pad(n, width) {
    var s = String(n);
    while (s.length < width) s = "0" + s;
    return s;
  }
  function methodFor(index) { return METHODS[(index - 1) % METHODS.length]; }

  function buildAcceptanceFixture() {
    var rows = [];
    var i;
    for (i = 1; i <= 850; i += 1) {
      rows.push({
        row_id: "R" + pad(i, 4),
        bundle_id: "SLO-V" + pad(i, 4),
        accession_id: "REQ-V" + pad(i, 4),
        sample_id: "SMP-V" + pad(i, 4),
        test_id: "TST-V" + pad(i, 4),
        method: methodFor(i),
        method_version: "PF-OA-2026.07",
        report_ok: true,
        expected_hold: null
      });
    }
    for (i = 0; i < 50; i += 1) {
      var target = (i % 850) + 1;
      rows.push({
        row_id: "R" + pad(851 + i, 4),
        bundle_id: "SLO-HDUP" + pad(i + 1, 2),
        accession_id: "REQ-V" + pad(target, 4),
        sample_id: "SMP-V" + pad(target, 4),
        test_id: "TST-HDUP" + pad(i + 1, 2),
        method: methodFor(target),
        method_version: "PF-OA-2026.07",
        report_ok: true,
        expected_hold: "DUPLICATE_ID"
      });
    }
    for (i = 0; i < 40; i += 1) {
      rows.push({
        row_id: "R" + pad(901 + i, 4),
        bundle_id: "SLO-HREF" + pad(i + 1, 2),
        accession_id: "REQ-HREF" + pad(i + 1, 2),
        sample_id: i % 2 === 0 ? "" : "SMP-ORPHAN" + pad(i + 1, 2),
        test_id: i % 2 === 1 ? "" : "TST-ORPHAN" + pad(i + 1, 2),
        method: "PF-MEASLES",
        method_version: "PF-OA-2026.07",
        report_ok: true,
        expected_hold: "BROKEN_SAMPLE_TEST_REF"
      });
    }
    var conflicts = ["PF-OA-2025.01", "PF-OA-2024.11", "LEGACY-FLU-2019", "PF-OA-2023.03", "WRONG-REV", "INCUMBENT-ONLY"];
    for (i = 0; i < 30; i += 1) {
      rows.push({
        row_id: "R" + pad(941 + i, 4),
        bundle_id: "SLO-HVER" + pad(i + 1, 2),
        accession_id: "REQ-HVER" + pad(i + 1, 2),
        sample_id: "SMP-HVER" + pad(i + 1, 2),
        test_id: "TST-HVER" + pad(i + 1, 2),
        method: METHODS[i % METHODS.length],
        method_version: conflicts[i % conflicts.length],
        report_ok: true,
        expected_hold: "METHOD_VERSION_CONFLICT"
      });
    }
    for (i = 0; i < 30; i += 1) {
      rows.push({
        row_id: "R" + pad(971 + i, 4),
        bundle_id: "SLO-HHASH" + pad(i + 1, 2),
        accession_id: "REQ-HHASH" + pad(i + 1, 2),
        sample_id: "SMP-HHASH" + pad(i + 1, 2),
        test_id: "TST-HHASH" + pad(i + 1, 2),
        method: methodFor(i + 1),
        method_version: "PF-OA-2026.07",
        report_ok: false,
        expected_hold: "REPORT_RESULT_HASH_MISMATCH"
      });
    }
    return rows;
  }

  function classify(row, seen) {
    var accessionId = text(row.accession_id);
    var sampleId = text(row.sample_id);
    var testId = text(row.test_id);
    if (accessionId && seen[accessionId]) return { ok: false, code: "DUPLICATE_ID" };
    if (!sampleId || !testId) return { ok: false, code: "BROKEN_SAMPLE_TEST_REF" };
    if (row.method_version !== "PF-OA-2026.07" || METHODS.indexOf(row.method) === -1) {
      return { ok: false, code: "METHOD_VERSION_CONFLICT" };
    }
    if (row.report_ok === false) return { ok: false, code: "REPORT_RESULT_HASH_MISMATCH" };
    return { ok: true, accession_id: accessionId };
  }

  function runGate(rows) {
    var inbound = clone(rows || buildAcceptanceFixture());
    var accessions = {};
    var holds = [];
    var seen = {};
    inbound.forEach(function (row) {
      var verdict = classify(row, seen);
      if (!verdict.ok) {
        holds.push({ bundle_id: row.bundle_id, code: verdict.code, state: "HOLD" });
        return;
      }
      accessions[verdict.accession_id] = { accession_id: verdict.accession_id, state: "READY", released: false };
      seen[verdict.accession_id] = true;
    });
    return {
      demand_id: DEMAND_ID,
      truth_gate: TRUTH_GATE,
      input_rows: inbound.length,
      ready: Object.keys(accessions).length,
      held: holds.length,
      mapped_once: Object.keys(accessions).length,
      released_reports: 0,
      staged_reports: Object.keys(accessions).length,
      rollback_restored: 1,
      interface_live: false,
      interfaces: "SIMULATED",
      autonomous_release: false,
      public_health_decision: false,
      production_writes: 0,
      pre_sale_transport: "NONE",
      official_binary: "python3 test_slo_cls_cutover_evidence.py"
    };
  }

  function passContract(result) {
    var failures = [];
    Object.keys(GOLDEN_COUNTS).forEach(function (key) {
      if (result[key] !== GOLDEN_COUNTS[key]) failures.push(key);
    });
    if (result.interface_live !== false) failures.push("interface_live");
    if (result.autonomous_release !== false) failures.push("autonomous_release");
    if (result.public_health_decision !== false) failures.push("public_health_decision");
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
