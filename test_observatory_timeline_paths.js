/* Run the actual renderer in a small DOM harness; no browser/network dependency. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

class Element {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
    this.listeners = {};
    this._text = "";
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(""); }
  set innerHTML(value) { this.textContent = value; }
  appendChild(child) { this.children.push(child); return child; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
}

async function main() {
  const ids = ["snapshot-status", "refresh-snapshot", "refresh-status", "coverage-note",
    "source-coverage", "cockpit-lines", "metrics", "board-motion", "session-rows",
    "presence-rows", "work-rows", "collision-list", "attention-list", "timeline-filters",
    "timeline", "briefing", "handoff", "economy", "routes"];
  const nodes = Object.fromEntries(ids.map(id => [id, new Element(id)]));
  const row = (id, extra) => ({ts: "2026-09-06T23:00:00Z", kind: "CHECKPOINT",
    session_id: id, task_id: "task-" + id, evidence: [], ...extra});
  let fixture = {
    schema: "commons-observatory/v0.1", now: "2026-09-06T23:00:00Z", stale_after_seconds: 600,
    timeline: [
      row("multi", {path: "src/first.py", claimed_paths: ["src/first.py", "tests/secondary.py", "docs/third.md"]}),
      row("legacy", {path: "legacy/only.py"}),
      row("empty", {path: "UNKNOWN", claimed_paths: []}),
      row("fallback", {path: "fallback/only.py", claimed_paths: null}),
    ],
  };
  let requests = 0;
  let failure = null;
  const pendingTimers = new Map();
  let timerId = 0;
  const context = vm.createContext({
    console, Date, AbortController,
    document: {
      hidden: false,
      getElementById: id => nodes[id],
      createElement: tag => new Element(tag),
      addEventListener() {},
    },
    window: {},
    FormData: class { constructor(values) { this.values = values; } get(key) { return this.values[key] || ""; } },
    setTimeout: (callback, delay) => { pendingTimers.set(++timerId, {callback, delay}); return timerId; },
    clearTimeout: id => pendingTimers.delete(id),
    setInterval() {},
    fetch: async () => {
      requests++;
      if (failure) throw failure;
      return {ok: true, json: async () => fixture};
    },
  });
  const source = fs.readFileSync(path.join(__dirname, "observatory.js"), "utf8");
  vm.runInContext(source, context, {filename: "observatory.js"});
  const settle = () => new Promise(resolve => setImmediate(resolve));
  await settle();
  assert.equal(context.window.COMMONS_OBSERVATORY, fixture, "real renderer should load fixture");
  const matching = () => nodes.timeline.children.filter(li => li.className !== "empty").map(li => {
    const match = /session ([^ ]+) · task/.exec(li.textContent);
    assert.ok(match, "timeline row should contain its session");
    return match[1];
  });
  let checks = 0;
  function select(values, expected, message) {
    nodes["timeline-filters"].listeners.submit({preventDefault() {}, target: values});
    assert.deepEqual(matching(), expected, message);
    checks++;
  }
  select({path: "tests/secondary.py"}, ["multi"], "secondary path should match");
  select({path: "src/first.py"}, ["multi"], "first path remains searchable");
  select({path: "SECONDARY"}, ["multi"], "path search is case-insensitive");
  select({path: "docs/third"}, ["multi"], "third path supports substring search");
  select({path: "missing/file.py"}, [], "unrelated path must not match");
  select({path: "first.py tests"}, [], "do not match across joined filenames");
  select({path: "first.py,tests"}, [], "do not match across comma-joined filenames");
  select({path: "legacy/only"}, ["legacy"], "legacy single-path bake remains readable");
  select({path: "fallback/only"}, ["fallback"], "null list falls back to legacy path");
  select({path: "UNKNOWN"}, ["empty"], "empty path list preserves UNKNOWN behavior");
  select({path: "secondary", kind: "LANDING"}, [], "other filters still combine with paths");
  select({path: "secondary", kind: "CHECKPOINT", session: "multi"}, ["multi"], "combined matching filters retain row");
  nodes["timeline-filters"].listeners.reset();
  for (const [id, timer] of pendingTimers) {
    if (timer.delay === 0) { pendingTimers.delete(id); timer.callback(); }
  }
  assert.deepEqual(matching(), ["multi", "legacy", "empty", "fallback"], "reset restores all rows");
  checks++;
  select({path: "secondary"}, ["multi"], "select before refresh");
  fixture = {...fixture, timeline: [row("refreshed", {path: "src/new.py", claimed_paths: ["src/new.py", "tests/secondary.py"]})]};
  await nodes["refresh-snapshot"].listeners.click();
  assert.deepEqual(matching(), ["refreshed"], "refresh preserves active multi-path filter");
  checks++;
  failure = new Error("fixture network failure");
  await nodes["refresh-snapshot"].listeners.click();
  assert.deepEqual(matching(), ["refreshed"], "failed refresh preserves last successful data and filter");
  assert.equal(nodes["refresh-snapshot"].disabled, false, "failed refresh re-enables the button");
  checks++;
  assert.equal(requests, 3, "filtering and reset must not create network requests");
  checks++;
  console.log(`PASS ${checks} timeline path renderer checks`);
}

main().catch(error => { console.error(error); process.exitCode = 1; });
