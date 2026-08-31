(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.LuvakSsaLabAnalyticsCutover = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var DEMAND_ID = "luvak-ssa-lab-analytics-cutover-lims-01";
  var TRUTH_GATE = "HOLD / BUILD-AND-VERIFY";
  var METHODS = {
    INTERSTITIAL_O: "IGA-O-2024-SYN",
    INTERSTITIAL_N: "IGA-N-2024-SYN",
    INTERSTITIAL_H: "IGA-H-2024-SYN",
    METALS_ICP: "ICP-MS-2024-SYN"
  };
  var METHOD_NAMES = Object.keys(METHODS);
  var MISMATCH = [
    ["INTERSTITIAL_O", "IGA-O-2018-LEGACY"],
    ["INTERSTITIAL_N", "IGA-N-WRONG"],
    ["INTERSTITIAL_H", "SSA-DRAFT"],
    ["METALS_ICP", "ICP-2011"]
  ];
  var GOLDEN_COUNTS = {
    input_rows: 100, ready: 80, held: 20, held_test_stages: 0,
    released_reports: 0, staged_reports: 80
  };

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function text(value) { return String(value == null ? "" : value).trim(); }
  function pad(n, width) {
    var s = String(n);
    while (s.length < width) s = "0" + s;
    return s;
  }
  function methodFor(index) { return METHOD_NAMES[(index - 1) % METHOD_NAMES.length]; }

  function buildAcceptanceFixture() {
    var rows = [];
    var i;
    for (i = 1; i <= 80; i += 1) {
      var method = methodFor(i);
      rows.push({
        row_id: "R" + pad(i, 3),
        sample_id: "LVK-SMP-" + pad(i, 3),
        quote_id: "LVK-Q-" + pad(i, 3),
        form_id: "FORM-" + pad(i, 3),
        package_id: "PKG-" + pad(i, 3),
        form_package_id: "PKG-" + pad(i, 3),
        method: method,
        method_version: METHODS[method],
        expected_hold: null
      });
    }
    for (i = 0; i < 8; i += 1) {
      rows.push({
        row_id: "R" + pad(81 + i, 3),
        sample_id: "LVK-SMP-HQ" + pad(i + 1, 2),
        quote_id: "",
        form_id: "FORM-HQ" + pad(i + 1, 2),
        package_id: "PKG-HQ" + pad(i + 1, 2),
        form_package_id: "PKG-HQ" + pad(i + 1, 2),
        method: "INTERSTITIAL_O",
        method_version: METHODS.INTERSTITIAL_O,
        expected_hold: "MISSING_ACCEPTED_QUOTE"
      });
    }
    for (i = 0; i < 4; i += 1) {
      rows.push({
        row_id: "R" + pad(89 + i, 3),
        sample_id: "LVK-SMP-" + pad(i + 1, 3),
        quote_id: "LVK-Q-HDUP" + pad(i + 1, 2),
        form_id: "FORM-HDUP" + pad(i + 1, 2),
        package_id: "PKG-HDUP" + pad(i + 1, 2),
        form_package_id: "PKG-HDUP" + pad(i + 1, 2),
        method: methodFor(i + 1),
        method_version: METHODS[methodFor(i + 1)],
        expected_hold: "DUPLICATE_SAMPLE_ID"
      });
    }
    for (i = 0; i < 4; i += 1) {
      rows.push({
        row_id: "R" + pad(93 + i, 3),
        sample_id: "LVK-SMP-HFP" + pad(i + 1, 2),
        quote_id: "LVK-Q-HFP" + pad(i + 1, 2),
        form_id: "FORM-HFP" + pad(i + 1, 2),
        package_id: "PKG-HFP" + pad(i + 1, 2),
        form_package_id: "PKG-OTHER" + pad(i + 1, 2),
        method: "METALS_ICP",
        method_version: METHODS.METALS_ICP,
        expected_hold: "FORM_PACKAGE_MISMATCH"
      });
    }
    for (i = 0; i < 4; i += 1) {
      rows.push({
        row_id: "R" + pad(97 + i, 3),
        sample_id: "LVK-SMP-HREV" + pad(i + 1, 2),
        quote_id: "LVK-Q-HREV" + pad(i + 1, 2),
        form_id: "FORM-HREV" + pad(i + 1, 2),
        package_id: "PKG-HREV" + pad(i + 1, 2),
        form_package_id: "PKG-HREV" + pad(i + 1, 2),
        method: MISMATCH[i][0],
        method_version: MISMATCH[i][1],
        expected_hold: "METHOD_REVISION_MISMATCH"
      });
    }
    return rows;
  }

  function classify(row, seen) {
    var sampleId = text(row.sample_id);
    var quoteId = text(row.quote_id);
    if (!quoteId) return { ok: false, code: "MISSING_ACCEPTED_QUOTE" };
    if (sampleId && seen[sampleId]) return { ok: false, code: "DUPLICATE_SAMPLE_ID" };
    if (!text(row.form_id) || !text(row.package_id) || text(row.form_package_id) !== text(row.package_id)) {
      return { ok: false, code: "FORM_PACKAGE_MISMATCH" };
    }
    if (!METHODS[row.method] || METHODS[row.method] !== row.method_version) {
      return { ok: false, code: "METHOD_REVISION_MISMATCH" };
    }
    return { ok: true, sample_id: sampleId };
  }

  function runGate(rows) {
    var inbound = clone(rows || buildAcceptanceFixture());
    var accessions = {};
    var holds = [];
    var seen = {};
    inbound.forEach(function (row) {
      var verdict = classify(row, seen);
      if (!verdict.ok) {
        holds.push({ sample_id: row.sample_id || null, code: verdict.code, state: "HOLD", test_stage: null });
        return;
      }
      accessions[verdict.sample_id] = { sample_id: verdict.sample_id, state: "READY", released: false };
      seen[verdict.sample_id] = true;
    });
    return {
      demand_id: DEMAND_ID,
      truth_gate: TRUTH_GATE,
      input_rows: inbound.length,
      ready: Object.keys(accessions).length,
      held: holds.length,
      held_test_stages: 0,
      released_reports: 0,
      staged_reports: Object.keys(accessions).length,
      interface_live: false,
      interfaces: "SIMULATED",
      autonomous_release: false,
      materials_qualification_decision: false,
      production_writes: 0,
      pre_sale_transport: "NONE",
      official_binary: "python3 test_luvak_ssa_lab_analytics_cutover.py"
    };
  }

  function passContract(result) {
    var failures = [];
    Object.keys(GOLDEN_COUNTS).forEach(function (key) {
      if (result[key] !== GOLDEN_COUNTS[key]) failures.push(key);
    });
    if (result.interface_live !== false) failures.push("interface_live");
    if (result.autonomous_release !== false) failures.push("autonomous_release");
    if (result.materials_qualification_decision !== false) failures.push("materials_qualification_decision");
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
