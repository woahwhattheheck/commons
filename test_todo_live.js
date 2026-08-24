const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = __dirname;
const html = fs.readFileSync(path.join(root, "todo.html"), "utf8");
const directives = fs.readFileSync(path.join(root, "DIRECTIVES.md"), "utf8");
const scripts = Array.from(html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g), m => m[1]);
const source = scripts.find(script => script.includes("Re-derive the table"));
assert(source, "todo live parser script exists");

const elements = {
  rows: { innerHTML: "" },
  src: { textContent: "" }
};
const sandbox = {
  document: {
    createElement() {
      let value = "";
      return {
        set textContent(next) { value = String(next); },
        get innerHTML() {
          return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }
      };
    },
    getElementById(id) { return elements[id]; }
  },
  fetch: async function () {
    return { ok: true, text: async function () { return directives; } };
  }
};

vm.runInNewContext(source, sandbox);
setImmediate(function () {
  const rows = elements.rows.innerHTML;
  assert.strictEqual((rows.match(/<tr>/g) || []).length, 22, "live parser renders every directive");
  assert(/<tr><td>7<\/td>[\s\S]*?s-built'>BUILT<\/b>/.test(rows), "avatar status is BUILT");
  assert(/<tr><td>9<\/td>[\s\S]*?s-half'>HALF<\/b>/.test(rows), "mirror status is HALF");
  assert(/<tr><td>10<\/td>[\s\S]*?s-open'>OPEN<\/b> Not LANDED/.test(rows), "OPEN beats later Not LANDED");
  assert(/<tr><td>18<\/td>[\s\S]*?s-measured'>MEASURED<\/b>/.test(rows), "MEASURED is first-class");
  assert.strictEqual(elements.src.textContent, "live — 22 directives parsed from DIRECTIVES.md just now");
  console.log("TODO LIVE PARSER TEST: 22 canonical rows, statuses exact");
});
