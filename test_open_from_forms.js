const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const carrier = fs.readFileSync("carrier.js", "utf8");

function extractFunction(source, name) {
  const start = source.indexOf(`function ${name}(`);
  assert.notStrictEqual(start, -1, `${name} was not found`);
  const brace = source.indexOf("{", start);
  let depth = 0;
  for (let i = brace; i < source.length; i += 1) {
    if (source[i] === "{") depth += 1;
    if (source[i] === "}") {
      depth -= 1;
      if (depth === 0) return source.slice(start, i + 1);
    }
  }
  throw new Error(`${name} was not closed`);
}

const sandbox = {};
vm.runInNewContext(`${extractFunction(carrier, "asFrom")}; result = [
  asFrom(""),
  asFrom("  player / lane 7  "),
  asFrom("x".repeat(160))
];`, sandbox, { filename: "carrier.js#asFrom" });
assert.strictEqual(sandbox.result[0], "", "blank must remain available for the UNSEATED fallback");
assert.strictEqual(sandbox.result[1], "player / lane 7", "arbitrary caller text must survive unchanged");
assert.strictEqual(sandbox.result[2], "x".repeat(160), "caller text must not be length-gated");

const pages = [
  ...fs.readdirSync(".").filter(name => name.endsWith(".html")),
  ...fs.readdirSync("to").filter(name => name.endsWith(".html")).map(name => `to/${name}`),
];

let checkedPages = 0;
for (const page of pages) {
  const source = fs.readFileSync(page, "utf8");
  const senderInputs = Array.from(source.matchAll(/<input\b[^>]*\bname="(?:from|from_other)"[^>]*>/gi), match => match[0]);
  if (!senderInputs.length) continue;
  checkedPages += 1;
  for (const input of senderInputs) {
    assert(!/\brequired\b/i.test(input), `${page} still requires a caller identity`);
    assert(!/\bmaxlength\s*=/i.test(input), `${page} still length-gates a caller identity`);
  }
}
assert(checkedPages > 50, `expected broad public-route coverage, checked only ${checkedPages} pages`);

console.log("PASS test_open_from_forms.js");
