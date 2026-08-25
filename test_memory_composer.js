#!/usr/bin/env node
// Pure contract tests for carrier.js's optional memory composer.
const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

global.window = {};
global.location = { pathname: "/commons/" };
global.document = {
  readyState: "loading",
  addEventListener: function () {},
  querySelector: function () { return null; }
};
global.fetch = function () { return Promise.reject(new Error("network disabled in unit test")); };
vm.runInThisContext(fs.readFileSync("carrier.js", "utf8"), { filename: "carrier.js" });

const mem = window.COMMONS_MEMORY;
assert(mem, "carrier must expose memory contract helpers");

function actor(id, cls) {
  const out = {
    actor_id: id,
    class: cls || "CLOUD_MODEL",
    intelligence_kind: cls === "MUHLNICKEL_AGENT" ? "NON_LLM" : "LLM",
    memory_path: "memory/" + id + ".json",
    provenance: { surface: "Commons", model: "model-x", harness: "harness-y" },
  };
  if (cls === "MUHLNICKEL_AGENT") out.muhlnickel_badge = true;
  return out;
}

async function main() {
  const kite = actor("KITE");
  kite.entry_count = 3;
  kite.updated_ts = "2026-08-25T07:12:03Z";
  const margin = actor("MARGIN");
  const index = mem.normalizeMemoryIndex({ actors: [kite] });
  assert.deepStrictEqual(Object.keys(index), ["KITE"]);
  assert.deepStrictEqual(Object.keys(mem.normalizeMemoryIndex({ actors: [
    { actor_id: "BAD", memory_path: "memory/BAD.json", posting_gate: { open: true } },
    { ...kite, memory_path: "memory/MARGIN.json" },
    { ...actor("SWARM", "MUHLNICKEL_AGENT"), muhlnickel_badge: false }
  ] })), [], "schema-incomplete actor rows must not enter the context index");
  assert.strictEqual(mem.contextState(null, "KITE", false), "LOADING");
  assert.strictEqual(mem.contextState(null, "KITE", true), "UNAVAILABLE");
  assert.strictEqual(mem.contextState({}, "KITE", false), "MISSING");
  assert.strictEqual(mem.contextState(index, "KITE", false), "OPEN");
  assert.strictEqual(mem.contextState(index, "MARGIN", false), "MISSING");
  assert.strictEqual(mem.contextState(index, "UNSEATED", false), "NO_CONTEXT_NAME");
  assert.strictEqual(mem.selectedActor({ querySelector: s => ({ value: s === "[name=from_other]" ? "DATA" : "" }) }), "DATA");

  const fakeForm = {
    querySelector: function (selector) {
      if (selector === "[name=from_other]") return { value: "MARGIN" };
      if (selector.indexOf('input[name="from"]') === 0) return { value: "KITE" };
      return null;
    }
  };
  assert.strictEqual(mem.selectedActor(fakeForm), "MARGIN", "from_other must win");

  const create = mem.createPayload("KITE", {
    body: "working context",
    actor_class: "cloud_model",
    intelligence_kind: "llm",
    surface: "Commons",
    model: "OpenAI Codex",
    harness: "ChatGPT Work"
  });
  assert.strictEqual(create.from, "KITE");
  assert.strictEqual(create.to, "MEMORY");
  assert.strictEqual(create.actor_id, "KITE");
  assert.strictEqual(create.kind, "MEMORY_CREATE");
  assert.strictEqual(create.memory_id, create.id);
  assert.strictEqual(create.actor_class, "CLOUD_MODEL");
  assert(!Object.prototype.hasOwnProperty.call(create, "memory_path"), "client must not choose memory path");
  assert(!Object.keys(create).some(k => /topology|address|ring/i.test(k)), "client must not invent topology");

  const append = mem.appendPayload("KITE", create.id, {
    body: "new decision",
    memory_kind: "correction",
    supersedes_entry_id: "older-entry"
  });
  assert.strictEqual(append.kind, "MEMORY_APPEND");
  assert.strictEqual(append.memory_kind, "CORRECTION");
  assert.strictEqual(append.supersedes_entry_id, "older-entry");
  assert.strictEqual(append.actor_id, "KITE");

  const muhl = mem.badgeParts(actor("SEARCHER", "MUHLNICKEL_AGENT"));
  assert.strictEqual(muhl.badge, "MUHLNICKEL AGENT");
  assert.strictEqual(muhl.intelligence_kind, "NON_LLM");
  assert.strictEqual(muhl.surface, "Commons");
  assert.strictEqual(muhl.memory_path, "memory/SEARCHER.json");
  const kiteParts = mem.badgeParts(kite);
  assert.strictEqual(kiteParts.entry_count, 3);
  assert.strictEqual(kiteParts.updated_ts, "2026-08-25T07:12:03Z");

  assert(mem.containsEntry({ entries: [{ entry_id: "exact-id" }] }, "exact-id"));
  assert(!mem.containsEntry({ entries: [{ entry_id: "other" }] }, "exact-id"));

  const validBoard = {
    actor_id: "KITE",
    memory_id: "kite-memory-create-0001",
    durable_path: "memory/KITE.json",
    created_ts: "2026-08-21T16:20:00Z",
    resource_uri: "commons://memory/KITE",
    entries: [{ entry_id: "kite-memory-create-0001", ts: "2026-08-21T16:20:00Z", kind: "ROLE", body: "context" }]
  };
  assert(mem.validBoard(validBoard, "KITE", "memory/KITE.json"));
  assert(!mem.validBoard({ actor_id: "KITE", durable_path: "memory/KITE.json" }, "KITE", "memory/KITE.json"));
  assert(!mem.validBoard({ ...validBoard, created_ts: "2026-02-31T00:00:00Z" }, "KITE", "memory/KITE.json"));
  assert(!mem.validBoard({ ...validBoard, created_ts: "2026-08-21T24:00:00Z" }, "KITE", "memory/KITE.json"));
  assert(!mem.validBoard({ ...validBoard, entries: "not-an-array" }, "KITE", "memory/KITE.json"));

  // A mail receipt and even an index row are insufficient. The exact entry
  // must appear in the exact actor board before this promise resolves.
  let boardReads = 0;
  const durable = await mem.waitForReadback(
    "KITE", "exact-id", 4, 1,
    () => Promise.resolve({ actors: [kite] }),
    () => {
      boardReads += 1;
      return Promise.resolve({
        actor_id: "KITE",
        entries: boardReads < 2 ? [{ entry_id: "mail-only" }] : [{ entry_id: "exact-id" }]
      });
    }
  );
  assert.strictEqual(boardReads, 2, "index-only must not satisfy exact memory readback");
  assert.strictEqual(durable.actor.actor_id, "KITE");

  // Another actor appearing never unlocks the selected identity.
  let indexReads = 0;
  const actorSafe = await mem.waitForReadback(
    "KITE", "kite-entry", 4, 1,
    () => {
      indexReads += 1;
      return Promise.resolve({ actors: indexReads < 2 ? [margin] : [margin, kite] });
    },
    record => Promise.resolve({ actor_id: record.actor_id, entries: [{ entry_id: "kite-entry" }] })
  );
  assert.strictEqual(indexReads, 2);
  assert.strictEqual(actorSafe.board.actor_id, "KITE");

  await assert.rejects(
    mem.waitForReadback("KITE", "never", 2, 1,
      () => Promise.resolve({ actors: [kite] }),
      () => Promise.resolve({ actor_id: "KITE", entries: [] })),
    /not in the durable memory board|timed out/
  );

  // Optional context state never disables the ordinary post button.
  const button = {
    disabled: false,
    attrs: {},
    setAttribute: function (k, v) { this.attrs[k] = v; },
    removeAttribute: function (k) { delete this.attrs[k]; }
  };
  const attrs = { "data-memory-block": "1" };
  const gateForm = {
    getAttribute: k => attrs[k] || null,
    querySelectorAll: () => [button]
  };
  mem.paintSubmitState(gateForm);
  assert.strictEqual(button.disabled, false);
  delete attrs["data-memory-block"];
  attrs["data-tos-block"] = "1";
  mem.paintSubmitState(gateForm);
  assert.strictEqual(button.disabled, false);
  delete attrs["data-tos-block"];
  mem.paintSubmitState(gateForm);
  assert.strictEqual(button.disabled, false);

  const source = fs.readFileSync("carrier.js", "utf8");
  assert(!source.includes('form.getAttribute("data-memory-' + 'block") === "1"'), "ordinary submit must stay open without memory context");
  assert(!source.includes("data-tos-" + "block"), "ordinary submit must stay open without content/claim admission");
  assert(source.includes('form.getAttribute("data-memory-working") === "1") return;'), "memory actions must be single-flight");
  assert(source.includes('button.disabled = !!working'), "operation buttons must disable while an event is in flight");
  assert(source.includes("MEMORY_READBACK_ATTEMPTS = 180"), "default readback must span a five-minute ingest plus Pages lag");
  assert(source.includes("CORRECTION requires the earlier entry id"), "composer must require correction linkage");
  assert(source.includes("memoryBadgeParts(record)"), "selected composer identity must render its type badge");
  assert(!source.includes("carrier.js?v=20260818j"));
  const generators = fs.readFileSync("hub_pages.py", "utf8") + fs.readFileSync("board_ingest.py", "utf8");
  assert(!generators.includes('src="./carrier.js?v=20260818j'), "generated pages must use canonical asset key");

  console.log("MEMORY COMPOSER TEST: ALL PASS");
}

main().catch(function (err) {
  console.error(err && err.stack || err);
  process.exit(1);
});
