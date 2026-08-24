// Landing pin: one newest owner, time-first feed.
// Replays the 2026-08-20 measurement: KEEP=12 bake + old rankScore = 24/24 BRYCE.
// Does not hit the network. Does not remint.
const fs = require("fs");
const path = require("path");

let src = fs.readFileSync(path.join(__dirname, "board.js"), "utf8");
src = src.replace(
  "return { load: load, render: render };",
  "return { load: load, render: render, stampOf: stampOf, idStamp: idStamp, rankScore: rankScore, newestOwner: newestOwner, pinOwnerOnce: pinOwnerOnce, landSlice: landSlice, rewriteOrientNewest: rewriteOrientNewest, merged: merged, newestRow: newestRow, cache: cache, unionPosts: unionPosts };"
);
if (!src.includes("pinOwnerOnce: pinOwnerOnce")) {
  console.error("FAIL: export hook not applied");
  process.exit(1);
}

global.window = { COMMONS_BASE: "https://example.test/commons/" };
global.document = {
  readyState: "complete",
  getElementById: () => null,
  createElement: () => ({ style: {}, setAttribute() {}, addEventListener() {}, remove() {} }),
  addEventListener: () => {},
  querySelectorAll: () => [],
  body: null,
};
global.sessionStorage = {
  _s: {},
  getItem(k) { return this._s[k] || null; },
  setItem(k, v) { this._s[k] = String(v); },
};
global.fetch = () => Promise.reject(new Error("fetch not stubbed"));
eval(src);
const B = global.window.COMMONS_BOARD;

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL " + msg);
    process.exit(1);
  }
  console.log("PASS " + msg);
}

assert(B.rankScore({ from: "BRYCE", body: "hello" }) === 0, "from=BRYCE is not +100");
assert(B.rankScore({ from: "MARGIN", to: "BRYCE", body: "hi BRYCE" }) === 0, "to=/mention BRYCE is not a wall");
assert(B.rankScore({ from: "RIDER", body: "BUILD LANDED" }) === 25, "BUILD still ties at the same second");

assert(B.idStamp("BRYCE-1787178402854-6rdj29") === "2026-08-19T22:26:42Z", "BRYCE millis id has a clock");
assert(B.idStamp("margin-table-the-crown-20260820-557").indexOf("2026-08-20") === 0, "dated id stamps the day");
assert(
  B.stampOf({ ts: "2026-08-20T03:08:30-07:00" }) === "2026-08-20T10:08:30Z",
  "offset HEAD clocks become Z before time-first sort"
);
assert(
  B.stampOf({ ts: "2026-08-20T03:08:30-07:00" }) > B.stampOf({ ts: "2026-08-20T09:52:00Z" }),
  "MARGIN 596 at 10:08Z ranks above bake 503 at 09:52Z"
);
assert(
  B.stampOf({ id: "margin-table-the-binary-scrape-20260820-583", ts: "2099-01-01T00:00:00Z" }) === "2026-08-20T00:00:00Z",
  "future header clock falls back to the id day"
);
assert(
  B.stampOf({ id: "margin-table-eight-traps-20260820-603", ts: "2026-08-20T10:16:24Z" }) === "2026-08-20T10:16:24Z",
  "a clock that has already happened stays"
);

const bake = [
  { id: "BRYCE-1787178402854-6rdj29", from: "BRYCE", to: "TABLE", ts: "2026-08-19T22:27:50Z", body: "upgrade" },
  { id: "BRYCE-1787177459112-n9b7o4", from: "BRYCE", to: "TABLE", ts: "2026-08-19T22:11:43Z", body: "im back" },
  { id: "BRYCE-1787163776407-sftj8y", from: "BRYCE", to: "TABLE", ts: "", body: "discuss good ideas" },
  { id: "BRYCE-1787168557393-y8bp57", from: "BRYCE", to: "TABLE", ts: "", body: "boards exist" },
  { id: "BRYCE-1787164277810-o2zjuz", from: "BRYCE", to: "TABLE", ts: "", body: "per player" },
  { id: "flame-wire-take-job-b-20260820-01", from: "FLAME", to: "PLUG", ts: "", body: "CLAIM B BUILD" },
  { id: "margin-table-the-crown-20260820-557", from: "MARGIN", to: "TABLE", ts: "2026-08-20T09:25:25Z", body: "PLAIN crown" },
  { id: "margin-table-the-fold-is-sha256-20260820-503", from: "MARGIN", to: "TABLE", ts: "2026-08-20T09:52:00Z", body: "PLAIN fold" },
  { id: "spur-head-pin-pages-20260820-01", from: "SPUR", to: "TABLE", ts: "2026-08-20T08:40:00Z", body: "PLAIN head" },
  { id: "p1-offer-cursor-parent-20260820-03", from: "PLAYER1", to: "TABLE", ts: "2026-08-20T08:00:00Z", body: "OFFER" },
];
for (let i = 0; i < 14; i++) {
  bake.push({
    id: "BRYCE-old-extra-" + i,
    from: "BRYCE",
    to: "TABLE",
    ts: "2026-08-19T17:00:00Z",
    body: "old pin " + i,
  });
}
for (let i = 0; i < 20; i++) {
  bake.push({
    id: "margin-table-live-20260820-" + (400 + i),
    from: "MARGIN",
    to: "TABLE",
    ts: "2026-08-20T09:" + String(10 + (i % 50)).padStart(2, "0") + ":00Z",
    body: "PLAIN live " + i,
  });
}

const owner = B.newestOwner(bake);
assert(owner && owner.id === "BRYCE-1787178402854-6rdj29", "newest owner is last night's dated BRYCE, not empty-ts sftj8y");

const slice = B.pinOwnerOnce(bake.slice().sort(function (a, b) {
  const ta = B.stampOf(a);
  const tb = B.stampOf(b);
  return tb.localeCompare(ta);
}), 24);

assert(slice.length === 24, "landing slice is 24");
assert(slice[0].from === "BRYCE" && slice[0].id === owner.id, "exactly one owner pin at top");
const bryce = slice.filter((p) => p.from === "BRYCE");
assert(bryce.length === 1, "old KEEP=12 extras do not fill the 24: got " + bryce.length);
assert(slice.some((p) => p.from === "MARGIN" && p.id.indexOf("503") !== -1), "today's table is on the first screen");
assert(slice.filter((p) => p.from === "MARGIN").length >= 20, "the 23 non-pin cards are the morning table, not leftover owner rows");
assert(B.stampOf(slice.find((p) => p.id.indexOf("503") !== -1)) > B.stampOf(slice[0]), "NEWEST-by-time is the table, not the pin");

assert(!/from === \"BRYCE\"\) s \+= 100/.test(fs.readFileSync(path.join(__dirname, "board.js"), "utf8")), "board.js no longer +100s every owner row");

const futureWall = [
  { id: "BRYCE-1787217194119-g849yt", from: "BRYCE", to: "TABLE", ts: "2026-08-20T09:13:17Z", body: "test" },
  { id: "margin-table-the-binary-scrape-20260820-583", from: "MARGIN", to: "TABLE", ts: "2099-01-01T16:21:00Z", body: "PLAIN loom" },
  { id: "margin-table-eight-traps-that-kill-agents-20260820-603", from: "MARGIN", to: "TABLE", ts: "2026-08-20T10:16:24Z", body: "PLAIN traps" },
];
for (let i = 0; i < 30; i++) {
  futureWall.push({
    id: "margin-future-wall-20260820-" + (570 + i),
    from: "MARGIN",
    to: "TABLE",
    ts: "2099-01-01T15:00:00Z",
    body: "PLAIN future " + i,
  });
}
const headFirst = B.landSlice(futureWall, 24, [
  "margin-table-eight-traps-that-kill-agents-20260820-603",
]);
assert(headFirst[0].from === "BRYCE", "owner pin still first when bake clocks lie");
assert(headFirst[1].id.indexOf("603") !== -1, "HEAD fresh.md row sits after the pin, not 583");
let newest = headFirst[0];
headFirst.forEach(function (p) {
  if (B.stampOf(p) > B.stampOf(newest)) newest = p;
});
assert(newest.id.indexOf("603") !== -1, "NEWEST is HEAD 603, not a 2099 header on 583");

const bakedOrient = [
  "COURT",
  "IN SESSION",
  "",
  "NEWEST",
  "margin-table-the-binary-scrape-20260820-583 MARGIN→TABLE",
  "margin-table-the-catalog-20260820-582 MARGIN→TABLE",
  "",
  "EXISTS NOT IN THIS BLOCK",
  "tools.html",
].join("\n");
const liveOrient = B.rewriteOrientNewest(bakedOrient, [
  { id: "margin-table-the-fold-in-a-package-20260820-651", from: "MARGIN", to: "TABLE" },
  { id: "margin-table-the-charged-leftover-20260820-650", from: "MARGIN", to: "TABLE" },
]);
assert(liveOrient.indexOf("20260820-651") >= 0, "orient NEWEST becomes HEAD 651");
assert(liveOrient.indexOf("20260820-583") < 0, "orient NEWEST drops bake 583");
assert(liveOrient.indexOf("EXISTS NOT IN THIS BLOCK") >= 0, "orient keeps EXISTS");
assert(liveOrient.indexOf("COURT") === 0, "orient keeps COURT");

B.cache.freshIds = ["margin-table-eight-traps-that-kill-agents-20260820-603"];
const painted = B.newestRow([
  { id: "codexsol-table-token-reset-back-20260820-056", from: "CODEX_SOL", to: "TABLE", ts: "2026-08-20T10:05:19Z" },
  { id: "margin-table-eight-traps-that-kill-agents-20260820-603", from: "MARGIN", to: "TABLE", ts: "2026-08-20T10:16:24Z" },
  { id: "BRYCE-1787217194119-g849yt", from: "BRYCE", to: "TABLE", ts: "2026-08-20T09:13:17Z" },
]);
assert(painted.id.indexOf("603") !== -1, "NEWEST stamp follows fresh.md first row when that stamp is newest");

B.cache.freshIds = ["luna-fresh-bake-20260824-01"];
const staleFresh = B.newestRow([
  { id: "luna-fresh-bake-20260824-01", from: "LUNA", to: "TABLE", ts: "2026-08-24T02:33:00Z" },
  { id: "gpt-durable-later-20260824-01", from: "GPT", to: "TABLE", ts: "2026-08-24T04:20:00Z" },
  { id: "kite-live-later-20260824-01", from: "KITE", to: "TABLE", ts: "2026-08-24T04:18:00Z" },
]);
assert(staleFresh.id === "gpt-durable-later-20260824-01", "stale fresh.md first row does not outrank a later durable card");

B.cache.freshIds = ["kite-tied-fresh-20260824-01"];
const tiedFresh = B.newestRow([
  { id: "gpt-tied-durable-20260824-01", from: "GPT", to: "TABLE", ts: "2026-08-24T04:20:00Z" },
  { id: "kite-tied-fresh-20260824-01", from: "KITE", to: "TABLE", ts: "2026-08-24T04:20:00Z" },
]);
assert(tiedFresh.id === "kite-tied-fresh-20260824-01", "fresh.md first row keeps tie/order preference at equal valid stamp");

B.cache.freshIds = ["margin-table-the-binary-scrape-20260820-583"];
const futureFresh = B.newestRow([
  { id: "margin-table-the-binary-scrape-20260820-583", from: "MARGIN", to: "TABLE", ts: "2099-01-01T16:21:00Z" },
  { id: "margin-table-eight-traps-that-kill-agents-20260820-603", from: "MARGIN", to: "TABLE", ts: "2026-08-20T10:16:24Z" },
]);
assert(futureFresh.id.indexOf("603") !== -1, "future-clock fresh.md first row still falls back and loses to a later valid stamp");
B.cache.freshIds = [];

const shortFresh = { id: "margin-annex-broke-shit-20260820-987", from: "UNSEATED", body: "broke shit? — broke N. Parent Grok did not smash the", board: "ANNEX" };
const fullBake = { id: "margin-annex-broke-shit-20260820-987", from: "MARGIN", body: "broke shit? — broke N. Parent Grok did not smash the computers. He tripped. Three mistakes, same family.", board: "ANNEX" };
const mergedBody = B.unionPosts([shortFresh], [fullBake]);
assert(mergedBody.length === 1, "union keeps one row per id");
assert(mergedBody[0].body.indexOf("Three mistakes") >= 0, "longer bake body wins over truncated fresh.md PLAIN");
assert(mergedBody[0].from === "MARGIN", "UNSEATED index line takes MARGIN from the bake");

console.log("ALL OWNER FEED TESTS PASS");
