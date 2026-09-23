"use strict";

const $ = (id) => document.getElementById(id);
const SIDES = ["source", "target"];
const MAX_FILE_BYTES = 4000000;
const PAGE_SIZE = 50;
const loaded = {source: null, target: null};
const loadSequence = {source: 0, target: 0};
let generation = 0;
let busy = false;
let rows = [];
let page = 0;
let downloadUrls = [];

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function status(message, error = false) {
  $("status").textContent = message;
  $("status").classList.toggle("error", error);
}

function discardResults() {
  generation += 1;
  downloadUrls.forEach((url) => URL.revokeObjectURL(url));
  downloadUrls = [];
  ["download-manifest", "download-report", "download-markdown", "download-html"].forEach((id) => {
    $(id).removeAttribute("href");
    $(id).removeAttribute("download");
  });
  rows = [];
  page = 0;
  $("results").hidden = true;
  $("row-body").replaceChildren();
  $("metrics").replaceChildren();
  $("result-state").textContent = "";
  $("report-meta").textContent = "";
}

function changed() {
  const hadResult = !$("results").hidden;
  discardResults();
  if (hadResult) status("Inputs changed. Compare again to produce a report for the new inputs.");
}

function ready() {
  return SIDES.every((side) => loaded[side] !== null);
}

function updateControls() {
  $("compare").disabled = busy || !ready();
  $("compare").textContent = busy ? "Comparing…" : "Compare exports";
  for (const kind of ["key", "field"]) {
    const children = Array.from($(`${kind}-map`).children);
    $(`add-${kind}`).disabled = !ready() || children.length >= (kind === "key" ? 4 : 32);
    children.forEach((row) => {
      row.querySelector("button").disabled = children.length <= 1;
      row.querySelectorAll("select").forEach((select) => { select.disabled = !ready(); });
    });
  }
}

async function api(path, payload) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch(path, {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload), signal: controller.signal, cache: "no-store",
    });
    let result;
    try { result = await response.json(); }
    catch (_) { throw new Error(`Server returned an unreadable response (HTTP ${response.status}).`); }
    if (!response.ok) throw new Error(result.error || `Request failed (HTTP ${response.status}).`);
    return result;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("Request timed out. Check the local server and try again.");
    throw error;
  } finally { clearTimeout(timer); }
}

function mappingSelect(caption, options, placeholder) {
  const label = element("label", caption);
  const select = document.createElement("select");
  select.required = true;
  if (placeholder) {
    const first = element("option", placeholder);
    first.value = "";
    select.append(first);
  }
  for (const value of options) {
    const option = element("option", value);
    option.value = value;
    select.append(option);
  }
  label.append(select);
  return label;
}

function addMapping(kind) {
  const container = $(`${kind}-map`);
  if (container.children.length >= (kind === "key" ? 4 : 32)) return;
  const row = element("div", undefined, "mapping-row");
  row.append(
    mappingSelect("Source field", loaded.source?.columns || [], "Choose source field"),
    mappingSelect("Target field", loaded.target?.columns || [], "Choose target field"),
    mappingSelect("Type", kind === "key" ? ["string", "integer"] : ["string", "integer", "boolean"]),
  );
  const remove = element("button", "Remove");
  remove.type = "button";
  remove.setAttribute("aria-label", `Remove ${kind} mapping`);
  remove.addEventListener("click", () => { row.remove(); changed(); updateControls(); });
  row.append(remove);
  container.append(row);
  updateControls();
}

function resetMappings() {
  for (const kind of ["key", "field"]) {
    $(`${kind}-map`).replaceChildren();
    addMapping(kind);
  }
}

async function loadExport(side, newFile) {
  const sequence = ++loadSequence[side];
  changed();
  loaded[side] = null;
  $(`${side}-columns`).replaceChildren();
  if (newFile) {
    $(`${side}-captured`).value = "";
    $(`${side}-complete`).checked = false;
  }
  resetMappings();
  updateControls();
  const file = $(`${side}-file`).files[0];
  if (!file) {
    $(`${side}-preview`).textContent = "No export loaded.";
    status("Load both exports to begin.");
    return;
  }
  if (newFile && /\.(csv|json)$/i.test(file.name)) {
    $(`${side}-format`).value = file.name.toLowerCase().endsWith(".json") ? "json" : "csv";
  }
  const format = $(`${side}-format`).value;
  $(`${side}-preview`).textContent = "Reading field names and record count…";
  try {
    if (file.size > MAX_FILE_BYTES) throw new Error(`Export exceeds ${MAX_FILE_BYTES.toLocaleString()} bytes; it was not truncated.`);
    // Preserve BOM characters for the server's explicit CSV/JSON handling and
    // reject invalid UTF-8 instead of silently inserting replacement characters.
    const text = new TextDecoder("utf-8", {fatal: true, ignoreBOM: true}).decode(await file.arrayBuffer());
    if (sequence !== loadSequence[side]) return;
    const preview = await api("/api/inspect", {format, text});
    if (sequence !== loadSequence[side]) return;
    loaded[side] = {format, text, columns: preview.columns};
    $(`${side}-preview`).textContent = `${preview.record_count} records · ${preview.columns.length} fields · ${file.size.toLocaleString()} bytes`;
    $(`${side}-columns`).replaceChildren(...preview.columns.map((name) => element("span", name, "field-chip")));
    resetMappings();
    status(ready() ? "Exports loaded. Declare capture times and choose key and compared-field mappings." : "Load the other export to continue.");
  } catch (error) {
    if (sequence !== loadSequence[side]) return;
    $(`${side}-preview`).textContent = "Export could not be loaded.";
    status(`${side}: ${error.message}`, true);
  } finally {
    if (sequence === loadSequence[side]) updateControls();
  }
}

function readMappings(kind) {
  return Array.from($(`${kind}-map`).children).map((row) => {
    const selects = row.querySelectorAll("select");
    return {source: selects[0].value, target: selects[1].value, type: selects[2].value};
  });
}

function intakeRequest() {
  const request = {
    cutover_at_utc: $("cutover").value,
    max_snapshot_age_seconds: Number($("max-age").value),
    key_map: readMappings("key"), field_map: readMappings("field"),
  };
  if (!Number.isSafeInteger(request.max_snapshot_age_seconds)) throw new Error("Maximum age must be a whole number of seconds.");
  for (const side of SIDES) {
    request[side] = {
      format: loaded[side].format, text: loaded[side].text,
      snapshot_id: $(`${side}-id`).value,
      schema_revision: $(`${side}-revision`).value,
      captured_at_utc: $(`${side}-captured`).value,
      complete: $(`${side}-complete`).checked,
    };
  }
  return request;
}

function download(id, filename, text, type) {
  const url = URL.createObjectURL(new Blob([text], {type}));
  downloadUrls.push(url);
  $(id).href = url;
  $(id).download = filename;
}

function renderRows() {
  const classification = $("classification-filter").value;
  const needle = $("key-filter").value.toLowerCase();
  const filtered = rows.filter((row) => {
    if (classification && row.classification !== classification) return false;
    const fields = row.mismatch_fields.map((field) => `${field.source_field} ${field.target_field}`).join(" ");
    return `${row.key_commitment} ${row.classification} ${fields} ${row.reason_codes.join(" ")}`.toLowerCase().includes(needle);
  });
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  page = Math.min(page, pages - 1);
  const body = $("row-body");
  body.replaceChildren();
  for (const row of filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)) {
    const tr = document.createElement("tr");
    const state = element("td");
    state.append(element("span", row.classification, `tag ${row.classification === "PARITY" ? "parity" : "attention"}`));
    const key = element("td");
    key.append(element("code", row.key_commitment));
    const detail = element("td");
    detail.append(element("p", row.reason_codes.length ? row.reason_codes.join(", ") : "Mapped fields match."));
    for (const mismatch of row.mismatch_fields) {
      const disclosure = document.createElement("details");
      disclosure.append(element("summary", `${mismatch.source_field} → ${mismatch.target_field}`));
      disclosure.append(element("p", "Source value digest"), element("code", mismatch.source_value_sha256));
      disclosure.append(element("p", "Target value digest"), element("code", mismatch.target_value_sha256));
      detail.append(disclosure);
    }
    tr.append(state, key, detail);
    body.append(tr);
  }
  if (!filtered.length) {
    const tr = document.createElement("tr");
    const cell = element("td", "No result rows match this filter.");
    cell.colSpan = 3;
    tr.append(cell);
    body.append(tr);
  }
  $("page-info").textContent = `${filtered.length} matching / ${rows.length} total keys · page ${page + 1} of ${pages}`;
  $("prev-page").disabled = page === 0;
  $("next-page").disabled = page + 1 >= pages;
}

function renderReport(result) {
  // Only the report (counts, metadata and hashes) is parsed for presentation.
  // The original canonical strings are used verbatim for every download.
  const report = JSON.parse(result.report_json);
  const counts = report.summary.counts;
  rows = report.rows;
  $("result-state").textContent = report.summary.diagnostic_state;
  $("report-meta").textContent = `Cutover ${report.cutover_at_utc} · source ${report.source_snapshot.record_count} records · target ${report.target_snapshot.record_count} records`;
  const metrics = [
    ["Union keys", report.summary.union_key_count], ["Parity", counts.PARITY],
    ["Missing / unexpected / changed", counts.MISSING_TARGET + counts.UNEXPECTED_TARGET + counts.FIELD_MISMATCH],
    ["Stale / duplicate / invalid", counts.STALE_EVIDENCE + counts.DUPLICATE_KEY + counts.INVALID_EVIDENCE],
  ];
  $("metrics").replaceChildren(...metrics.map(([label, value]) => {
    const card = element("div", undefined, "metric");
    card.append(element("strong", value), element("span", label));
    return card;
  }));
  download("download-manifest", "parity-input.json", result.manifest_json, "application/json;charset=utf-8");
  download("download-report", "parity-report.json", result.report_json, "application/json;charset=utf-8");
  download("download-markdown", "parity-report.md", result.report_markdown, "text/markdown;charset=utf-8");
  download("download-html", "parity-report.html", result.report_html, "text/html;charset=utf-8");
  const all = element("option", "All classifications");
  all.value = "";
  $("classification-filter").replaceChildren(all, ...Object.entries(counts).map(([name, count]) => {
    const option = element("option", `${name} (${count})`);
    option.value = name;
    return option;
  }));
  $("key-filter").value = "";
  page = 0;
  renderRows();
  $("results").hidden = false;
  $("report-title").focus();
}

$("intake").addEventListener("input", changed);
$("intake").addEventListener("change", changed);
$("intake").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy || !ready()) return;
  discardResults();
  const submittedGeneration = generation;
  busy = true;
  updateControls();
  status("Comparing the supplied exports…");
  try {
    const result = await api("/api/compare", intakeRequest());
    if (submittedGeneration !== generation) {
      status("Inputs changed during comparison. Compare again for the current inputs.");
      return;
    }
    renderReport(result);
    status("Comparison complete. Review the classifications and download the files you need.");
  } catch (error) {
    if (submittedGeneration === generation) status(error.message, true);
  } finally { busy = false; updateControls(); }
});
for (const side of SIDES) {
  $(`${side}-file`).addEventListener("change", () => loadExport(side, true));
  $(`${side}-format`).addEventListener("change", () => loadExport(side, false));
}
for (const kind of ["key", "field"]) {
  $(`add-${kind}`).addEventListener("click", () => { changed(); addMapping(kind); });
}
$("use-now").addEventListener("click", () => {
  changed();
  $("cutover").value = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
});
$("classification-filter").addEventListener("change", () => { page = 0; renderRows(); });
$("key-filter").addEventListener("input", () => { page = 0; renderRows(); });
$("prev-page").addEventListener("click", () => { page = Math.max(0, page - 1); renderRows(); });
$("next-page").addEventListener("click", () => { page += 1; renderRows(); });
$("clear-session").addEventListener("click", () => {
  discardResults();
  $("intake").reset();
  for (const side of SIDES) {
    loadSequence[side] += 1;
    loaded[side] = null;
    $(`${side}-preview`).textContent = "No export loaded.";
    $(`${side}-columns`).replaceChildren();
  }
  resetMappings();
  status("Session cleared. Files already downloaded are not deleted.");
  updateControls();
});
window.addEventListener("beforeunload", () => downloadUrls.forEach((url) => URL.revokeObjectURL(url)));
const portableDownload = element("a", "Download printable HTML", "download");
portableDownload.id = "download-html";
$("download-markdown").after(portableDownload);
resetMappings();
updateControls();
