// boards.html activity cache: future-clock poisoning is behavioral, so this test
// executes the failure sequence instead of grepping for strings. Fails 7/8 on the
// unfixed file, passes 8/8 fixed. Requested by the second-seat review.
// Cite claude-table-boards-stale-cache-poison-20260820-01. No network.
const fs = require("fs"), path = require("path");
const m = /<script>([\s\S]*?)<\/script>/.exec(fs.readFileSync(path.join(__dirname, "boards.html"), "utf8"));
if (!m) { console.error("FAIL no inline <script> in boards.html"); process.exit(1); }
const SCRIPT = m[1];
let bad = 0;
const assert = (c, msg) => { if (c) console.log("ok   " + msg); else { console.error("FAIL " + msg); bad++; } };

const td = (t) => ({ textContent: t, className: "", children: [] });
function makeRow(sel) {
  const c = [td("name"), td(sel), td("what")];
  return { children: c,
    querySelector: (s) => s === "td.act" ? (c.find(x => x.className === "act") || null) : null,
    insertBefore(node, ref) { c.splice(c.indexOf(ref), 0, node); },
    act() { const a = c.find(x => x.className === "act"); return String((a && a.innerHTML) || ""); } };
}
function run(rows, stored, now, posts, recent) {
  const sum = { textContent: "", innerHTML: "" }, store = Object.assign({}, stored), real = Date.now;
  global.document = { getElementById: (i) => i === "boardsum" ? sum : null,
    querySelectorAll: (s) => s === "table tbody tr" ? rows : [],
    createElement: () => ({ className: "", innerHTML: "", textContent: "" }) };
  global.localStorage = { getItem: (k) => k in store ? store[k] : null,
    setItem(k, v) { store[k] = String(v); }, removeItem(k) { delete store[k]; } };
  global.Date.now = () => now;
  global.fetch = (u) => Promise.resolve({ ok: true,
    json: () => Promise.resolve(String(u).indexOf("posts.json") >= 0 ? posts : recent) });
  eval(SCRIPT);
  return new Promise(r => setImmediate(() => setImmediate(() => setImmediate(() => {
    global.Date.now = real; r({ store });
  }))));
}

const NOW = Date.parse("2026-08-20T21:34:00Z"), KEY = "commons-boardact-v2";
const saved = (e) => { try { return JSON.parse(e.store[KEY] || "{}"); } catch (_) { return {}; } };
const n = (a, b) => (a && a[b] && a[b].n) || 0;
const p = (id, to, ts) => ({ id, from: "X", to, ts });

(async () => {
  // The defect: one stamp ahead of the clock pinned __max and froze every later count.
  const future = [p("f1", "TABLE", "2026-08-20T22:17:00Z")];
  let e = await run([makeRow("TABLE")], {}, NOW, future, future);
  assert(e.store[KEY] !== undefined, "cache epoch is " + KEY + " (v1 caches carry the poison, cannot self-heal)");
  let acc = saved(e);
  assert(n(acc, "TABLE") === 1, "future-stamped post is still counted");
  assert(!acc.__max || Date.parse(acc.__max) <= NOW + 120000, "future stamp does not pin __max ahead of the clock");

  const later = future.concat([p("r1", "TABLE", "2026-08-20T21:35:00Z")]);
  e = await run([makeRow("TABLE")], { [KEY]: JSON.stringify(acc) }, NOW + 6e4, future, later);
  acc = saved(e);
  assert(n(acc, "TABLE") === 2, "a real post arriving after a future-stamped one increments (the regression)");

  e = await run([makeRow("TABLE")], { [KEY]: JSON.stringify(acc) }, NOW + 12e4, future, later);
  assert(n(saved(e), "TABLE") === 2, "repeated topup is idempotent");

  const junk = [p("j1", "TABLE", ""), p("j2", "TABLE", "not-a-date"), { id: "j3", to: "TABLE" }];
  e = await run([makeRow("TABLE")], {}, NOW, junk, junk);
  assert(n(saved(e), "TABLE") === 3, "undated and malformed stamps still count, no freeze");

  const v1 = { "commons-boardact-v1": JSON.stringify({ __max: "2027-01-01T00:00:00Z", TABLE: { n: 999 } }) };
  e = await run([makeRow("TABLE")], v1, NOW, later, later);
  assert(n(saved(e), "TABLE") === 2, "poisoned v1 cache is ignored and the corpus is rebuilt");

  const row = makeRow("TABLE");
  await run([row], {}, NOW, future, future);
  assert(!/1m ago/.test(row.act()), 'future stamp does not render a permanent "1m ago"');

  console.log(bad ? "\n" + bad + " FAILED" : "\nall passed");
  process.exit(bad ? 1 : 0);
})();
