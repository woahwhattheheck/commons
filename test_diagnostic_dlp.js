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
  "PUBLIC_CONTACT_URL: https://alice:secret@127.0.0.1/contact",
  "PUBLIC_CONTACT_URL: https://alice%3Asecret%40example.com/contact",
  "PUBLIC_CONTACT_URL: https://alice@example.com/contact",
  "PUBLIC_CONTACT_URL: https://alice@127.0.0.1/contact",
  "PUBLIC_CONTACT_URL: https://alice%40example.com/contact",
  "PUBLIC_CONTACT_URL: https://alice%40127.0.0.1/contact",
  "PUBLIC_CONTACT_URL: https://alice%2F@127.0.0.1/contact",
  "PUBLIC_CONTACT_URL: https://alice%3F@127.0.0.1/contact",
  "PUBLIC_CONTACT_URL: https://alice%23@127.0.0.1/contact",
  "PUBLIC_CONTACT_URL: https://alice%0A@example.com/contact",
  "PUBLIC_OBJECTIVE: priv%FFateEmail=hidden",
  "PUBLIC_OBJECTIVE: tok%FFen=hidden",
  "PUBLIC_CONTACT_URL: https://example.com/contact#privateEmail=hidden",
  "PUBLIC_CONTACT_URL: https://example.com/contact#token=hidden",
  "PUBLIC_CONTACT_URL: https://example.com/contact#%70rivateEmail=hidden",
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

const bindingPathPayloads = [
  "?privateEmail[0]=hidden",
  "?user.privateEmail=hidden",
  "?user[privateEmail]=hidden",
  "?users[0][privateEmail]=hidden",
  "?PrIvAtEeMaIl=hidden",
  "?user%5BprivateEmail%5D=hidden",
  JSON.stringify({ "user.private_email": "hidden" }),
  JSON.stringify({ "privateEmail[0]": "hidden" }),
  JSON.stringify({ "users[0][privateEmail]": "hidden" }),
  JSON.stringify({ PrIvAtEeMaIl: "hidden" }),
  'payload={"private_email": "secret"',
  '{"private_email": \'secret\'}',
];
for (const payload of bindingPathPayloads) {
  const event = submit(payload);
  assert.strictEqual(event.prevented, true, `binding-path payload was not prevented: ${payload}`);
  assert.strictEqual(event.stopped, true, `binding-path payload did not stop propagation: ${payload}`);
}

const safeBindingPayloads = [
  "?user[privateEmail]=",
  "?user[privateEmail]=%20%20",
  "?publicObjective=fix_user[privateEmail]_parsing",
  "?public_privateEmail=hidden",
  "?email_address_public_opt_in=false",
  "?awssecretary=public",
];
for (const payload of safeBindingPayloads) {
  const event = submit(payload);
  assert.strictEqual(event.prevented, false, `safe binding control was prevented: ${payload}`);
  assert.strictEqual(event.stopped, false, `safe binding control stopped propagation: ${payload}`);
}

function nestedArrayJson(depth, leaf) {
  return "[".repeat(depth) + JSON.stringify(leaf) + "]".repeat(depth);
}

for (const payload of [
  nestedArrayJson(33, { public_objective: "safe" }),
  nestedArrayJson(2200, { public_objective: "safe" }),
  nestedArrayJson(32, { privateEmail: "hidden" }),
  JSON.stringify(Array(1000).fill(0)),
]) {
  const event = submit(payload);
  assert.strictEqual(event.prevented, true, "over-budget JSON was not prevented");
  assert.strictEqual(event.stopped, true, "over-budget JSON did not stop propagation");
}

for (const payload of [
  nestedArrayJson(32, { public_objective: "safe" }),
  JSON.stringify(Array(999).fill(0)),
]) {
  const event = submit(payload);
  assert.strictEqual(event.prevented, false, "in-budget safe JSON was prevented");
  assert.strictEqual(event.stopped, false, "in-budget safe JSON stopped propagation");
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
  ...bindingPathPayloads,
  nestedArrayJson(33, { public_objective: "safe" }),
  nestedArrayJson(2200, { public_objective: "safe" }),
  JSON.stringify(Array(1000).fill(0)),
]) {
  const event = submit(`${fullPostPrefix}\n${payload}`);
  assert.strictEqual(event.prevented, true, `full-post bypass was not prevented: ${payload}`);
  assert.strictEqual(event.stopped, true, `full-post bypass did not stop propagation: ${payload}`);
}

for (const payload of [
  ...safeBindingPayloads,
  nestedArrayJson(32, { public_objective: "safe" }),
  JSON.stringify(Array(999).fill(0)),
]) {
  const event = submit(`${fullPostPrefix}\n${payload}`);
  assert.strictEqual(event.prevented, false, `safe full-post control was prevented: ${payload.slice(0, 80)}`);
  assert.strictEqual(event.stopped, false, `safe full-post control stopped propagation: ${payload.slice(0, 80)}`);
}

for (const safe of [
  JSON.stringify({ public_objective: "reproducibility" }),
  JSON.stringify({ api_key: "", nested: { token: "" } }),
  "PUBLIC_CONTACT_URL: https://example.com/contact",
  "PUBLIC_CONTACT_URL: https://example.com/contact?next=%2Fpublic",
  "PUBLIC_CONTACT_URL: https://example.com/contact#section",
  "PUBLIC_CONTACT_URL: https://example.com/alice%2F@public",
  "PUBLIC_OBJECTIVE: 100%",
  "PUBLIC_OBJECTIVE: 100%25",
  "PUBLIC_OBJECTIVE: reproducibility",
]) {
  const event = submit(safe);
  assert.strictEqual(event.prevented, false, `safe payload was unexpectedly prevented: ${safe}`);
  assert.strictEqual(event.stopped, false, `safe payload unexpectedly stopped propagation: ${safe}`);
}

console.log(`diagnostic inline DLP PASS: ${canonicalForbiddenNames.length} canonical names plus camelCase/encoded/full-post adversarial payloads`);
