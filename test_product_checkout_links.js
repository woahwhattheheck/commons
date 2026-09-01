"use strict";
const assert = require("assert");
const fs = require("fs");
const path = require("path");

const offers = [
  ["dealer-service-lead-rescue.html", "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b"],
  ["plant-downtime-handoff.html", "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e"],
  ["referral-intake-completeness.html", "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c"],
  ["repair-booking-preflight.html", "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d"]
];

for (const [file, url] of offers) {
  const html = fs.readFileSync(path.join(__dirname, file), "utf8");
  const count = html.split(url).length - 1;
  assert.strictEqual(count, 2, file + " must expose the exact checkout link twice");
  const safeLink = 'href="' + url + '" target="_blank" rel="noopener noreferrer"';
  assert.ok(html.includes(safeLink), file + " must isolate the external checkout tab");
  assert.ok(html.includes("Start the $199 diagnostic"), file + " must name the exact purchase");
  assert.ok(html.includes("Secure Stripe checkout opens in a new tab."), file + " must explain navigation");
  assert.ok(/never charges|never charge/.test(html), file + " must preserve the proof-versus-payment boundary");
  assert.ok(/payment happens only if you complete Stripe Checkout/i.test(html), file + " must state when payment occurs");
  assert.ok(!html.includes("No Stripe charge"), file + " must not contradict the live checkout");
  assert.ok(!/(?:sk|pk)_(?:live|test)_|client_secret|payment_intent/i.test(html), file + " must not expose payment credentials or identifiers");
  assert.ok(!/SKU [67] pattern|do not remint/i.test(html), file + " must not expose internal catalog jargon");
}

console.log("product checkout links: 4 pages PASS");
