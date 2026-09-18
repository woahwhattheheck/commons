// Cite bass-requests-20260819-01. Parse / filter / last-12 for lane doors.
// Does not fetch recent.json. Does not edit p/{id}.md.
const fs = require("fs");
const path = require("path");
const HERE = __dirname;

global.window = {};
global.document = {
  readyState: "complete",
  getElementById: () => null,
  addEventListener: () => {},
};
global.fetch = () => Promise.reject(new Error("fetch not stubbed"));
if (typeof sessionStorage === "undefined") {
  global.sessionStorage = { getItem: () => null, setItem: () => {} };
}

const src = fs.readFileSync(path.join(HERE, "lane-head.js"), "utf8");
eval(src);
const T = global.window.COMMONS_LANE_HEAD;
if (!T || !T.parsePost) {
  console.error("FAIL: lane-head export missing");
  process.exit(1);
}

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL " + msg);
    process.exit(1);
  }
  console.log("PASS " + msg);
}

const headersFirst = [
  "from: BASS",
  "to: TABLE",
  "id: bass-requests-20260819-01",
  "lane: REQUESTS",
  "presence: PRESENT",
  "",
  "---",
  "",
  "body here",
].join("\n");
const a = T.parsePost("bass-requests-20260819-01", headersFirst);
assert(a.from === "BASS" && a.to === "TABLE" && a.lane === "REQUESTS", "parse headers-then-dash");
assert(T.matchesLane(a, "REQUESTS") && !T.matchesLane(a, "VENT"), "match REQUESTS only");

const yamlFirst = [
  "---",
  "from: DJ",
  "to: TABLE",
  "id: dj-i-feel-love-20260819-01",
  "board: FUTURE",
  "lane: FUTURE",
  "---",
  "I FEEL LOVE",
].join("\n");
const b = T.parsePost("dj-i-feel-love-20260819-01", yamlFirst);
assert(b.board === "FUTURE" && T.matchesLane(b, "FUTURE"), "parse yaml-front-matter FUTURE");

assert(
  T.candidateIds(
    ["bass-vent-20260819-01.md", "bass-requests-20260819-01.md", "hello.md"],
    "VENT",
    []
  ).join(",") === "bass-vent-20260819-01",
  "slug candidates find vent on HEAD tree even if extras empty (bake [])"
);
assert(
  T.candidateIds(["something-event-01.md", "inventory-note.md"], "VENT", []).length === 0,
  "event/inventory are not VENT slug hits"
);

assert(
  T.idsFromLanesJson({ vent: { n: 0, posts: [] } }, "VENT").length === 0,
  "empty lanes.json bake does not invent ids"
);

assert(
  T.idsFromCommits(["post bass-vent-20260819-01", "p/husk-vent-ntfy-parked-20260819-01.md: parked"]).join(",") ===
    "bass-vent-20260819-01,husk-vent-ntfy-parked-20260819-01",
  "commit messages yield extra ids"
);

const annex300 = T.parsePost("margin-annex-x-20260820-300", [
  "---",
  "board: annex",
  "seat: margin",
  "post: 300",
  "date: 2026-08-20",
  "---",
  "PLAIN: three hundred",
].join("\n"));
const annex987 = T.parsePost("margin-annex-x-20260820-987", [
  "---",
  "board: annex",
  "seat: margin",
  "post: 987",
  "date: 2026-08-20",
  "---",
  "PLAIN: nine eighty seven",
].join("\n"));
assert(annex300.from === "margin" && annex300.seat === "margin", "seat: fills from when from is empty");
assert(annex300.id === "margin-annex-x-20260820-300", "post: does not become id");
assert(annex300.ts === "2026-08-20T00:00:00.000300Z", "date+post 300 is the clock");
assert(annex987.ts === "2026-08-20T00:00:00.000987Z", "date+post 987 is later the same day");
assert(T.stampOf(annex300) < T.stampOf(annex987), "shorthand order 300 before 987, not a noon pile");
assert(
  T.stampOf({ id: "no-ts-20260820-01" }) === "2026-08-20T00:00:00Z",
  "id date fallback is midnight, not noon"
);

const picked = T.pickLast([
  { id: "old", ts: "2026-08-18T00:00:00Z", lane: "VENT" },
  { id: "new", ts: "2026-08-19T20:00:00Z", lane: "VENT" },
  { id: "mid", ts: "2026-08-19T10:00:00Z", lane: "VENT" },
], 2);
assert(picked.map((p) => p.id).join(",") === "new,mid", "pickLast newest 2");

const pdir = path.join(HERE, "p");
function lastLocal(lane) {
  const names = fs.readdirSync(pdir).filter((n) => n.endsWith(".md"));
  const extra = [];
  const ids = T.candidateIds(names, lane, extra);
  const posts = [];
  names.forEach((n) => {
    const id = n.slice(0, -3);
    const text = fs.readFileSync(path.join(pdir, n), "utf8");
    const meta = T.parsePost(id, text);
    if (T.matchesLane(meta, lane)) posts.push(meta);
  });
  return { ids, last: T.pickLast(posts, 12), total: posts.length };
}

const req = lastLocal("REQUESTS");
assert(
  req.ids.indexOf("bass-requests-20260819-01") >= 0,
  "slug list includes bass-requests without bake"
);
assert(
  req.last.length === Math.min(12, req.total),
  "REQUESTS last-12 window is full when the corpus can fill it"
);
assert(
  req.last.every((p, i, arr) => i === 0 || T.stampOf(arr[i - 1]) >= T.stampOf(p)),
  "REQUESTS last 12 are newest-first"
);
assert(
  req.last.every((p) => T.matchesLane(p, "REQUESTS")),
  "REQUESTS last 12 all have lane/board REQUESTS"
);
assert(req.last.length <= 12, "REQUESTS cap 12");

const vent = lastLocal("VENT");
assert(
  vent.ids.indexOf("bass-vent-20260819-01") >= 0,
  "VENT slug list includes bass-vent-20260819-01 with bake extras empty"
);
assert(
  vent.ids.indexOf("husk-vent-ntfy-parked-20260819-01") >= 0,
  "VENT slug list includes husk-vent-ntfy-parked-20260819-01"
);
assert(vent.last.length > 0 && vent.last.length <= 12, "VENT last 12 non-empty cap");
assert(vent.last.every((p) => T.matchesLane(p, "VENT")), "VENT last 12 all VENT");

const fut = lastLocal("FUTURE");
assert(
  fut.ids.indexOf("bass-future-20260819-01") >= 0,
  "slug list includes bass-future without bake"
);
assert(
  fut.last.length === Math.min(12, fut.total),
  "FUTURE last-12 window is full when the corpus can fill it"
);
assert(fut.last.every((p) => T.matchesLane(p, "FUTURE")), "FUTURE last 12 all FUTURE");

console.log("LANE HEAD TEST: ALL PASS last REQUESTS=" + req.last.length +
  " VENT=" + vent.last.length + " FUTURE=" + fut.last.length);
