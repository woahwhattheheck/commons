"use strict";
const $ = id => document.getElementById(id);
let key = "", epoch = 0, commands = {}, route = null, busy = false, routeRequest = 0;
const keyName = "laundry-console-session-key";
const labels = {operation_key:"Operation key", customer_id:"Customer ID", site_id:"Site ID",
  agreement_id:"Price agreement ID", item_code:"Item code", unit_price_cents:"Unit price in cents",
  active_from:"Active from", active_to:"Active through (optional)", plan_id:"Plan ID",
  route_code:"Route code", weekday:"Weekday (Monday 0 to Sunday 6)", stop_sequence:"Stop sequence",
  service_date:"Service date", stop_id:"Stop ID", linen_counts:"Picked-up counts",
  processed_counts:"Processed-good counts", damaged_counts:"Damaged counts (optional)",
  delivered_counts:"Delivered counts", container_ids:"Container IDs", exception_id:"Exception ID",
  resolution_code:"Resolution code", note:"Supported disposition note", name:"Name"};
function savedKey(value) {
  try {
    if (value === undefined) return sessionStorage.getItem(keyName);
    if (value === null) sessionStorage.removeItem(keyName); else sessionStorage.setItem(keyName, value);
  } catch (_) { /* Private browsing may disable storage; the in-memory session still works. */ }
  return null;
}
const newKey = () => "console." + crypto.randomUUID();
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}
function status(id, message, error=false) {
  $(id).textContent = message;
  $(id).className = "status " + (error ? "error" : "success");
}
async function request(path, options={}, download=false) {
  const generation = epoch;
  const response = await fetch(path, {...options, credentials:"omit", cache:"no-store",
    headers:{Authorization:"Bearer " + key, ...(options.headers || {})}});
  const data = response.ok && download ? await response.blob() : await response.json();
  if (generation !== epoch) throw new Error("The console session changed. Reopen the current workspace.");
  if (!response.ok) throw new Error(data.message || "Local request failed.");
  return data;
}
function datalist(id, rows, field, description) {
  $(id).replaceChildren(...rows.map(row => {
    const option = element("option"); option.value = row[field]; option.label = description(row); return option;
  }));
}
function renderFields() {
  const spec = commands[$("command").value];
  const fields = $("fields"); fields.replaceChildren();
  for (const [name, type] of Object.entries({...spec.required, ...spec.optional})) {
    const label = element("label", labels[name] || name); label.htmlFor = "field-" + name;
    const input = element(type === "dict" || type === "list" ? "textarea" : "input");
    input.id = "field-" + name; input.name = name; input.required = Object.hasOwn(spec.required, name);
    input.dataset.kind = type;
    if (type === "int") { input.type = "number"; input.step = "1"; input.min = "0";
      if (name === "weekday") input.max = "6";
    } else if (name.includes("active_") || name === "service_date") input.type = "date";
    if (type === "dict") input.placeholder = "towel=3\nsheet=2";
    if (type === "list") input.placeholder = "bag-001\nbag-002";
    if (name === "operation_key") input.value = newKey();
    const lists = {customer_id:"customer-options", site_id:"site-options", stop_id:"stop-options"};
    if (lists[name]) input.setAttribute("list", lists[name]);
    label.append(input);
    if (type === "dict" || type === "list") label.append(element("small", type === "dict"
      ? "One item=count per line. Enter observed counts, including zero where appropriate."
      : "One observed container ID per line."));
    fields.append(label);
  }
  status("operation-status", "");
}
function payloadFromForm() {
  const payload = {};
  for (const input of $("fields").querySelectorAll("input, textarea")) {
    const raw = input.value;
    if (!input.required && raw === "") continue;
    const type = input.dataset.kind;
    if (type === "int") {
      if (!/^[0-9]+$/.test(raw) || !Number.isSafeInteger(Number(raw))) throw new Error("Enter a whole-number " + labels[input.name] + ".");
      payload[input.name] = Number(raw);
    } else if (type === "dict") {
      const counts = Object.create(null);
      for (const line of raw.split(/\r?\n/).filter(line => line.trim())) {
        const parts = line.split("=").map(part => part.trim());
        if (parts.length !== 2 || !parts[0] || !/^[0-9]+$/.test(parts[1])
            || !Number.isSafeInteger(Number(parts[1])) || Object.hasOwn(counts, parts[0]))
          throw new Error("Counts need unique item=whole-number lines; nothing was sent.");
        counts[parts[0]] = Number(parts[1]);
      }
      payload[input.name] = counts;
    } else if (type === "list") payload[input.name] = raw.split(/\r?\n/).map(value => value.trim()).filter(Boolean);
    else payload[input.name] = raw;
  }
  return payload;
}
function setBusy(value) {
  busy = value;
  for (const control of $("operation-form").elements) control.disabled = value;
  $("lock").disabled = value;
  for (const button of $("stops").querySelectorAll("button")) button.disabled = value;
}
function prepare(action, field, value) {
  if (busy) return;
  $("command").value = action; renderFields(); $("field-" + field).value = value;
  $("operation-form").scrollIntoView({behavior:"smooth", block:"start"});
  $("field-" + field).focus();
}
async function refresh() {
  const data = await request("/api/overview");
  $("customer-count").textContent = data.counts.customers;
  $("route-count").textContent = data.counts.routes;
  $("exception-count").textContent = data.counts.open_exceptions;
  datalist("route-options", data.routes, "route_id", r => r.service_date + " · " + r.state);
  datalist("customer-options", data.customers, "customer_id", r => r.name);
  datalist("site-options", data.sites, "site_id", r => r.name);
  $("list-note").textContent = `Pickers show at most ${data.list_limit} records each. Older exact IDs can be entered directly.`;
}
function clearRoute() {
  route = null; $("stops").replaceChildren(); $("stop-options").replaceChildren();
  $("route-summary").textContent = "No current route loaded. Open an exact route ID.";
}
async function loadRoute() {
  const sequence = ++routeRequest;
  clearRoute();
  const id = $("route-id").value;
  if (!id) throw new Error("Select or enter an exact route ID.");
  const loaded = await request("/api/route?id=" + encodeURIComponent(id));
  if (sequence !== routeRequest || id !== $("route-id").value) return;
  route = loaded;
  $("route-summary").textContent = `${route.service_date} · ${route.route_code} · ${route.state} · ${route.stops.length} stops`;
  datalist("stop-options", route.stops, "stop_id", s => s.site_name);
  $("stops").replaceChildren();
  for (const stop of route.stops) {
    const card = element("article", undefined, "stop");
    const heading = element("div", undefined, "stop-head");
    heading.append(element("h3", `${stop.sequence} · ${stop.customer_name} / ${stop.site_name}`), element("span", stop.state, "chip"));
    card.append(heading, element("p", stop.stop_id, "mono"));
    const scroll = element("div", undefined, "table-scroll"), table = element("table"), head = element("tr");
    for (const name of ["Item", "Pickup", "Good", "Damage", "Delivered"]) head.append(element("th", name));
    const thead = element("thead"); thead.append(head); table.append(thead);
    const body = element("tbody"), phases = ["pickup_counts", "processed_counts", "damaged_counts", "delivered_counts"];
    const items = [...new Set(phases.flatMap(phase => Object.keys(stop[phase])))].sort();
    for (const item of items) {
      const row = element("tr"); row.append(element("th", item));
      for (const phase of phases) row.append(element("td", Object.hasOwn(stop[phase], item) ? stop[phase][item] : "—"));
      body.append(row);
    }
    table.append(body); scroll.append(table); card.append(scroll);
    card.append(element("p", "Pickup containers: " + (stop.pickup_containers.join(", ") || "Not recorded"), "subtle"),
      element("p", "Delivered containers: " + (stop.delivery_containers.join(", ") || "Not recorded"), "subtle"));
    for (const exception of stop.exceptions) {
      const box = element("div", undefined, "exception");
      box.append(element("strong", `${exception.kind} · ${exception.status}`), element("p", `${exception.item_code}: expected ${exception.expected_qty}, observed ${exception.actual_qty}`), element("p", exception.exception_id, "mono"));
      if (exception.status === "OPEN") {
        const button = element("button", "Review and resolve", "secondary"); button.disabled = busy;
        button.addEventListener("click", () => prepare("resolve", "exception_id", exception.exception_id)); box.append(button);
      } else box.append(element("p", `${exception.resolution_code}: ${exception.resolution_note}`));
      card.append(box);
    }
    if (stop.invoice) card.append(element("div", `DRAFT · USD ${(stop.invoice.total_cents / 100).toFixed(2)} · not issued or paid`, "draft"));
    const next = {MANIFESTED:"pickup", PICKED_UP:"process", PROCESSED:"deliver", DELIVERED:"invoice-draft"}[stop.state];
    if (next) {
      const button = element("button", "Prepare " + next.replace("-", " "), "secondary"); button.disabled = busy;
      button.addEventListener("click", () => prepare(next, "stop_id", stop.stop_id)); card.append(button);
    }
    $("stops").append(card);
  }
  status("route-status", "Current route loaded. Review all open exceptions before drafting.");
}
async function download(kind) {
  const id = $(kind === "route" ? "route-id" : "export-customer-id").value;
  if (!id) throw new Error("Enter the exact " + kind + " ID first.");
  const format = $(kind + "-format").value;
  const query = new URLSearchParams({kind, id, format});
  const blob = await request("/api/export?" + query, {}, true);
  const link = element("a"); link.href = URL.createObjectURL(blob);
  link.download = `laundry-${kind}.${format === "markdown" ? "md" : format}`;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  status("route-status", "Downloaded native " + kind + " " + format + ". Nothing was sent to a customer.");
}
function lock() {
  epoch++; routeRequest++; key = ""; savedKey(null); clearRoute();
  $("workspace").hidden = true; $("lock").hidden = true; $("unlock-panel").hidden = false;
  $("fields").replaceChildren(); $("stops").replaceChildren(); $("receipt").textContent = "";
  for (const id of ["route-options", "customer-options", "site-options"]) $(id).replaceChildren();
  for (const id of ["customer-count", "route-count", "exception-count"]) $(id).textContent = "0";
  $("route-id").value = ""; $("export-customer-id").value = "";
  status("route-status", ""); status("operation-status", "");
  $("session-key").value = ""; $("session-key").focus();
}
async function unlock(value) {
  epoch++; key = value;
  try {
    commands = (await request("/api/config")).commands;
    await refresh(); renderFields(); savedKey(key);
    $("unlock-panel").hidden = true; $("workspace").hidden = false; $("lock").hidden = false;
    $("session-key").value = "";
  } catch (error) { lock(); status("unlock-status", error.message, true); }
}
$("unlock-form").addEventListener("submit", event => { event.preventDefault(); unlock($("session-key").value.trim()); });
$("lock").addEventListener("click", lock);
$("command").addEventListener("change", renderFields);
$("new-key").addEventListener("click", () => { $("field-operation_key").value = newKey(); status("operation-status", "New key selected. This is a new operation, not a retry."); });
$("operation-form").addEventListener("submit", async event => {
  event.preventDefault(); if (busy) return;
  try {
    const action = $("command").value, payload = payloadFromForm(); setBusy(true);
    status("operation-status", "Recording locally. Keep this key until the result is known.");
    const result = await request("/api/operations/" + action, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
    $("receipt").textContent = JSON.stringify(result, null, 2);
    status("operation-status", `${result.status} · ${result.operation_key}. This key remains available for an exact replay.`);
    if (action === "manifest") $("route-id").value = result.result.route_id;
    try { await refresh(); if ($("route-id").value) await loadRoute(); }
    catch (error) { status("route-status", "Operation acknowledged; refreshing the view failed: " + error.message, true); }
  } catch (error) { status("operation-status", error.message + " Keep the same key and fields for a retry.", true); }
  finally { setBusy(false); }
});
for (const [id, action] of [["open-route", loadRoute], ["refresh", async () => { await refresh(); if ($("route-id").value) await loadRoute(); }], ["export-route", () => download("route")], ["export-customer", () => download("customer")]]) {
  $(id).addEventListener("click", () => action().catch(error => { status("route-status", error.message, true); }));
}
$("route-id").addEventListener("input", () => { routeRequest++; clearRoute(); });
const incoming = new URLSearchParams(location.hash.slice(1)).get("key");
if (location.hash) history.replaceState(null, "", location.pathname);
const initial = incoming || savedKey();
if (initial) unlock(initial);
