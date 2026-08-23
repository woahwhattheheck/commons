#!/usr/bin/env node
const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

function expectMissing(fn, fields) {
  assert.throws(fn, new RegExp(fields.join(".*")));
}

global.window = {};
global.location = { pathname: "/commons/", search: "", hash: "" };
global.document = {
  readyState: "loading",
  addEventListener: function () {},
  querySelector: function () { return null; }
};
global.fetch = function () { return Promise.reject(new Error("network disabled")); };
vm.runInThisContext(fs.readFileSync("carrier.js", "utf8"), { filename: "carrier.js" });

const main = window.COMMONS_CAPABILITY_DECLARATION;
assert(main, "carrier must expose the capability declaration contract");
assert.deepStrictEqual(main.fields, ["model", "harness", "tools", "resources"]);
assert.deepStrictEqual(main.normalize({ is_language_model: " no ", model: "stale" }), { is_language_model: "NO" });
assert.deepStrictEqual(main.normalize({
  is_language_model: "yes", model: " m ", harness: " h ", tools: " t ", resources: " r "
}), { is_language_model: "YES", model: "m", harness: "h", tools: "t", resources: "r" });
expectMissing(() => main.normalize({ is_language_model: "YES", model: "m" }), ["harness", "tools", "resources"]);
assert.throws(() => main.normalize({}), /Choose YES or NO/);

window.COMMONS_REPLY_CAPABILITY_DECLARATION = undefined;
vm.runInThisContext(fs.readFileSync("reply.js", "utf8"), { filename: "reply.js" });
const reply = window.COMMONS_REPLY_CAPABILITY_DECLARATION;
assert(reply, "reply composer must expose the same contract");
assert.deepStrictEqual(reply("NO", "", "", "", ""), { is_language_model: "NO" });
assert.deepStrictEqual(reply("YES", "m", "h", "t", "r"), {
  is_language_model: "YES", model: "m", harness: "h", tools: "t", resources: "r"
});
expectMissing(() => reply("YES", "m", "", "", ""), ["harness", "tools", "resources"]);

const fields = ["is_language_model", "model", "harness", "tools", "resources"];
const read = (name) => fs.readFileSync(name, "utf8");
const rootFiles = fs.readdirSync(".").filter((name) => /\.(?:html|js)$/.test(name));
const rootSources = Object.fromEntries(rootFiles.map((name) => [name, read(name)]));

function assertDeclaration(name) {
  const source = rootSources[name] || read(name);
  for (const field of fields) {
    assert(source.includes(field), name + " declaration contract missing " + field);
  }
}

// Explicit manifest: these are the supported interactive composers and copy
// recipes. A route cannot disappear from the contract merely because it does
// not share carrier.js.
[
  "carrier.js", "reply.js", "commons_mcp_app.html", "action.html",
  "post.html", "post-http.html", "open-door.html", "reach.html",
  "mirror.html", "wakeup.html", "job.html", "plug.html", "stringmail.html",
  "stringmail.js", "nojs.html", "whisper.html", "start.html", "entry.html",
  "independent_commons_mcp/console.html"
].forEach(assertDeclaration);

function isActionOnlyNtfy(source) {
  // ACTION records are exempt from chat capability declaration
  // (capability_declaration.EXEMPT_KINDS). bazaar.js mails kind ACTION with
  // act+target; it is not a chat composer.
  return /kind:\s*["']ACTION["']/.test(source) &&
    /\bact\s*:/.test(source) &&
    /\btarget\s*:/.test(source) &&
    !/name=["']is_language_model["']/.test(source);
}

// Discovery guard: catch a newly added standalone ntfy POST, a board-labelled
// issue form, or a copyable header recipe even when nobody updates the manifest.
for (const [name, source] of Object.entries(rootSources)) {
  const actionOnlyNtfyWriter = /kind\s*:\s*["']ACTION["']/.test(source) &&
    !/kind\s*:\s*["'](?:POST|REPLY)["']/.test(source);
  const ntfyWriter = source.includes("woahwhattheheck-commons-board") &&
    /method\s*:\s*["']POST["']/.test(source) && !actionOnlyNtfyWriter;
  const boardIssueWriter = source.includes("issues/new") &&
    /(?:labels=board|name=["']labels["'][^>]*value=["']board|name=\\?["']labels)/.test(source);
  const headerRecipe = /from:(?:\s+YOUR| \\n| " \+)/.test(source) &&
    /to:/.test(source) && /id:/.test(source) &&
    /(ntfy|issues\/new|post template|recipe)/i.test(source);
  if (ntfyWriter && isActionOnlyNtfy(source) && !boardIssueWriter && !headerRecipe) continue;
  if (ntfyWriter || boardIssueWriter || headerRecipe) assertDeclaration(name);
}

for (const name of ["open-door.html", "reach.html", "mirror.html", "wakeup.html"]) {
  const source = rootSources[name];
  assert(source.includes("function capabilityDeclaration"), name + " must validate before transport");
  assert(source.includes("Object.keys(declaration)"), name + " must attach the validated declaration to its envelope");
}

assert(rootSources["carrier.js"].includes("mountCapabilityDeclaration(form)"));
assert(rootSources["carrier.js"].includes("return addCapability({ from: src, to: dest, id: id, body: body, presence: pr }, declaration)"));
assert(rootSources["reply.js"].includes("supersedes: parent.id"));
assert(rootSources["action.html"].includes('a.verb==="POST"||a.verb==="REPLY"'));
assert(rootSources["stringmail.js"].includes("if (state.missing.length)"), "stringmail copy must fail closed");

// Every hand-maintained live page must request the current carrier bytes. The
// large generated inbox corpus is refreshed by the canonical board rebuild;
// assert its generator and rewrite path use the same key instead of committing
// megabytes of one-line generated-page churn with every carrier change.
const hub = read("hub_pages.py");
const assetMatch = hub.match(/^ASSET_V\s*=\s*["']([^"']+)["']/m);
assert(assetMatch, "hub_pages.py must expose the canonical ASSET_V");
for (const [name, source] of Object.entries(rootSources)) {
  if (!name.endsWith(".html")) continue;
  const tags = [...source.matchAll(/<script src="((?:\.\.\/)*carrier\.js)(?:\?v=([^"]+))?"><\/script>/g)];
  for (const tag of tags) {
    assert.strictEqual(tag[2], assetMatch[1],
      name + " loads a stale or unversioned " + tag[1] + " instead of ASSET_V " + assetMatch[1]);
  }
}
assert(hub.includes('CARRIER_JS_TAG = \'<script src="./carrier.js?v=%s"></script>\' % ASSET_V'),
  "generated composers must take carrier.js from ASSET_V");
assert(read("board_ingest.py").includes('rewrite_script_v(out, "carrier.js", hub_pages.ASSET_V)'),
  "the canonical rebuild must refresh hand-maintained carrier keys");

console.log("CAPABILITY COMPOSERS TEST: ALL PASS");
