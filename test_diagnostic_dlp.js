#!/usr/bin/env node
"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const html = fs.readFileSync("diagnostic.html", "utf8");
const inlineScripts = Array.from(html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi), (match) => match[1]);
const dlpScript = inlineScripts.find((source) =>
  source.includes("forbiddenNames") && source.includes('form.addEventListener("submit"')
);
assert(dlpScript, "diagnostic DLP inline script was not found");

let submitListener = null;
let capture = null;
const output = { textContent: "" };
const form = {
  elements: [],
  addEventListener(type, listener, options) {
    if (type === "submit") {
      submitListener = listener;
      capture = options;
    }
  },
};
const document = {
  getElementById(id) {
    if (id === "say") return form;
    if (id === "out") return output;
    return null;
  },
};
vm.runInNewContext(dlpScript, { document, JSON, Object, Array, String }, { filename: "diagnostic.html#dlp" });
assert.strictEqual(typeof submitListener, "function", "diagnostic submit listener was not registered");
assert.strictEqual(capture, true, "diagnostic DLP listener must run in capture phase");

function submit(body, fieldName = "body") {
  form.elements = [
    { name: "to", value: "OFFER" },
    { name: fieldName, value: body },
  ];
  const event = {
    prevented: false,
    stopped: false,
    preventDefault() { this.prevented = true; },
    stopImmediatePropagation() { this.stopped = true; },
  };
  output.textContent = "";
  submitListener(event);
  return event;
}

const canonicalForbiddenNames = [
  "authorization", "aws_access_key_id", "password", "passwd", "passphrase",
  "api_key", "access_token", "auth_token", "client_secret", "secret", "token",
  "private_buyer", "private_customer", "buyer_private", "model_bytes",
  "model_weights", "gguf_bytes", "gguf_file", "weights", "base64", "b64",
  "tax_id", "taxpayer_id", "taxpayer_identification", "ein", "tin",
  "email", "email_address", "customer_email", "private_email", "contact_email",
  "buyer_email", "work_email", "contact", "private_contact", "customer_contact",
  "buyer_contact", "phone", "phone_number", "telephone", "mobile", "mobile_phone",
  "customer_phone", "private_phone", "contact_phone", "buyer_phone", "name",
  "full_name", "first_name", "last_name", "legal_name", "customer_name",
  "private_name", "contact_name", "buyer_name", "address", "street_address",
  "address_line_1", "address_line_2", "mailing_address", "postal_address",
  "customer_address", "private_address", "contact_address", "postal_code",
  "zip_code", "postcode", "routing_number", "account_number", "bank_account",
  "bank_account_number", "bank_routing_number", "aba_routing_number", "iban",
  "swift", "swift_code", "bic", "sort_code",
  "aws_secret_access_key",
];

for (const field of canonicalForbiddenNames) {
  for (const payload of [
    JSON.stringify({ [field]: "hidden" }),
    JSON.stringify({ safe: { nested: { [field]: "hidden" } } }),
    `"${field}": "hidden"`,
    `${field}=hidden`,
  ]) {
    const event = submit(payload);
    assert.strictEqual(event.prevented, true, `${field} payload was not prevented: ${payload}`);
    assert.strictEqual(event.stopped, true, `${field} payload did not stop propagation: ${payload}`);
  }
}

for (const payload of [
  "AUTHORIZATION: Bearer owner-secret-token",
  "PUBLIC_CONTACT_URL: https://alice:secret@example.com/contact",
  "PUBLIC_CONTACT_URL: https://alice%3Asecret%40example.com/contact",
  "AWS_ACCESS_KEY_ID: AKIAABCDEFGHIJKLMNOP",
  "AUTH: ghp_1234567890abcdef",
  "PAYLOAD: data:application/octet-stream;base64,QUJDREVGRw==",
  "alice.customer@example.com",
  "555-123-4567",
  "+1 (555) 123-4567",
  "5551234567",
  "123 Main Street",
  "A".repeat(100),
]) {
  const event = submit(payload);
  assert.strictEqual(event.prevented, true, `named sensitive payload was not prevented: ${payload}`);
  assert.strictEqual(event.stopped, true, `named sensitive payload did not stop propagation: ${payload}`);
}

for (const name of canonicalForbiddenNames) {
  const event = submit("hidden", name);
  assert.strictEqual(event.prevented, true, `sensitive form field name was not prevented: ${name}`);
  assert.strictEqual(event.stopped, true, `sensitive form field name did not stop propagation: ${name}`);
}

const reviewerCamelFields = [
  "routingNumber", "accountNumber", "bankAccount", "customerEmail",
  "phoneNumber", "fullName",
];
for (const field of reviewerCamelFields) {
  for (const payload of [
    JSON.stringify({ [field]: "hidden" }),
    JSON.stringify({ public: { nested: { [field]: "hidden" } } }),
    `${field}=hidden`,
  ]) {
    const event = submit(payload);
    assert.strictEqual(event.prevented, true, `camelCase payload was not prevented: ${payload}`);
    assert.strictEqual(event.stopped, true, `camelCase payload did not stop propagation: ${payload}`);
  }
  const fieldEvent = submit("hidden", field);
  assert.strictEqual(fieldEvent.prevented, true, `camelCase form field was not prevented: ${field}`);
  assert.strictEqual(fieldEvent.stopped, true, `camelCase form field did not stop propagation: ${field}`);
}

let overDepthPayload = JSON.stringify({ privateEmail: "alice@example.com" });
for (let layer = 0; layer < 5; layer += 1) overDepthPayload = encodeURIComponent(overDepthPayload);
const encodedReviewerPayloads = [
  "alice%40example.com",
  "%7B%22token%22%3A%22hidden%22%7D",
  "%7B%22privateEmail%22%3A%22alice%40example.com%22%7D",
  "%257B%2522privateEmail%2522%253A%2522alice%2540example.com%2522%257D",
  "customerEmail%3Dalice%2540example.com",
  overDepthPayload,
];
for (const encoded of encodedReviewerPayloads) {
  const event = submit(encoded);
  assert.strictEqual(event.prevented, true, `encoded payload was not prevented: ${encoded}`);
  assert.strictEqual(event.stopped, true, `encoded payload did not stop propagation: ${encoded}`);
}

const fullPostPrefix = [
  "PLAIN: Public, non-confidential GGUF diagnostic purchase intent.",
  "PURCHASE_INTENT: YES",
  "GGUF_CONTROL: YES",
  "HARNESS_READY: YES",
  "PUBLIC_CONTACT_URL: https://example.com/contact",
].join("\n");
for (const payload of [
  ...reviewerCamelFields.map((field) => `${field}=hidden`),
  ...encodedReviewerPayloads,
]) {
  const event = submit(`${fullPostPrefix}\n${payload}`);
  assert.strictEqual(event.prevented, true, `full-post bypass was not prevented: ${payload}`);
  assert.strictEqual(event.stopped, true, `full-post bypass did not stop propagation: ${payload}`);
}

for (const safe of [
  JSON.stringify({ public_objective: "reproducibility" }),
  JSON.stringify({ api_key: "", nested: { token: "" } }),
  "PUBLIC_CONTACT_URL: https://example.com/contact",
  "PUBLIC_CONTACT_URL: https://example.com/contact?next=%2Fpublic",
  "PUBLIC_OBJECTIVE: reproducibility",
]) {
  const event = submit(safe);
  assert.strictEqual(event.prevented, false, `safe payload was unexpectedly prevented: ${safe}`);
  assert.strictEqual(event.stopped, false, `safe payload unexpectedly stopped propagation: ${safe}`);
}

console.log(`diagnostic inline DLP PASS: ${canonicalForbiddenNames.length} canonical names plus camelCase/encoded/full-post adversarial payloads`);
