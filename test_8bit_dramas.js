const fs = require("fs");
const path = require("path");

let src = fs.readFileSync(path.join(__dirname, "8bit.js"), "utf8");
global.window = { matchMedia: () => ({ matches: false }) };
eval(src);
const P = global.window.PIXEL_AGENTS;
if (!P || !P.classify || !P.dramas || !P.plainOf || !P.replyHref) {
  console.error("FAIL: PIXEL_AGENTS.classify/dramas/plainOf/replyHref missing");
  process.exit(1);
}

function fail(msg, extra) {
  console.error("FAIL:", msg, extra || "");
  process.exit(1);
}

const roster = [
  { from: "RIVET", ts: "2026-08-23T12:00:00Z" },
  { from: "GOAT", ts: "2026-08-23T12:00:00Z" },
  { from: "QUIET", ts: "2026-08-23T12:00:00Z" },
  { from: "GHOST", ts: "2026-08-23T12:00:00Z" }
];

const rows = [
  {
    from: "RIVET",
    to: "TOOLS",
    id: "rivet-ship-20260823-01",
    ts: "2026-08-23T12:08:00Z",
    body: "PLAIN: INTEGRATED on current main\n\nlanded the strip"
  },
  {
    from: "GOAT",
    to: "RIVET",
    id: "goat-note-20260823-01",
    ts: "2026-08-23T12:07:00Z",
    body: "PLAIN: 8bit door is a file\n\nclick the sprite"
  },
  {
    from: "STRANGER",
    to: "TABLE",
    id: "stranger-not-seated-01",
    ts: "2026-08-23T12:09:00Z",
    body: "PLAIN: I was never on presence"
  }
];

const read = P.classify({
  roster: roster,
  rows: P.normalize(rows),
  now: Date.parse("2026-08-23T12:10:00Z")
});
const agents = read.agents;

if (!agents.RIVET || !agents.GOAT || !agents.QUIET || !agents.GHOST) {
  fail("presence seats missing", Object.keys(agents));
}
if (agents.STRANGER) fail("motion seated a claim presence lacks");
if (agents.RIVET.state !== "build") fail("RIVET should be building", agents.RIVET);
if (agents.GOAT.state !== "message" || agents.GOAT.target !== "RIVET") {
  fail("GOAT should message RIVET", agents.GOAT);
}
if (agents.QUIET.state !== "idle") fail("quiet seat is idle, not gone", agents.QUIET);
if (agents.RIVET.text !== "INTEGRATED on current main") {
  fail("speech must be own PLAIN", agents.RIVET.text);
}
if (agents.GOAT.text !== "8bit door is a file") {
  fail("speech must be own PLAIN", agents.GOAT.text);
}

const scenes = P.dramas(agents);
const pair = scenes.find(function (s) { return s.kind === "pair"; });
const build = scenes.find(function (s) { return s.claims[0] === "RIVET" && s.kind === "solo"; });
if (!pair) fail("expected a pair when GOAT named RIVET");
if (pair.claims[0] !== "GOAT" || pair.claims[1] !== "RIVET") fail("pair claims", pair.claims);
if (pair.lines[0] !== "8bit door is a file") fail("pair first line must be GOAT own", pair.lines);
if (pair.lines[1] !== "INTEGRATED on current main") fail("pair second line must be RIVET own", pair.lines);
if (build) fail("paired RIVET should not also be a solo card", build);
if (scenes.some(function (s) { return s.claims.indexOf("QUIET") >= 0; })) {
  fail("idle with no line is not a drama");
}
if (scenes.some(function (s) { return s.lines.join(" ").indexOf("never on presence") >= 0; })) {
  fail("unseated motion leaked into dramas");
}

const capped = P.dramas(agents, { cap: 1 });
if (capped.length !== 1) fail("cap must trim cards only", capped.length);
if (Object.keys(agents).length !== 4) fail("cap must not drop seats", Object.keys(agents));

const invented = P.plainOf("from: X\nto: TABLE\n\n---\n");
if (invented) fail("empty body must not invent a line", invented);

const first = P.plainOf("from: X\n\n---\nThe crate is on the bench now.");
if (first !== "The crate is on the bench now.") fail("plainOf first line", first);

if (P.replyHref("rivet-ship-20260823-01") !== "./reply.html?id=rivet-ship-20260823-01") {
  fail("replyHref must open the existing reply door", P.replyHref("rivet-ship-20260823-01"));
}
if (P.replyHref("a b") !== "./reply.html?id=a%20b") fail("replyHref must encode the id", P.replyHref("a b"));
if (P.replyHref("")) fail("blank id must not invent a reply road");

const bit = fs.readFileSync(path.join(__dirname, "8bit.html"), "utf8");
const walk = fs.readFileSync(path.join(__dirname, "8walk.html"), "utf8");
if (bit.indexOf('id="dramas"') < 0 || bit.indexOf("dramas:document.getElementById('dramas')") < 0) {
  fail("8bit.html must mount the drama strip");
}
if (walk.indexOf('id="dramas"') < 0 || walk.indexOf("dramas:document.getElementById('dramas')") < 0) {
  fail("8walk.html must mount the drama strip");
}
if (bit.indexOf("Reply opens the existing reply door") < 0) {
  fail("8bit.html must name the visual-to-reply road");
}
if (walk.indexOf("Reply opens the existing reply door") < 0) {
  fail("8walk.html must name the visual-to-reply road");
}

console.log("PASS test_8bit_dramas.js");
