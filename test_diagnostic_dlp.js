#!/usr/bin/env node
"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = __dirname;
const html = fs.readFileSync(path.join(root, "diagnostic.html"), "utf8");
const carrier = fs.readFileSync(path.join(root, "carrier.js"), "utf8");
const scripts = Array.from(html.matchAll(/<script>([\s\S]*?)<\/script>/g), (match) => match[1]);
const dlp = scripts.find((source) => source.includes("var forbidden = ["));
assert.ok(dlp, "diagnostic DLP script must exist");

let submitHandler;
const form = {
  elements: { from: { value: "" }, body: { value: "" } },
  addEventListener(name, handler) {
    if (name === "submit") submitHandler = handler;
  },
};
const out = { textContent: "" };
const document = {
  getElementById(id) {
    if (id === "say") return form;
    if (id === "out") return out;
    throw new Error("unexpected element: " + id);
  },
};
vm.runInNewContext(dlp, { document });
assert.equal(typeof submitHandler, "function", "DLP must register before carrier submission");

function attempt(body, from = "public-org") {
  let prevented = false;
  let stopped = false;
  form.elements.from.value = from;
  form.elements.body.value = body;
  out.textContent = "";
  submitHandler({
    preventDefault() { prevented = true; },
    stopImmediatePropagation() { stopped = true; },
  });
  return { prevented, stopped, message: out.textContent };
}

const blocked = [
  "CUSTOMER_EMAIL: private@example.com",
  "PRIVATE_CONTACT: private@example.com",
  "CUSTOMER_PHONE: +1-212-555-0199",
  "CUSTOMER_NAME: Jane Doe",
  "STREET_ADDRESS: 123 Main Street",
  "CONTACT: private@example.com",
  '"CUSTOMER_EMAIL": "private@example.com"',
  "PASSWORD: hunter2",
  "AUTHORIZATION: Bearer secret-token",
  "AKIAABCDEFGHIJKLMNOP",
];
blocked.forEach((value) => {
  const result = attempt(value);
  assert.ok(result.prevented, "must prevent private value: " + value);
  assert.ok(result.stopped, "must stop carrier for private value: " + value);
});

const clean = attempt([
  "PLAIN: Public, non-confidential GGUF diagnostic purchase intent.",
  "PUBLIC_CONTACT_URL: https://example.com/contact",
  "PURCHASE_INTENT: YES",
].join("\n"));
assert.equal(clean.prevented, false, "public contact URL must remain accepted");
assert.equal(clean.stopped, false, "clean signal must reach the carrier");

const privateFrom = attempt("PURCHASE_INTENT: YES", "CONTACT: private@example.com");
assert.ok(privateFrom.prevented && privateFrom.stopped, "private values in from must also be blocked");
assert.ok(html.indexOf("event.stopImmediatePropagation()") < html.indexOf("carrier.js?"));
assert.ok(html.includes('data-no-from-memory="true"'));
assert.equal(
  (carrier.match(/input\[name="from"\]:not\(\[data-no-from-memory\]\)/g) || []).length,
  2,
  "from-memory load and save must both skip opted-out diagnostic inputs",
);

console.log("DIAGNOSTIC_DLP_OK " + blocked.length + " blocked vectors + clean/public/from-memory checks");
