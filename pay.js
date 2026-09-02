(function () {
  "use strict";
  var STRIPE_CHECKOUT_HOSTS = { "buy.stripe.com": true, "donate.stripe.com": true };
  var STRIPE_CHECKOUT_PATH = /^\/[A-Za-z0-9_-]+$/;
  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) {
      if (c === "&") return "&amp;";
      if (c === "<") return "&lt;";
      if (c === ">") return "&gt;";
      if (c === '"') return "&quot;";
      return "&#39;";
    });
  }
  function isStripeCheckoutUrl(raw) {
    if (typeof raw !== "string" || !raw) return false;
    var parsed;
    try { parsed = new URL(raw); } catch (err) { return false; }
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
  function hasDurableCapabilityEvidence(checkout) {
    var evidence = checkout && checkout.capability_evidence;
    if (!evidence || typeof evidence !== "object") return false;
    if (typeof evidence.reference !== "string" || !evidence.reference.trim()) return false;
    if (typeof evidence.observed_at !== "string" || !/(?:Z|[+-]\d\d:\d\d)$/.test(evidence.observed_at)) return false;
    return !Number.isNaN(Date.parse(evidence.observed_at));
  }
  function accountReady(snapshot) {
    var provider = snapshot && snapshot.provider || {};
    return provider.name === "stripe" &&
      provider.livemode === true &&
      provider.charges_enabled === true &&
      provider.payouts_enabled === true &&
      Array.isArray(provider.currently_due) &&
      provider.currently_due.length === 0;
  }
  function railEligible(snapshot, listing) {
    var checkout = listing && listing.checkout;
    if (!accountReady(snapshot)) return false;
    if (!checkout || checkout.provider !== "stripe") return false;
    if (checkout.status !== "ACTIVE_CHARGEABLE") return false;
    if (checkout.link_active !== true) return false;
    if (checkout.account_charges_enabled !== true) return false;
    if (checkout.account_payouts_enabled !== true) return false;
    if (!isStripeCheckoutUrl(checkout.url)) return false;
    if (!hasDurableCapabilityEvidence(checkout)) return false;
    var inert = snapshot.inert_duplicate_urls || [];
    if (inert.indexOf(checkout.url) !== -1) return false;
    return true;
  }
  function tipPayDoor() {
    var path = (location && location.pathname) || "";
    return /(?:^|\/)(?:tips|pay)\.html$/i.test(path);
  }
  function fillSlot(slot, listing, snapshot, funnel) {
    if (!railEligible(snapshot, listing)) {
      slot.innerHTML = '<p class="note">Provider rail is inert. Unverified URLs stay unpublished.</p>';
      return;
    }
    // tips.html + pay.html: exact catalog checkout URL (same as land/sku-*.md). commerce keeps funnel gate.
    var checkoutFirst = tipPayDoor() || (funnel && funnel.readiness === "READY_FOR_CHECKOUT");
    if (checkoutFirst) {
      slot.innerHTML = '<p><a class="checkout-active" href="' + esc(listing.checkout.url) +
        '" rel="noopener noreferrer" target="_blank" data-funnel-sku="' + esc(listing.id) +
        '" data-funnel-action="checkout-open">Verified chargeable Stripe checkout</a></p>' +
        '<p class="note">A click is intent, not authorization, settlement, payout, or cash.</p>';
      return;
    }
    slot.innerHTML = '<p><a class="funnel-intake" href="./commerce.html#' + esc(listing.id) +
      '" data-funnel-sku="' + esc(listing.id) +
      '" data-funnel-action="qualification-open">Start public intake, then pay</a></p>' +
      '<p class="note">Provider is chargeable and payout-capable. Missing terms stay in front of checkout.</p>';
  }
  function fillOwner(snapshot) {
    var node = document.getElementById("owner-action");
    if (!node) return;
    var action = snapshot.owner_action || {};
    var fallback = snapshot.fallback || {};
    var money = snapshot.money || {};
    node.innerHTML = '<p><b>Remaining owner Stripe onboarding:</b> ' + esc(action.id || "UNKNOWN") +
      '</p><p>' + esc(action.summary || "") + '</p>' +
      (action.optional_nonblocking ? '<p class="note">' + esc(action.optional_nonblocking) + '</p>' : "") +
      '<p><b>If Stripe later fails closed:</b> <a href="' + esc(fallback.url || "mailto:tokenjunkielabs@gmail.com") +
      '">' + esc(fallback.label || "Email Token Junkie Labs") + '</a></p>' +
      '<p class="note">Collected cash USD ' + esc(money.collected_cash_usd) +
      '. AUTHORIZATION/SETTLEMENT/PAYOUT/BANK_AVAILABLE remain ' +
      esc(money.bank_available || "NOT_LANDED") + '.</p>';
  }
  function ownerActionUrlOk(raw) {
    if (typeof raw !== "string" || !raw) return false;
    var parsed;
    try { parsed = new URL(raw); } catch (err) { return false; }
    if (parsed.protocol !== "https:") return false;
    if (parsed.username || parsed.password) return false;
    return parsed.hostname === "dashboard.stripe.com" ||
      parsed.hostname === "www.paypal.com" ||
      parsed.hostname === "paypal.com" ||
      parsed.hostname === "github.com" ||
      parsed.hostname === "squareup.com" ||
      parsed.hostname === "www.squareup.com";
  }
  function fillFailover(registry, snapshot) {
    var node = document.getElementById("rail-failover");
    if (!node) return;
    var rails = (registry && registry.rails) || [];
    var stripeReady = accountReady(snapshot);
    var actions = [];
    rails.forEach(function (rail) {
      var list = (rail.required_owner_actions || []).concat(rail.optional_owner_actions || []);
      list.forEach(function (action) {
        if (action && action.kind === "EXTERNAL_OWNER_ACTION" && ownerActionUrlOk(action.url)) {
          if (!stripeReady || action.blocking) actions.push(action);
        }
      });
    });
    if (stripeReady && !actions.length) {
      node.innerHTML = '<p class="note">Measured Stripe rail is CHARGEABLE. Failover owner actions stay one-click and unpublished as checkout. Full registry: <a href="./payment-capability.html">payment rails</a>.</p>';
      return;
    }
    var html = '<p><b>Storefront failover.</b> Unverified rails stay inert. Official provider UIs only:</p>';
    actions.forEach(function (action) {
      html += '<p><a class="failover-owner-action" href="' + esc(action.url) +
        '" rel="noopener noreferrer" target="_blank">' + esc(action.label) + "</a></p>";
    });
    html += '<p><a href="mailto:tokenjunkielabs@gmail.com">tokenjunkielabs@gmail.com</a></p>';
    node.innerHTML = html;
  }
  function render(snapshot, catalog, registry) {
    var byId = {};
    (catalog.listings || []).forEach(function (row) { byId[row.id] = row; });
    Array.prototype.forEach.call(document.querySelectorAll(".js-checkout-slot"), function (slot) {
      var sku = slot.getAttribute("data-sku");
      fillSlot(slot, byId[sku], snapshot, (catalog.funnels || {})[sku]);
    });
    fillOwner(snapshot);
    fillFailover(registry, snapshot);
  }
  var snapshotUrl = "./revenue/checkout_capability/snapshot.json?v=" + Date.now();
  var catalogUrl = "./revenue/outcome_commerce/catalog.json?v=" + Date.now();
  var registryUrl = "./revenue/payment_capability/registry.json?v=" + Date.now();
  Promise.all([
    fetch(snapshotUrl, { cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error(String(response.status));
      return response.json();
    }),
    fetch(catalogUrl, { cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error(String(response.status));
      return response.json();
    }),
    fetch(registryUrl, { cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error(String(response.status));
      return response.json();
    }).catch(function () { return { rails: [] }; })
  ]).then(function (pair) {
    render(pair[0], pair[1], pair[2]);
  }).catch(function (error) {
    Array.prototype.forEach.call(document.querySelectorAll(".js-checkout-slot"), function (slot) {
      slot.textContent = "Catalog unavailable: " + error.message + ". Stripe URLs stay inert.";
    });
  });
})();
