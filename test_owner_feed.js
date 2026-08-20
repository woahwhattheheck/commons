// Landing pin: one newest owner, time-first feed.
// Replays the 2026-08-20 measurement: KEEP=12 bake + old rankScore = 24/24 BRYCE.
// Does not hit the network. Does not remint.
const fs = require("fs");
const path = require("path");

let src = fs.readFileSync(path.join(__dirname, "board.js"), "utf8");
src = src.replace(
  "return { load: load, render: render };",
  "return { load: load, render: render, stampOf: stampOf, idStamp: idStamp, rankScore: rankScore, newestOwner: newestOwner, pinOwnerOnce: pinOwnerOnce, merged: merged };"
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

console.log("ALL OWNER FEED TESTS PASS");
