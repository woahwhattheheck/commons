(function () {
  "use strict";
  var data;
  var STRIPE_CHECKOUT_HOSTS = { "buy.stripe.com": true, "donate.stripe.com": true };
  var STRIPE_CHECKOUT_PATH = /^\/[A-Za-z0-9_-]+$/;
  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) {
      return ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c];
    });
  }
  function isLiveStripeCheckoutUrl(raw) {
    if (typeof raw !== "string" || !raw) return false;
    var parsed;
    try {
      parsed = new URL(raw);
    } catch (err) {
      return false;
    }
    if (parsed.protocol !== "https:") return false;
    if (parsed.username || parsed.password) return false;
    if (/^https:\/\/[^/]*:\d+/i.test(raw)) return false;
    if (parsed.port !== "") return false;
    if (raw.indexOf("?") !== -1 || raw.indexOf("#") !== -1) return false;
    if (parsed.search !== "" || parsed.hash !== "") return false;
    if (!Object.prototype.hasOwnProperty.call(STRIPE_CHECKOUT_HOSTS, parsed.hostname)) return false;
    if (!STRIPE_CHECKOUT_PATH.test(parsed.pathname)) return false;
    if (parsed.href !== raw) return false;
    return true;
  }
  function termsSource(row) {
    return row.source || row.source_artifact || {};
  }
  function termsLabel(row) {
    var src = termsSource(row);
    var label = esc(src.path);
    if (Object.prototype.hasOwnProperty.call(src, "pointer")) label += "#" + esc(src.pointer);
    return label;
  }
  function checkoutAnchor(row) {
    var checkout = row.checkout;
    if (!checkout || checkout.status !== "LIVE" || checkout.provider !== "stripe") return "";
    if (!isLiveStripeCheckoutUrl(checkout.url)) return "";
    return '<p><a class="checkout-live" href="' + esc(checkout.url) + '" rel="noopener noreferrer" target="_blank">LIVE Stripe hosted checkout</a></p>';
  }
  function amount(component, quantity) {
    var kind = component.kind, q = Number(quantity || 0), total = 0;
    if (["fixed", "subscription", "milestone", "license"].indexOf(kind) >= 0) total = Number(component.amount || 0) * q;
    else if (["usage", "outcome", "sponsorship"].indexOf(kind) >= 0) total = Number(component.unit_amount || 0) * Math.max(0, q - Number(component.included || 0));
    else if (kind === "take_rate") total = q * Number(component.rate_bps || 0) / 10000;
    return total;
  }
  function componentText(c) {
    if (c.amount != null) return "$" + Number(c.amount).toLocaleString() + " " + esc(c.kind);
    if (c.unit_amount != null) return "$" + esc(c.unit_amount) + "/" + esc(c.meter || "unit") + " " + esc(c.kind);
    if (c.rate_bps != null) return (Number(c.rate_bps) / 100).toFixed(2) + "% " + esc(c.kind);
    return esc(c.kind);
  }
  function renderCatalog() {
    document.getElementById("catalog-status").textContent = data.listings.length + " adapters; source terms remain canonical.";
    document.getElementById("catalog").innerHTML = data.listings.map(function (row) {
      return '<article class="card"><p class="state-' + esc(row.state) + '"><b>' + esc(row.state) + '</b></p><h3>' + esc(row.name) + '</h3>' +
        '<p class="money">' + row.pricing.components.map(componentText).join(" + ") + ' ' + esc(row.pricing.currency) + '</p>' +
        '<p>' + row.pricing.components.map(function(c){return '<span class="pill">' + esc(c.kind) + '</span>';}).join("") + '</p>' +
        '<p class="note">terms: <code>' + termsLabel(row) + '</code></p>' +
        '<p><a href="./' + esc(row.routes.human) + '">human door</a> · <a href="./' + esc(row.routes.machine) + '">machine source</a></p>' +
        checkoutAnchor(row) + '</article>';
    }).join("");
  }
  function renderMetrics() {
    var id = document.getElementById("listing").value;
    var row = data.listings.filter(function (x) { return x.id === id; })[0];
    var host = document.getElementById("metrics");
    host.innerHTML = row.pricing.components.map(function (c) {
      var initial = ["fixed", "subscription", "milestone", "license"].indexOf(c.kind) >= 0 ? "1" : "0";
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
