"use strict";

// Test-only DOM/event boundary for the *actual* app.js, not copied intake logic.
// The Python caller supplies a real loopback HTTP endpoint with an explicitly
// recording compiler-adapter spy. This is neither Chromium nor compiler proof.
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

async function run(config, appPath) {
  const requests = [];
  const elements = new Map();
  class Element {
    constructor(tag = "div") {
      this.tagName = tag; this.children = []; this.dataset = {}; this.value = "";
      this.nodeType = 1; this.className = "";
      this.disabled = false; this.files = []; this.textContent = "";
      this.listeners = new Map(); this.attributes = {};
    }
    get childElementCount() { return this.children.filter(child => child.nodeType === 1).length; }
    replaceChildren(...children) {
      if (this.children.some(child => child === document.activeElement || child.contains?.(document.activeElement))) document.activeElement = document.body;
      this.children = children;
      if (this.tagName === "select") this.value = children[0]?.value || "";
    }
    append(...children) { this.children.push(...children); }
    contains(node) { return this === node || this.children.some(child => child === node || child.contains?.(node)); }
    querySelectorAll(selector) {
      if (!/^\.[\w-]+$/.test(selector)) throw new Error(`Unsupported fixture selector: ${selector}`);
      const matches = [];
      for (const child of this.children) {
        if (child.nodeType !== 1) continue;
        if (child.className.split(/\s+/).includes(selector.slice(1))) matches.push(child);
        matches.push(...child.querySelectorAll(selector));
      }
      return matches;
    }
    focus() { if (!this.disabled) document.activeElement = this; }
    setAttribute(key, value) { this.attributes[key] = value; }
    addEventListener(kind, fn) { this.listeners.set(kind, fn); }
    async click() { if (!this.disabled) return this.listeners.get("click")?.(); }
  }
  const nativeFetch = globalThis.fetch;
  let context;
  const document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, new Element());
      return elements.get(id);
    },
    createElement(tag) { return new Element(tag); },
    createTextNode(value) { return { nodeType: 3, textContent: String(value) }; },
    body: new Element("body")
  };
  document.activeElement = document.body;
  const sandbox = {
    document,
    Option: function(label, value) { return Object.assign(new Element("option"), { textContent: label, value }); },
    Blob, TextEncoder, TextDecoder, URL, URLSearchParams, location: { search: "" }, setTimeout,
    fetch: async (url, options) => {
      requests.push({ url, body: options.body, credentials: options.credentials, cache: options.cache });
      if (config.network_error) throw new Error("synthetic transport unavailable");
      const response = await nativeFetch(new URL(url, config.origin), {
        ...options, headers: { ...options.headers, Origin: config.origin }
      });
      if (config.race === "reset_response") vm.runInContext("resetWorkbench()", context);
      if (config.race === "demo_response") vm.runInContext("installReport(syntheticReport())", context);
      return response;
    }
  };
  sandbox.window = sandbox;
  context = vm.createContext(sandbox);
  // Active draft preservation is part of real replacement handling. Load the
  // actual shared validators so this transport fixture obeys that same contract.
  for (const helper of ["handoff.js", "handoff_import.js"]) {
    const helperPath = path.join(path.dirname(appPath), helper);
    vm.runInContext(fs.readFileSync(helperPath, "utf8"), context, { filename: helperPath });
  }
  vm.runInContext(fs.readFileSync(appPath, "utf8"), context, { filename: appPath });

  function file(encoded, options = {}) {
    const bytes = Buffer.from(encoded, "base64");
    const blob = new Blob([bytes]);
    const read = async (method) => {
      if (options.read_error) throw new Error("synthetic file read error");
      if (config.race === "reset_file") vm.runInContext("resetWorkbench()", context);
      return blob[method]();
    };
    return {
      size: options.declared_size ?? bytes.length,
      text: () => read("text"),
      arrayBuffer: () => read("arrayBuffer")
    };
  }
  if (!config.omit_candidate) elements.get("candidateFile").files = [file(config.candidate, config.candidate_options)];
  if (!config.omit_authority) elements.get("authorityFile").files = [file(config.authority, config.authority_options)];
  // Exercise replacement semantics: active authority and notes clear on a failed
  // replacement; its valid tab snapshot remains separate. This is synthetic.
  vm.runInContext("installReport(syntheticReport()); state.notes.set(keyFor(state.cells[0]),'older draft');", context);
  await elements.get("inspectBtn").click();
  const state = JSON.parse(vm.runInContext(`JSON.stringify({
    receipt:state.report?.receipt_sha256 || null,
    synthetic:state.report?.synthetic_demo ?? null,
    notes:[...state.notes], cells:state.cells.length
  })`, context));
  return {
    requests, state,
    error: elements.get("error").textContent,
    disabled: Object.fromEntries(["inspectBtn", "exportBtn", "markdownBtn", "importDraftBtn"]
      .map(id => [id, elements.get(id).disabled]))
  };
}

if (require.main === module) {
  const appPath = path.resolve(process.argv[2] || path.join(__dirname, "app.js"));
  let data = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", chunk => { data += chunk; });
  process.stdin.on("end", async () => {
    try { console.log(JSON.stringify(await run(JSON.parse(data), appPath))); }
    catch (err) { console.error(err.stack || String(err)); process.exitCode = 1; }
  });
}
module.exports = { run };
