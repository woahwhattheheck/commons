(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.TwoSourceReconciler = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  var VERSION = "two-source-reconciler/v1";

  function plainObject(value, label) {
    if (!value || typeof value !== "object" || Array.isArray(value)) throw new TypeError(label + " must be an object");
    return value;
  }
  function requiredText(value, label) {
    if (typeof value !== "string" || !value.trim()) throw new TypeError(label + " must be a non-empty string");
    return value.trim();
  }
  function safeInteger(value, label) {
    if (!Number.isSafeInteger(value)) throw new TypeError(label + " must be a safe integer");
    return value;
  }
  function normalizeFields(fields) {
    if (!Array.isArray(fields) || fields.length === 0) throw new TypeError("fields must be a non-empty array");
    var seen = Object.create(null);
    return fields.map(function (field, index) {
      field = requiredText(field, "fields[" + index + "]");
      if (seen[field]) throw new TypeError("duplicate field: " + field);
      seen[field] = true;
      return field;
    });
  }
  function normalizeRow(row, side, index, fields) {
    plainObject(row, side + "[" + index + "]");
    var values = plainObject(row.values, side + "[" + index + "].values");
    var normalized = {
      rowId: requiredText(row.rowId, side + "[" + index + "].rowId"),
      key: requiredText(row.key, side + "[" + index + "].key"),
      values: {}
    };
    fields.forEach(function (field) {
      normalized.values[field] = safeInteger(values[field], side + "[" + index + "].values." + field);
    });
    return normalized;
  }
  function group(rows) {
    var out = Object.create(null);
    rows.forEach(function (row) {
      if (!out[row.key]) out[row.key] = [];
      out[row.key].push(row);
    });
    return out;
  }
  function sums(rows, fields) {
    var out = {};
    fields.forEach(function (field) { out[field] = 0; });
    rows.forEach(function (row) {
      fields.forEach(function (field) { out[field] += row.values[field]; });
    });
    return out;
  }
  function reconcile(input) {
    plainObject(input, "input");
    var fields = normalizeFields(input.fields);
    if (!Array.isArray(input.left)) throw new TypeError("left must be an array");
    if (!Array.isArray(input.right)) throw new TypeError("right must be an array");
    var left = input.left.map(function (row, index) { return normalizeRow(row, "left", index, fields); });
    var right = input.right.map(function (row, index) { return normalizeRow(row, "right", index, fields); });
    var lg = group(left), rg = group(right);
    var keys = Object.keys(lg).concat(Object.keys(rg).filter(function (key) { return !lg[key]; })).sort();
    var rows = keys.map(function (key) {
      var ls = lg[key] || [], rs = rg[key] || [], issues = [], delta = {};
      if (ls.length === 0) issues.push("MISSING_LEFT");
      if (rs.length === 0) issues.push("MISSING_RIGHT");
      if (ls.length > 1) issues.push("DUPLICATE_LEFT");
      if (rs.length > 1) issues.push("DUPLICATE_RIGHT");
      if (ls.length === 1 && rs.length === 1) {
        fields.forEach(function (field) {
          delta[field] = ls[0].values[field] - rs[0].values[field];
          if (delta[field] !== 0) issues.push("MISMATCH:" + field);
        });
      }
      return {
        key: key,
        state: issues.length === 0 ? "MATCH" : "REVIEW",
        issues: issues,
        leftRows: ls.map(function (row) { return row.rowId; }),
        rightRows: rs.map(function (row) { return row.rowId; }),
        delta: delta
      };
    });
    var leftTotals = sums(left, fields), rightTotals = sums(right, fields), deltaTotals = {};
    fields.forEach(function (field) { deltaTotals[field] = leftTotals[field] - rightTotals[field]; });
    return {
      schemaVersion: VERSION,
      fields: fields,
      summary: {
        match: rows.filter(function (row) { return row.state === "MATCH"; }).length,
        review: rows.filter(function (row) { return row.state === "REVIEW"; }).length,
        keys: rows.length,
        leftRows: left.length,
        rightRows: right.length
      },
      totals: { left: leftTotals, right: rightTotals, delta: deltaTotals },
      rows: rows
    };
  }
  return { VERSION: VERSION, reconcile: reconcile };
});
