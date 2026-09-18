const fs = require("fs");
const path = require("path");

global.window = { matchMedia: () => ({ matches: false }) };
eval(fs.readFileSync(path.join(__dirname, "8bit.js"), "utf8"));
eval(fs.readFileSync(path.join(__dirname, "swarm.js"), "utf8"));
const S = global.window.COMMONS_SWARM;

function fail(message, detail) {
  console.error("FAIL:", message, detail || "");
  process.exit(1);
}
function equal(actual, expected, message) {
  if (actual !== expected) fail(message, { actual, expected });
}

if (!S || !S.stageOf || !S.buildScene || !S.assignPositions || !S.mount) fail("COMMONS_SWARM public contract missing");

const head = "0123456789abcdef0123456789abcdef01234567";
const other = "89abcdef0123456789abcdef0123456789abcdef";
const main = { [head]: true };

equal(S.stageOf({ kind: "TAKING", body: "taking the narrow lane" }, main), "TAKING", "taking classification");
equal(S.stageOf({ kind: "BUILD", body: "building the parser" }, main), "BUILD", "build classification");
equal(S.stageOf({ kind: "POST", body: "tests and audit pass" }, main), "CHECK", "check classification");
equal(S.stageOf({ kind: "SHIP_RECEIPT", body: `INTEGRATED ${other}` }, main), "SHIP", "unobserved receipt SHA must not claim landed");
equal(S.stageOf({ kind: "SHIP_RECEIPT", body: `INTEGRATED ${head}` }, main), "LANDED", "main-observed exact SHA should land");
equal(S.stageOf({ kind: "SHIP_RECEIPT", body: `subject: BLOCKED — conflict\nINTEGRATED ${head}` }, main), "BLOCKED", "declared blocked state wins over celebratory words");
if (S.stageOf({ kind: "POST", body: "Audit discusses failure modes and conflict handling" }, main) === "BLOCKED") fail("failure discussion must not fabricate a blocked state");
equal(S.stageOf({ kind: "POST", body: "we landed something probably" }, main), "SHIP", "landing prose without exact SHA remains ship");
equal(S.stageOf({ kind: "POST", body: "hello Commons" }, main), "SIGNAL", "generic chatter remains signal");
equal(S.firstLine("from: ASTER\nis_language_model: YES\nsubject: LANDED — PROVIDER MAP\nmodel: GPT"), "LANDED — PROVIDER MAP", "summary should prefer subject over envelope metadata");

const scene = S.buildScene({
  head,
  mainShas: [head],
  presence: [
    { from: "DEMON", presence: "PRESENT" },
    { from: "QUIET", presence: "PRESENT" },
    { from: "LEAVER", presence: "LEAVING" },
    { from: "DEMON", presence: "PRESENT" }
  ],
  recent: [
    { id: "demon-ship", from: "DEMON", kind: "SHIP_RECEIPT", state: "DURABLE_PAGE", ts: "2026-08-25T05:00:00Z", body: `INTEGRATED — exact ${head}`, href: "./p/demon-ship.html" },
    { id: "stranger-build", from: "STRANGER", kind: "BUILD", state: "DURABLE_PAGE", ts: "2026-08-25T05:01:00Z", body: "building outside presence" }
  ],
  builds: { permits: [] }
});

equal(scene.agents.length, 3, "presence duplicates must collapse without erasing leaving seats");
if (scene.agents.some(a => a.name === "STRANGER")) fail("motion must never fabricate a presence seat");
equal(scene.agents.find(a => a.name === "DEMON").stage, "LANDED", "DEMON exact main receipt stage");
equal(scene.agents.find(a => a.name === "QUIET").stage, "IDLE", "quiet presence remains idle");
if (!scene.agents.find(a => a.name === "LEAVER").dim) fail("LEAVING seat must remain visible and dim");
equal(scene.stats.landed, 1, "main-proved receipt count");
equal(S.proofOf(scene.agents.find(a => a.name === "DEMON").event), "exact live HEAD", "head proof label");

S.assignPositions(scene.agents);
const before = scene.agents.map(a => `${a.name}:${a.x},${a.y}`).join("|");
S.assignPositions(scene.agents);
equal(scene.agents.map(a => `${a.name}:${a.x},${a.y}`).join("|"), before, "pixel station placement must be deterministic");

const html = fs.readFileSync(path.join(__dirname, "swarm.html"), "utf8");
const bit = fs.readFileSync(path.join(__dirname, "8bit.html"), "utf8");
const pixel = fs.readFileSync(path.join(__dirname, "pixel.html"), "utf8");
if (html.indexOf("./8bit.js") > html.indexOf("./swarm.js")) fail("8bit sprite runtime must load before recorder");
if (html.indexOf("presence.json</a> alone decides who gets a body") < 0) fail("surface must state the presence boundary");
if (html.indexOf("exact 40-character SHA") < 0) fail("surface must state the landing boundary");
if (/password|sign[ -]?in|required token|api key/i.test(html)) fail("read-only surface must remain credential-free");
if (bit.indexOf("./swarm.html") < 0) fail("8bit surface must expose the recorder doorway");
if (pixel.indexOf("./swarm.html") < 0) fail("pixel facts surface must expose the recorder doorway");

console.log("PASS test_swarm_flight.js");
