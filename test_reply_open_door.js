#!/usr/bin/env node
// Reply and generated post forms share the same blank-metadata open-door contract.
const assert = require("assert");
const fs = require("fs");

const carrier = fs.readFileSync("carrier.js", "utf8");
const reply = fs.readFileSync("reply.js", "utf8");

assert(carrier.includes('var src = asFrom(rawFrom) || "UNSEATED"'));
assert(carrier.includes("form.querySelectorAll('[name=\"from\"], [name=\"to\"]')"));
assert(reply.includes('asFrom(fromIn.value) || "UNSEATED"'));
assert(reply.includes('fromLab.textContent = "from (optional)"'));
assert(reply.includes('fromIn.setAttribute("placeholder", "blank lands as UNSEATED")'));
assert(reply.includes("Contents/Git Data may create the same canonical p/{id}.md"));
assert(reply.includes("if (!body && !file)"), "body or attachment remains transport integrity");
assert(!reply.includes("from is required"));
assert(!reply.includes("Direct Contents/Git Data post creation is unsupported"));

console.log("REPLY OPEN DOOR TEST: PASS");
