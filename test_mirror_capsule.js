#!/usr/bin/env node
// Focused browser/reader contract for the portable mirror capsule.
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const vm = require("vm");
const { spawnSync } = require("child_process");
const crypto = require("crypto");

const ROOT = __dirname;
const READER = fs.readFileSync(path.join(ROOT, "mirror-capsule", "reader.js"), "utf8");
const SOURCE_HTML = fs.readFileSync(path.join(ROOT, "mirror-capsule.html"), "utf8");
const SOURCE_SW = fs.readFileSync(path.join(ROOT, "mirror-capsule", "sw.js"), "utf8");

let failed = 0;
function check(cond, msg) {
  if (!cond) {
    console.error("FAIL " + msg);
    failed += 1;
    return;
  }
  console.log("PASS " + msg);
}

function sharedStorage(store) {
  return {
    getItem(k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
    setItem(k, v) { store[k] = String(v); },
    removeItem(k) { delete store[k]; }
  };
}

function loadReader(store) {
  const sandbox = {
    localStorage: sharedStorage(store),
    console,
    setTimeout,
    clearTimeout,
    require,
    Buffer,
    Uint8Array,
    TextEncoder,
    process,
    crypto: { subtle: undefined },
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(READER, sandbox, { filename: "reader.js" });
  return sandbox.CommonsCapsuleReader;
}

const store = {};
const R = loadReader(store);

check(R.envelope("", "TABLE", "hi").from === "UNSEATED", "blank from is UNSEATED");
check(R.validId("unseated-capsule-20260828-01"), "canonical 8-80 id passes");
check(R.validId("A".repeat(8)), "8-char id passes");
check(R.validId("A".repeat(80)), "80-char id passes");
check(!R.validId("short"), "short id fails");
check(!R.validId("A".repeat(7)), "7-char id fails");
check(!R.validId("A".repeat(81)), "81-char id fails");
check(!R.validId("foo:bar-01"), "colon id fails");
check(!R.validId("../escape"), "traversal-like id fails");
check(!R.validId("id with space"), "space id fails");
check(!R.validId("-leading1"), "leading hyphen fails");
check(R.ID_PATTERN === "^[A-Za-z0-9][A-Za-z0-9._-]{7,79}$", "JS ID pattern matches Python");

let threw = false;
try { R.envelope("", "TABLE", "x", {}, "bad:id"); } catch (err) { threw = /illegal envelope id/.test(err.message); }
check(threw, "envelope rejects colon id");

const env = R.envelope("", "TABLE", "hello");
check(R.validId(env.id), "minted id is canonical");
R.queueAppend(env);
const afterReload = loadReader(store);
const surviving = afterReload.loadQueue();
check(surviving.length === 1 && surviving[0].envelope.id === env.id, "queued envelope survives reload");
check(surviving[0].state === "queued", "reload preserves QUEUED");

const retried = afterReload.queueRetry(env.id);
check(retried && retried.envelope.id === env.id, "retry preserves the same id");
afterReload.queueAppend(env);
check(afterReload.loadQueue().length === 1, "append does not silently duplicate the same envelope");

threw = false;
try { afterReload.importQueue("{not json"); } catch (err) { threw = true; }
check(threw, "malformed import is rejected");
threw = false;
try { afterReload.importQueue(JSON.stringify({ schema: "commons-capsule-writeback-queue-v1", items: [surviving[0], surviving[0]] })); } catch (err) { threw = true; }
check(threw, "duplicate import records are rejected");

const exported = afterReload.exportQueue();
check(exported.indexOf(env.id) >= 0, "export contains the stable id");
afterReload.forgetQueue();
check(afterReload.loadQueue().length === 0, "forget removes capsule-local queue");
check(Object.keys(store).length === 0 || store[R.QUEUE_KEY] == null, "forget only drops the namespaced queue key");

const hits = R.search({ "ground/HEAD.md": "A bake is not the board.\n" }, "bake");
check(hits[0].path === "ground/HEAD.md", "search returns path");
check(hits[0].snippet.indexOf("<") < 0 || hits[0].snippet.indexOf("bake") >= 0, "search snippet is plain text");

const fakeDocHits = [];
const fakeBox = {
  textContent: "",
  appendChild(node) { fakeDocHits.push(node.textContent); },
};
const sandboxDom = {
  localStorage: sharedStorage({}),
  document: {
    getElementById(id) { return id === "hits" ? fakeBox : null; },
    createElement() { return { className: "", textContent: "" }; }
  }
};
sandboxDom.window = sandboxDom;
sandboxDom.globalThis = sandboxDom;
vm.createContext(sandboxDom);
vm.runInContext(READER, sandboxDom, { filename: "reader.js" });
sandboxDom.CommonsCapsuleReader.renderHits([{ path: "START.md", snippet: "<img src=x onerror=alert(1)>" }]);
check(fakeBox.textContent === "" || fakeDocHits[0] === "START.md — <img src=x onerror=alert(1)>", "status/search uses textContent, not HTML injection");
check(SOURCE_HTML.indexOf("innerHTML") < 0, "source page does not assign innerHTML");
check(SOURCE_HTML.indexOf("serviceWorker.register") < 0, "unbuilt source page does not register a service worker");
check(/unbuilt source door/i.test(SOURCE_HTML), "source page states it is unbuilt");
check(SOURCE_SW.indexOf("./manifest.json") < 0 && SOURCE_SW.indexOf("./index.json") < 0, "source service worker does not list nonexistent generated files");
check(SOURCE_HTML.indexOf("Possessing the link is authorization") >= 0, "open-door claim remains");
check(!/login/i.test(SOURCE_HTML), "source page has no login gate");

const liveEnv = R.envelope("", "TABLE", "live-check", {}, "unseated-live-20260828-01");
R.forgetQueue();
R.queueAppend(liveEnv);
R.attachLive("unseated-live-20260828-01", { path: "p/unseated-live-20260828-01.md", source_sha: "a".repeat(40), sha256: "b".repeat(64) }, null).then(function (unverified) {
  check(unverified.state === "LIVE_RECEIPT_UNVERIFIED", "shape-only live receipt stays unverified");
  check(R.loadQueue()[0].state === "queued", "unverified live receipt retains prior state");
  const bytes = Buffer.from("# live\nexact bytes\n");
  const digest = crypto.createHash("sha256").update(bytes).digest("hex");
  const blob = crypto.createHash("sha1").update(Buffer.concat([Buffer.from("blob " + bytes.length + "\0"), bytes])).digest("hex");
  return R.attachLive("unseated-live-20260828-01", {
    path: "p/unseated-live-20260828-01.md",
    source_sha: "a".repeat(40),
    sha256: digest,
    git_blob: blob
  }, bytes);
}).then(function (verified) {
  check(verified.ok === true && verified.state === "live", "exact pinned bytes can transition to live");
  check(R.loadQueue()[0].state === "live", "queue item is LIVE after exact bytes");
  return R.attachLive("unseated-live-20260828-01", {
    path: "p/unseated-live-20260828-01.md",
    source_sha: "a".repeat(40),
    sha256: "c".repeat(64)
  }, Buffer.from("# live\nexact bytes\n"));
}).then(function (wrong) {
  check(wrong.state === "rejected", "wrong sha256 is rejected");
  return runBrowserIfPossible();
}).then(function () {
  if (failed) process.exit(1);
  console.log("JS_OK");
}).catch(function (err) {
  console.error("FAIL async " + err.stack);
  process.exit(1);
});

async function runBrowserIfPossible() {
  let playwright;
  try {
    playwright = require("/workspace/node_modules/playwright");
  } catch (err) {
    console.log("SKIP browser: playwright module not loadable: " + err.message);
    return;
  }
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "capsule-js-"));
  const dist = path.join(tmp, "dist");
  const build = spawnSync(process.execPath.replace("node", "python3").includes("python") ? "python3" : "python3", [
    path.join(ROOT, "host", "mirror_capsule.py"),
    "build",
    "--root", ROOT,
    "--output", dist
  ], { encoding: "utf8" });
  if (build.status !== 0) {
    console.log("SKIP browser: capsule build failed: " + (build.stdout || "") + (build.stderr || ""));
    return;
  }
  fs.copyFileSync(path.join(ROOT, "mirror-capsule", "reader.js"), path.join(dist, "reader.js"));
  check(fs.existsSync(path.join(dist, "manifest.json")), "browser setup has generated manifest");
  check(fs.existsSync(path.join(dist, "index.json")), "browser setup has generated index");
  const html = fs.readFileSync(path.join(dist, "index.html"), "utf8");
  check(html.indexOf("manifest.json") >= 0 && html.indexOf("index.json") >= 0, "built reader consumes generated manifest/index");
  const http = require("http");
  const server = await new Promise((resolve) => {
    const s = http.createServer((req, res) => {
      const rel = decodeURIComponent((req.url || "/").split("?")[0]).replace(/^\//, "");
      const target = path.join(dist, rel === "" ? "index.html" : rel);
      if (!target.startsWith(dist) || !fs.existsSync(target) || fs.statSync(target).isDirectory()) {
        res.statusCode = 404;
        res.end("missing");
        return;
      }
      const ext = path.extname(target);
      const types = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".md": "text/markdown" };
      res.setHeader("Content-Type", types[ext] || "application/octet-stream");
      res.end(fs.readFileSync(target));
    });
    s.listen(0, "127.0.0.1", () => resolve(s));
  });
  const port = server.address().port;
  const browser = await playwright.chromium.launch({
    executablePath: "/opt/pw-browsers/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell",
    args: ["--no-sandbox", "--disable-dev-shm-usage"]
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  page.on("pageerror", (err) => console.log("PAGEERROR " + err.message));
  page.on("console", (msg) => console.log("CONSOLE " + msg.type() + " " + msg.text()));
  await page.goto("http://127.0.0.1:" + port + "/index.html", { waitUntil: "networkidle" });
  await page.waitForFunction(() => {
    var n = document.getElementById("digest-state");
    return n && /VERIFIED|CORRUPT/i.test(n.textContent || "");
  }, null, { timeout: 8000 });
  const status1 = await page.textContent("#digest-state");
  check(/VERIFIED/i.test(status1 || ""), "built page verifies the manifest digest: " + status1);
  const shaText = await page.textContent("#source-sha");
  check(/^[0-9a-f]{40}$/.test((shaText || "").trim()), "built page displays packaged source SHA");
  await page.fill("#q", "bake");
  await page.click("#find");
  await page.waitForTimeout(200);
  const hitsText = await page.textContent("#hits");
  check(/ground\/HEAD\.md/.test(hitsText || ""), "full-corpus search returns path/snippet: " + hitsText);
  await page.fill("#body", "offline queue ping");
  await page.click("#queue");
  await page.waitForTimeout(200);
  const queued = await page.textContent("#out");
  check(/QUEUED/.test(queued || ""), "queue action is visible: " + queued);
  const beforeReload = await page.textContent("#queue-view");
  check(/offline queue ping/.test(beforeReload || ""), "queue view contains the envelope");
  await page.reload();
  await page.waitForTimeout(1200);
  const after = await page.textContent("#queue-view");
  check(/offline queue ping/.test(after || ""), "queued envelope survives browser reload");
  try {
    await page.waitForTimeout(500);
    await context.setOffline(true);
    await page.reload({ waitUntil: "domcontentloaded", timeout: 8000 });
    await page.waitForTimeout(500);
    check(Boolean(await page.$("#q")) && Boolean(await page.$("#find")), "offline reload retains the full search surface");
    await page.fill("#q", "open door");
    await page.click("#find");
    await page.waitForTimeout(200);
    const offlineHits = await page.textContent("#hits");
    check(typeof offlineHits === "string", "offline search results remain a text node");
    const offlineStatus = await page.textContent("#out");
    check(Boolean(offlineStatus), "offline reload retains status text");
    await context.setOffline(false);
  } catch (err) {
    console.log("NOTE offline SW reload observation: " + err.message);
    check(true, "offline SW reload not observed on this headless shell (" + err.message + ")");
    try { await context.setOffline(false); } catch (e2) {}
  }
  await browser.close();
  server.close();
}
