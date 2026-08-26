(function () {
  "use strict";
  var data;
  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) {
      return ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c];
    });
  }
  function amount(component, quantity) {
    var kind = component.kind, q = Number(quantity || 0), total = 0;
    if (["fixed", "subscription", "milestone", "license"].indexOf(kind) >= 0) total = Number(component.amount || 0) * q;
    else if (["usage", "outcome", "sponsorship"].indexOf(kind) >= 0) total = Number(component.unit_amount || 0) * Math.max(0, q - Number(component.included || 0));
    else if (kind === "take_rate") total = q * Number(component.rate_bps || 0) / 10000;
    return total;
  }
  function componentText(c) {
    if (c.amount != null) return "$" + Number(c.amount).toLocaleString() + " " + c.kind;
    if (c.unit_amount != null) return "$" + c.unit_amount + "/" + esc(c.meter || "unit") + " " + c.kind;
    if (c.rate_bps != null) return (Number(c.rate_bps) / 100).toFixed(2) + "% " + c.kind;
    return c.kind;
  }
  function renderCatalog() {
    document.getElementById("catalog-status").textContent = data.listings.length + " adapters; source terms remain canonical.";
    document.getElementById("catalog").innerHTML = data.listings.map(function (row) {
      return '<article class="card"><p class="state-' + esc(row.state) + '"><b>' + esc(row.state) + '</b></p><h3>' + esc(row.name) + '</h3>' +
        '<p class="money">' + row.pricing.components.map(componentText).join(" + ") + ' ' + esc(row.pricing.currency) + '</p>' +
        '<p>' + row.pricing.components.map(function(c){return '<span class="pill">' + esc(c.kind) + '</span>';}).join("") + '</p>' +
        '<p class="note">terms: <code>' + esc(row.source.path) + "#" + esc(row.source.pointer) + '</code></p>' +
        '<p><a href="./' + esc(row.routes.human) + '">human door</a> · <a href="./' + esc(row.routes.machine) + '">machine source</a></p></article>';
    }).join("");
  }
  function renderMetrics() {
    var id = document.getElementById("listing").value;
    var row = data.listings.filter(function (x) { return x.id === id; })[0];
    var host = document.getElementById("metrics");
    host.innerHTML = row.pricing.components.map(function (c) {
      var initial = ["fixed", "milestone", "license"].indexOf(c.kind) >= 0 ? "1" : "0";
      var label = c.kind === "take_rate" ? "gross amount" : (c.meter || c.basis || "quantity");
      return '<label>' + esc(c.id) + ' · ' + esc(c.kind) + ' · ' + esc(label) + '<input type="number" min="0" step="any" value="' + initial + '" data-component="' + esc(c.id) + '"></label>';
    }).join("");
    Array.prototype.forEach.call(host.querySelectorAll("input"), function (input) { input.addEventListener("input", calculate); });
    calculate();
  }
  function calculate() {
    var id = document.getElementById("listing").value;
    var row = data.listings.filter(function (x) { return x.id === id; })[0];
    var values = {};
    Array.prototype.forEach.call(document.querySelectorAll("#metrics input"), function (input) { values[input.getAttribute("data-component")] = input.value; });
    var total = row.pricing.components.reduce(function (sum, c) { return sum + amount(c, values[c.id]); }, 0);
    document.getElementById("total").textContent = total.toLocaleString(undefined, {style:"currency", currency:row.pricing.currency, minimumFractionDigits:2});
    document.getElementById("quote-state").textContent = "QUOTED · " + row.state + " · not authorized, settled, paid out, or bank-available";
  }
  fetch("./revenue/outcome_commerce/catalog.json?v=" + Date.now(), {cache:"no-store"}).then(function (response) {
    if (!response.ok) throw new Error(String(response.status));
    return response.json();
  }).then(function (catalog) {
    data = catalog;
    renderCatalog();
    var select = document.getElementById("listing");
    select.innerHTML = data.listings.map(function (row) { return '<option value="' + esc(row.id) + '">' + esc(row.name) + '</option>'; }).join("");
    select.addEventListener("change", renderMetrics);
    renderMetrics();
  }).catch(function (error) {
    document.getElementById("catalog-status").textContent = "Catalog unavailable: " + error.message;
  });
})();
