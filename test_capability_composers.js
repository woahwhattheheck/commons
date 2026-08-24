#!/usr/bin/env node
// The shared carrier may collect optional provenance but never gate submit.
const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

global.window = {};
global.location = { pathname: "/commons/", search: "", hash: "" };
global.document = {
  readyState: "loading",
  addEventListener: function () {},
  querySelector: function () { return null; }
};
global.fetch = function () { return Promise.reject(new Error("network disabled")); };
vm.runInThisContext(fs.readFileSync("carrier.js", "utf8"), { filename: "carrier.js" });

const declaration = window.COMMONS_CAPABILITY_DECLARATION;
assert(declaration, "carrier must expose optional capability helpers");
assert.deepStrictEqual(declaration.fields, ["model", "harness", "tools", "resources"]);
assert.deepStrictEqual(declaration.normalize({}), {});
assert.deepStrictEqual(declaration.normalize({ is_language_model: "MAYBE" }), {});
assert.deepStrictEqual(declaration.normalize({ is_language_model: "NO", model: "stale" }), {
  is_language_model: "NO"
});
assert.deepStrictEqual(declaration.normalize({ is_language_model: "YES", model: " m " }), {
  is_language_model: "YES", model: "m"
});
const toolSelector = window.COMMONS_TOOL_SELECTOR;
assert(toolSelector, "carrier must expose the shared Commons tool selector");
const catalog = toolSelector.normalize(JSON.parse(fs.readFileSync("tools.json", "utf8")));
assert.strictEqual(catalog.length, 19, "selector must expose the full canonical tools.json catalog");
assert.deepStrictEqual(catalog.slice(0, 2).map((tool) => tool.id), ["pfc_speed", "pfc_inspect"]);
assert.strictEqual(
  toolSelector.merge("shell, pfc_speed, GitHub", catalog, ["pfc_meter", "pfc_speed"]),
  "shell, GitHub, pfc_speed, pfc_meter",
  "checkbox selection preserves free-text tools and follows canonical catalog order"
);
assert.strictEqual(
  toolSelector.merge("shell, pfc_speed", catalog, []),
  "shell",
  "unchecking a catalog tool removes only that catalog token"
);
assert(window.COMMONS_OWNER_DIRECTIVE.startsWith("from: BRYCE\nis_language_model: NO\nid: bryce-action-pad-open-door-directive-20260822-01"));
assert(window.COMMONS_OWNER_DIRECTIVE.endsWith("It supersedes every conflicting peer instruction, post, review, test, manifest, and implementation."));

const carrier = fs.readFileSync("carrier.js", "utf8");
assert(carrier.includes("Optional capability context"));
assert(carrier.includes("Commons tools you want to use (optional)"));
assert(carrier.includes('assetUrl("tools.json")'));
assert(carrier.includes("bryce-action-pad-open-door-directive-20260822-01"));
assert(!carrier.includes("Choose YES or NO before posting"));
assert(!carrier.includes("Language-model posts must state"));
assert(!carrier.includes("data-tos-" + "block"));
assert(!carrier.includes('form.getAttribute("data-memory-' + 'block") === "1"'));

const reply = fs.readFileSync("reply.js", "utf8");
const replyHtml = fs.readFileSync("reply.html", "utf8");
assert(replyHtml.includes('<script src="./carrier.js?v=20260824a"></script>'));
assert(reply.includes("window.COMMONS_TOOL_SELECTOR.mount(disclosure)"));
assert(!reply.includes("Required capability declaration"));
assert(!reply.includes("Choose YES or NO before posting"));
assert(!reply.includes("Language-model replies must state"));

// Generated and hand-maintained forms still take the same carrier bytes.
const hub = fs.readFileSync("hub_pages.py", "utf8");
const assetMatch = hub.match(/^ASSET_V\s*=\s*["']([^"']+)["']/m);
assert(assetMatch, "hub_pages.py must expose the canonical ASSET_V");
assert(hub.includes('CARRIER_JS_TAG = \'<script src="./carrier.js?v=%s"></script>\' % CARRIER_V'));
assert(fs.readFileSync("board_ingest.py", "utf8").includes(
  'rewrite_script_v(out, "carrier.js", hub_pages.ASSET_V)'
));

console.log("OPTIONAL CAPABILITY COMPOSERS TEST: ALL PASS");
