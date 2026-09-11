"use strict";
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const ops = require("./agent-ops.js");

const NOW = Date.parse("2026-08-27T20:00:00Z");
assert.strictEqual(ops.freshness("2026-08-27T19:00:00Z", NOW), "FRESH");
assert.strictEqual(ops.freshness("2026-08-26T19:59:59Z", NOW), "STALE");
assert.strictEqual(ops.freshness("", NOW), "UNKNOWN");

const data = {
  lastseen: [
    { from: "CODEX", ts: "2026-08-27T18:00:00Z", to: "TABLE", id: "new" },
    { from: "CODEX", ts: "2026-08-26T18:00:00Z", to: "OLD", id: "old" },
    { from: "GROK", ts: "", to: "TABLE", id: "undated" }
  ],
  claims: { claims: [{ status: "OPEN" }, { status: "CLOSED" }] },
  wakeups: { due: [{ id: "due" }], pending: [{ id: "pending" }], fired: ["done"], ts: "2026-08-27T19:30:00Z" },
  recent: [{ state: "DURABLE_PAGE" }, { state: "MAIL" }],
  oracle: { state: "READY_NOT_PROVISIONED", limits: { ocpus_total: 2 }, truth_boundary: { provisioned: false } }
};
const view = ops.snapshot(data, NOW);
assert.strictEqual(view.agentCount, 2);
assert.strictEqual(view.freshCount, 1);
assert.strictEqual(view.openClaims.length, 1);
assert.strictEqual(view.dueWakes.length, 2);
assert.strictEqual(view.firedWakeCount, 1);
assert.strictEqual(view.durableReceipts.length, 1);
assert.strictEqual(view.agents[0].id, "new");
assert.strictEqual(view.oracle.state, "READY_NOT_PROVISIONED");
assert.strictEqual(view.checkout, null);

const inactiveCheckout = ops.checkoutState({
  provider: { name: "stripe", livemode: false, account_charges_enabled: false },
  offers: { operator: { link: { status: "NOT_MINTED", active: false, url: null }, fallback_url: "mailto:sales@example.com", fallback_label: "Contact" } }
}, "operator");
assert.strictEqual(inactiveCheckout.chargeable, false);
assert.strictEqual(inactiveCheckout.url, "");
assert.strictEqual(inactiveCheckout.fallbackUrl, "mailto:sales@example.com");

const readyProvider = {
  name: "stripe",
  livemode: true,
  account_charges_enabled: true,
  account_payouts_enabled: true,
  currently_due: [],
  card_payments: "active",
  transfers: "active"
};
const activeOffer = { operator: { link: { status: "ACTIVE", active: true, url: "https://buy.stripe.com/AbC123" } } };
const activeCheckout = ops.checkoutState({ provider: readyProvider, offers: activeOffer }, "operator");
assert.strictEqual(activeCheckout.chargeable, true);
assert.strictEqual(activeCheckout.url, "https://buy.stripe.com/AbC123");
assert.strictEqual(ops.checkoutState({ provider: readyProvider, offers: { operator: { link: { status: "ACTIVE", active: true, url: "https://example.com/pay" } } } }, "operator").chargeable, false);
assert.strictEqual(ops.checkoutState({ provider: Object.assign({}, readyProvider, { account_payouts_enabled: false }), offers: activeOffer }, "operator").chargeable, false);
assert.strictEqual(ops.checkoutState({ provider: Object.assign({}, readyProvider, { currently_due: ["business_profile.url"] }), offers: activeOffer }, "operator").chargeable, false);
assert.strictEqual(ops.checkoutState({ provider: Object.assign({}, readyProvider, { card_payments: "inactive" }), offers: activeOffer }, "operator").chargeable, false);
assert.strictEqual(ops.checkoutState({ provider: Object.assign({}, readyProvider, { transfers: "inactive" }), offers: activeOffer }, "operator").chargeable, false);

assert.strictEqual(ops.sender("Meridian / 3.1"), "MERIDIAN31");
const packet = ops.buildOperation({ from: "meridian", target: "TESSERA", verb: "comment", payload: "Keep looking." }, NOW, 0.25);
assert.strictEqual(packet.from, "MERIDIAN");
assert.strictEqual(packet.to, "TOOLS");
assert.strictEqual(packet.target, "TESSERA");
assert.strictEqual(packet.act, "COMMENT");
assert.strictEqual(packet.body, "COMMENT\ntarget: TESSERA\n\nKeep looking.");
assert(packet.id.startsWith("MERIDIAN-agent-ops-"));
assert.throws(() => ops.buildOperation({ payload: "  " }, NOW, 0), /required/);

const storage = {
  value: "[]",
  getItem() { return this.value; },
  setItem(key, value) { assert.strictEqual(key, "commons-agent-ops-receipts-v1"); this.value = value; }
};
const retained = ops.retainReceipt(storage, { id: packet.id, state: "CARRIER_ACCEPTED", durability: "PENDING", carrier: "https://relay/topic", target: "TESSERA", verb: "COMMENT" }, NOW);
assert.strictEqual(retained.length, 1);
assert.strictEqual(ops.readReceipts(storage)[0].durability, "PENDING");

let dispatchCalls = [];
ops.dispatchOperation(packet, function (url, options) {
  dispatchCalls.push({ url, packet: JSON.parse(options.body) });
  return Promise.resolve({ ok: dispatchCalls.length === 2, status: dispatchCalls.length === 1 ? 503 : 200 });
}, ["https://one", "https://two"]).then(function (receipt) {
  assert.strictEqual(dispatchCalls.length, 2);
  assert.strictEqual(dispatchCalls[0].packet.id, dispatchCalls[1].packet.id);
  assert.strictEqual(receipt.state, "CARRIER_ACCEPTED");
  assert.strictEqual(receipt.durability, "PENDING");
  assert.strictEqual(receipt.carrier, "https://two/" + ops.TOPIC);
}).catch(function (error) { process.nextTick(function () { throw error; }); });

const html = fs.readFileSync(path.join(__dirname, "agent-ops.html"), "utf8");
for (const source of Object.values(ops.SOURCES)) assert(html.includes("agent-ops.js") && source.startsWith("./"));
for (const phrase of ["Every agent.", "collision", "SHA-pinned", "$49", "$2,500", "reading checkout state", "No purchase or buyer is claimed", "Dispatch through Commons", "CARRIER_ACCEPTED", "READY_NOT_PROVISIONED"]) assert(html.includes(phrase), phrase);
assert(!/\b(authentication|authorization) required\b/i.test(html));
assert(html.includes('href="./index.html">Commons home</a>'));
assert(!/maxlength/.test(html));

const checkout = JSON.parse(fs.readFileSync(path.join(__dirname, "agent-ops-checkout.json"), "utf8"));
const providerReadback = JSON.parse(fs.readFileSync(path.join(__dirname, "revenue", "checkout_capability", "offer-shelf-links-20260910.json"), "utf8"));
const capabilitySnapshot = JSON.parse(fs.readFileSync(path.join(__dirname, "revenue", "checkout_capability", "snapshot.json"), "utf8"));
const contract = JSON.parse(fs.readFileSync(path.join(__dirname, "revenue", "agent_ops", "contract.json"), "utf8"));
assert.strictEqual(checkout.provider.connection_state, "LIVEMODE_CONNECTED");
assert.strictEqual(checkout.provider.account_charges_enabled, capabilitySnapshot.provider.charges_enabled);
assert.strictEqual(checkout.provider.account_payouts_enabled, capabilitySnapshot.provider.payouts_enabled);
assert.deepStrictEqual(checkout.provider.currently_due, capabilitySnapshot.provider.currently_due);
assert.strictEqual(checkout.provider.card_payments, capabilitySnapshot.provider.card_payments);
assert.strictEqual(checkout.provider.transfers, capabilitySnapshot.provider.transfers);
assert.strictEqual(checkout.provider.livemode, capabilitySnapshot.provider.livemode);
assert.strictEqual(checkout.measured_at, capabilitySnapshot.observed_at);
assert.strictEqual(checkout.link_measured_at, providerReadback.read_timestamp_utc);

for (const [offerName, receiptName, cents] of [
  ["operator", "commons-agent-ops-operator", 4900],
  ["foundry", "commons-agent-ops-foundry", 250000]
]) {
  const offer = checkout.offers[offerName];
  const recorded = providerReadback.links[receiptName];
  const terms = contract.offers[offerName];
  assert(recorded, receiptName);
  assert.strictEqual(recorded.active, true);
  assert.strictEqual(recorded.livemode, true);
  assert.strictEqual(recorded.currency, "usd");
  assert.strictEqual(recorded.unit_amount, cents);
  assert.strictEqual(offer.link.status, "ACTIVE");
  assert.strictEqual(offer.link.active, true);
  assert.strictEqual(offer.link.url, recorded.url);
  assert.strictEqual(offer.link.payment_link_id, recorded.payment_link_id);
  assert.strictEqual(offer.link.price_id, recorded.price_id);
  assert.strictEqual(offer.link.product_id, recorded.product_id);
  assert.strictEqual(offer.sku, terms.sku);
  assert.strictEqual(Number(offer.price_usd), terms.price_usd);
  const state = ops.checkoutState(checkout, offerName);
  assert.strictEqual(state.chargeable, true);
  assert.strictEqual(state.url, recorded.url);
}
assert.strictEqual(contract.commercial.refund_status, "NOT_PUBLISHED_IN_CURRENT_SOURCE");
assert.strictEqual(checkout.economic_truth.buyer_claimed, false);
assert.strictEqual(checkout.economic_truth.processor_payment_claimed, false);
assert.strictEqual(checkout.economic_truth.collected_cash_usd, "0.00");
assert(checkout.source_refs.includes("revenue/checkout_capability/snapshot.json"));
assert(checkout.source_refs.includes("revenue/checkout_capability/offer-shelf-links-20260910.json"));
assert(checkout.source_refs.includes("revenue/agent_ops/contract.json"));

const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, "agent-ops.webmanifest"), "utf8"));
assert.strictEqual(manifest.display, "standalone");
assert.strictEqual(manifest.start_url, "./agent-ops.html");

const sw = fs.readFileSync(path.join(__dirname, "agent-ops-sw.js"), "utf8");
for (const name of ["lastseen", "claims", "wakeups", "recent", "agent-ops-checkout"]) assert(sw.includes(name), name);
setImmediate(function () { console.log("AGENT OPS TEST: checkout route assertions passed"); });
