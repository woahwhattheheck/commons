// INQUISITOR order 034: committed test artifact for the hard byte-cap.
// Runs the SHIPPED board.js with only a test-export line appended.
// Covers: exact-cap accept, cap+1 discard, slow-stream timeout, missing
// stream, missing AbortController, read error, durable-only render, cache token.
// The timeout case waits out the real 8s timer; full run is ~10s.
const fs = require("fs");
const path = require("path");
const HERE = __dirname;

let src = fs.readFileSync(path.join(HERE, "board.js"), "utf8");
if (src.includes("isVerificationLoop") || src.includes("VERIFICATION_LOOP")) {
  console.error("FAIL: board.js still contains the bot/writing-style blocker");
  process.exit(1);
}
src = src.replace(
  "return { load: load, render: render };",
  "return { load: load, render: render, _t: { parseNtfy: parseNtfy, boundedBody: boundedBody, liveFetch: liveFetch, loadHidden: loadHidden, cache: cache, NTFY_MAX_BYTES: NTFY_MAX_BYTES } };"
);
if (!src.includes("_t:")) { console.error("FAIL: export hook not applied"); process.exit(1); }

global.window = {};
global.document = {
  readyState: "complete",
  getElementById: () => null,
  createElement: () => ({ style: {}, setAttribute() {}, addEventListener() {}, remove() {} }),
  addEventListener: () => {},
  body: null,
};
global.fetch = () => Promise.reject(new Error("fetch not stubbed"));
eval(src);
const T = global.window.COMMONS_BOARD._t;
const enc = new TextEncoder();

function streamResponse(chunks, readImpl) {
  let i = 0;
  const reader = {
    cancelled: false,
    pending: null,
    read() {
      if (readImpl) return readImpl(this);
      return Promise.resolve(i < chunks.length ? { done: false, value: chunks[i++] } : { done: true });
    },
    cancel() { this.cancelled = true; if (this.pending) { this.pending({ done: true }); this.pending = null; } },
  };
  return { ok: true, headers: { get: () => null }, body: { getReader: () => reader }, _reader: reader };
}

async function main() {
  // 1. exactly 262144 bytes: ACCEPTED (cap is inclusive)
  const exact = streamResponse([enc.encode("x".repeat(131072)), enc.encode("y".repeat(131072))]);
  const r1 = await T.boundedBody(exact, null, () => {}, { reader: null, timedOut: false });
  if (r1 === null || r1.length !== 262144) { console.error("FAIL exact-cap accept"); process.exit(1); }
  console.log("PASS 262144 accepted");

  // 2. 262145 bytes: DISCARD (null), reader cancelled
  const over = streamResponse([enc.encode("x".repeat(131072)), enc.encode("y".repeat(131073))]);
  const r2 = await T.boundedBody(over, { abort() {} }, () => {}, { reader: null, timedOut: false });
  if (r2 !== null || !over._reader.cancelled) { console.error("FAIL cap+1 discard"); process.exit(1); }
  console.log("PASS 262145 discarded, reader cancelled");

  // 2b. the six relay readers share one allowance. Two individually safe
  // bodies must not each receive a fresh cap inside the same attempt.
  const shared = { cap: 10, spent: 0 };
  const hostA = streamResponse([enc.encode("123456")]);
  const hostB = streamResponse([enc.encode("abcde")]);
  const a = await T.boundedBody(hostA, null, () => {}, { reader: null, timedOut: false }, shared);
  const b = await T.boundedBody(hostB, { abort() {} }, () => {}, { reader: null, timedOut: false }, shared);
  if (a !== "123456" || b !== null || shared.spent !== 11 || !hostB._reader.cancelled) {
    console.error("FAIL aggregate relay budget"); process.exit(1);
  }
  console.log("PASS relay readers share one aggregate byte budget");

  // 3. missing stream: fail closed (null), no text() call possible
  const noStream = { ok: true, headers: { get: () => "10" }, text: () => { throw new Error("text() must never be called"); } };
  const r3 = await T.boundedBody(noStream, null, () => {}, { reader: null, timedOut: false });
  if (r3 !== null) { console.error("FAIL missing-stream fail-closed"); process.exit(1); }
  console.log("PASS missing stream fails closed");

  // 4. read error: liveFetch catch path clears cache.live (durable-only render)
  T.cache.live = [{ id: "stale" }];
  global.fetch = () => Promise.resolve(streamResponse(null, () => Promise.reject(new Error("boom"))));
  await T.liveFetch();
  if (T.cache.live.length !== 0) { console.error("FAIL read-error durable-only"); process.exit(1); }
  console.log("PASS read error clears live overlay (durable-only render)");

  // 5. missing AbortController: fail closed BEFORE fetch
  const AC = global.AbortController;
  delete global.AbortController;
  let fetched = false;
  global.fetch = () => { fetched = true; return Promise.reject(new Error("must not fetch")); };
  T.cache.live = [{ id: "stale2" }];
  await T.liveFetch();
  global.AbortController = AC;
  if (fetched || T.cache.live.length !== 0) { console.error("FAIL no-AbortController fail-closed"); process.exit(1); }
  console.log("PASS missing AbortController fails closed pre-fetch");

  // 5b. transient hidden.json failures retain the last known moderation map;
  // only a valid object response replaces it, including a legitimate {}.
  T.cache.hidden = { "hidden-post": 1 };
  global.fetch = () => Promise.reject(new Error("temporary network miss"));
  await T.loadHidden();
  if (!T.cache.hidden["hidden-post"]) { console.error("FAIL hidden map lost on network miss"); process.exit(1); }
  global.fetch = () => Promise.resolve({ ok: false });
  await T.loadHidden();
  if (!T.cache.hidden["hidden-post"]) { console.error("FAIL hidden map lost on HTTP miss"); process.exit(1); }
  global.fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  await T.loadHidden();
  if (Object.keys(T.cache.hidden).length !== 0) { console.error("FAIL valid empty hidden map did not clear"); process.exit(1); }
  console.log("PASS hidden map survives transient failure and clears only on valid {}");

  // 5c. an empty filtered result is also stable DOM. The poll must not rewrite
  // the identical no-match markup every 15 seconds.
  let emptyWrites = 0;
  let emptyMarkup = "";
  const emptyHost = {
    getAttribute() { return ""; },
    querySelector() { return null; },
    set innerHTML(v) { emptyWrites++; emptyMarkup = v; },
    get innerHTML() { return emptyMarkup; },
  };
  T.cache.host = emptyHost;
  T.cache.durable = [];
  T.cache.live = [];
  T.cache.painted = "";
  global.window.COMMONS_BOARD.render();
  global.window.COMMONS_BOARD.render();
  if (emptyWrites !== 1) { console.error("FAIL identical no-match repaint: " + emptyWrites); process.exit(1); }
  console.log("PASS identical no-match state does not repaint");

  // 6. slow stream: timer cancels the held reader, overlay dropped (waits ~8s)
  const slows = [];
  global.fetch = () => {
    const slow = streamResponse(null, (self) => new Promise((resolve) => { self.pending = resolve; }));
    slows.push(slow);
    return Promise.resolve(slow);
  };
  T.cache.live = [{ id: "stale3" }];
  const t0 = Date.now();
  await T.liveFetch();
  const secs = (Date.now() - t0) / 1000;
  if (slows.length !== 6 || !slows.every((slow) => slow._reader.cancelled) || T.cache.live.length !== 0) {
    console.error("FAIL slow-stream timeout"); process.exit(1);
  }
  console.log("PASS slow streams: all relay readers cancelled after " + secs.toFixed(1) + "s, overlay dropped");

  // 7. cache token: landing references exactly one board.js token, the current one
  // only real script references count — baked post bodies may quote old tokens.
  // The expected token comes from hub_pages.ASSET_V — a literal here goes stale
  // the day the key rolls, which is exactly what this check exists to catch.
  const hub = fs.readFileSync(path.join(HERE, "hub_pages.py"), "utf8");
  const av = (hub.match(/^ASSET_V\s*=\s*"([A-Za-z0-9]+)"/m) || [])[1];
  if (!av) { console.error("FAIL cache token: ASSET_V not found in hub_pages.py"); process.exit(1); }
  const idx = fs.readFileSync(path.join(HERE, "index.html"), "utf8");
  const tokens = idx.match(/<script src="\.\/board\.js\?v=[A-Za-z0-9]+"/g) || [];
  if (tokens.length !== 1 || !tokens[0].includes("v=" + av)) {
    console.error("FAIL cache token: " + JSON.stringify(tokens) + " expected v=" + av); process.exit(1);
  }
  const headTok = idx.match(/<script src="\.\/head\.js\?v=[A-Za-z0-9]+"/g) || [];
  if (headTok.length !== 1 || !headTok[0].includes("v=" + av)) {
    console.error("FAIL head.js token: " + JSON.stringify(headTok) + " expected v=" + av); process.exit(1);
  }
  const headAt = idx.indexOf('src="./head.js?v=' + av);
  const boardAt = idx.indexOf('src="./board.js?v=' + av);
  if (headAt < 0 || boardAt < 0 || headAt > boardAt) {
    console.error("FAIL head.js must be a static tag before board.js"); process.exit(1);
  }
  console.log("PASS cache token is board.js?v=" + av + ", head.js before board.js");

  console.log("ALL OVERLAY TESTS PASS · NTFY_MAX_BYTES = " + T.NTFY_MAX_BYTES);
}

main().catch((e) => { console.error("FAIL:", e); process.exit(1); });
