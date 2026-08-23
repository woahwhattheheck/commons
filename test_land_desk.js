"use strict";

var assert = require("assert");
var fs = require("fs");
var path = require("path");
var vm = require("vm");

var src = fs.readFileSync(path.join(__dirname, "land.js"), "utf8");
var sandbox = { console: console };
vm.createContext(sandbox);
vm.runInContext(src, sandbox);
var api = sandbox.KEEL_LAND;
assert.ok(api, "land.js must export KEEL_LAND");

var live = fs.readFileSync(
  path.join(__dirname, "p", "bryce-emergent-excellence-first-challenge-20260821-01.md"),
  "utf8"
);
assert.ok(/^kind:\s*OWNER_CHALLENGE\s*$/m.test(live), "live first-challenge file must keep kind OWNER_CHALLENGE");

var first = {
  id: "bryce-emergent-excellence-first-challenge-20260821-01",
  from: "BRYCE",
  kind: "OWNER_CHALLENGE",
  ts: "2026-08-21T11:11:36Z",
  subject: "first challenge",
  body: live
};
var openRows = api.challengeStates([first]);
assert.strictEqual(openRows.length, 1);
assert.strictEqual(openRows[0].state, "ACTIVE");
assert.strictEqual(openRows[0].close_id, "");

var closedRows = api.challengeStates([
  first,
  {
    id: "bryce-first-challenge-close-example",
    from: "BRYCE",
    kind: "CHALLENGE_CLOSE",
    ts: "2026-08-21T20:00:00Z",
    supersedes: "bryce-emergent-excellence-first-challenge-20260821-01",
    body: "supersedes: bryce-emergent-excellence-first-challenge-20260821-01"
  }
]);
assert.strictEqual(closedRows[0].state, "QUARANTINED");
assert.strictEqual(closedRows[0].close_id, "bryce-first-challenge-close-example");

var ignored = api.challengeStates([
  first,
  {
    id: "keel-cannot-close-this",
    from: "KEEL",
    kind: "CHALLENGE_CLOSE",
    ts: "2026-08-21T21:00:00Z",
    supersedes: "bryce-emergent-excellence-first-challenge-20260821-01",
    body: "no"
  }
]);
assert.strictEqual(ignored[0].state, "ACTIVE", "only BRYCE/ZERO close counts");

var openPr = api.prStateFromCompare(
  { number: 1561, state: "open" },
  { status: "diverged", ahead_by: 3, behind_by: 12 }
);
assert.strictEqual(openPr.state, "PR_OPEN");
assert.ok(/not INTEGRATED/i.test(openPr.note), "open PR must say it is not main");
assert.ok(/rebase/i.test(openPr.note), "behind-main PR must say rebase first");

var draftPr = api.prStateFromCompare(
  { number: 1621, state: "open", draft: true },
  { status: "ahead", ahead_by: 2, behind_by: 0 }
);
assert.strictEqual(draftPr.state, "CANDIDATE");
assert.ok(/not main/i.test(draftPr.note), "draft must stay a candidate");

var superseded = api.prStateFromCompare(
  { number: 12, state: "open" },
  { status: "identical", ahead_by: 0, behind_by: 4 }
);
assert.strictEqual(superseded.state, "SUPERSEDED");

var merged = api.prStateFromCompare(
  { number: 1560, merged_at: "2026-08-21T11:20:00Z" },
  { status: "identical", ahead_by: 0 }
);
assert.strictEqual(merged.state, "INTEGRATED");

var blocked = api.prStateFromCompare(
  { number: 1555, state: "open" },
  { status: "diverged", ahead_by: 20, behind_by: 80 }
);
assert.strictEqual(blocked.state, "PR_OPEN");
assert.ok(/token/i.test(blocked.note), "PR 1555 must keep the do-not-merge note");

assert.strictEqual(api.pathState(200).state, "INTEGRATED");
assert.strictEqual(api.pathState(404).state, "NOT_LANDED");

assert.ok(api.completionStateFromText, "land.js must classify talk vs land");
var doneText = api.completionStateFromText("INTEGRATED — VERIFIED ON CURRENT MAIN\nDURABLE_ON_MAIN — p/x.md VERIFIED");
assert.strictEqual(doneText.state, "INTEGRATED");
var sitting = api.completionStateFromText("READY / NOT YET LANDED — organ 13");
assert.strictEqual(sitting.state, "NOT_LANDED");
var prTalk = api.completionStateFromText("status PR_OPEN ahead 3");
assert.strictEqual(prTalk.state, "PR_OPEN");
var praise = api.completionStateFromText("remarkable blueprint, thought-provoking, I'll keep studying");
assert.strictEqual(praise.state, "CLAIMED");
assert.ok(/not a land/i.test(praise.note), "talk without completion words is not a land");
assert.ok(api.isDesignJam, "land.js must name a design jam");
var jam = api.completionStateFromText(
  "I'd love to jam on self-healing desired state and nanny/gardener logic. What do you all think?"
);
assert.strictEqual(jam.state, "CLAIMED");
assert.ok(/design jam/i.test(jam.note), "design jam without a SHA is CLAIMED");
assert.ok(/Ship a path/i.test(jam.note), "design jam must tell the window to ship");
var jamDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nself-healing desired state already on main"
);
assert.strictEqual(jamDone.state, "INTEGRATED", "completion words still beat a jam phrase");

var talkOnly = api.excerptState({ sidecar: true, container: false });
assert.strictEqual(talkOnly.state, "NOT_LANDED");
assert.ok(/fabricator is not the file/i.test(talkOnly.note));

var excerptOk = api.excerptState({ sidecar: true, container: true, shaMatch: true });
assert.strictEqual(excerptOk.state, "INTEGRATED");

var shaMiss = api.excerptState({ sidecar: true, container: true, shaMatch: false });
assert.strictEqual(shaMiss.state, "NOT_LANDED");

assert.ok(api.organCensusFromListing, "land.js must census PLUMB organs from the excerpt listing");
assert.strictEqual(api.PLUMB_ORGANS.length, 19);
var organNow = api.organCensusFromListing([
  "muhl_grbn.mno", "muhl_ispn.mno", "muhl_lvin.mno", "muhl_pdap.mno",
  "muhl_petr.mno", "muhl_rgcg.mno", "muhl_synd.mno", "muhl_hdvs.mno",
  "muhl_byzq.mno", "muhl_stig.mno", "muhl_socr.mno"
]);
assert.strictEqual(organNow.filter(function (row) { return row.state === "INTEGRATED"; }).length, 11);
assert.strictEqual(organNow.filter(function (row) { return row.state === "NOT_LANDED"; }).length, 8);
assert.strictEqual(organNow[0].name, "muhl_hdvs");
assert.strictEqual(organNow[0].state, "INTEGRATED");
assert.strictEqual(organNow[1].name, "muhl_sdmk");
assert.strictEqual(organNow[1].state, "NOT_LANDED");
assert.ok(/Talk is not this file/i.test(organNow[1].note), "missing excerpt must tell the window to ship");

assert.ok(api.roadState, "land.js must classify roads as projections of HEAD");
assert.strictEqual(api.roadState("git").state, "INTEGRATED");
assert.strictEqual(api.roadState("HEAD").state, "INTEGRATED");
assert.strictEqual(api.roadState("slack").state, "CARRIER_ONLY");
assert.strictEqual(api.roadState("ntfy").state, "CARRIER_ONLY");
assert.strictEqual(api.roadState("pages").state, "CARRIER_ONLY");
assert.ok(/projection/i.test(api.roadState("discord").note), "discord is a projection");
assert.strictEqual(api.roadState("materialized view essay").state, "CLAIMED");

var html = fs.readFileSync(path.join(__dirname, "land.html"), "utf8");
assert.ok(html.indexOf('id="compose-attach"') >= 0, "land form must expose the DROP attach control");
assert.ok(html.indexOf("carrier.js") >= 0, "land form must use the public carrier");
assert.ok(html.indexOf("kind: CHALLENGE_CLOSE") >= 0, "close recipe must be visible without JS");
assert.ok(html.indexOf("Finish the merge") >= 0, "desk must tell a window not to stop at PR_OPEN");
assert.ok(html.indexOf("Talk is not a land") >= 0, "desk must classify talk without a main SHA");
assert.ok(html.indexOf('id="talk-form"') >= 0, "desk must expose the talk classifier");
assert.ok(html.indexOf("fabricator is not the excerpt") >= 0, "desk must call a sidecar-without-file NOT_LANDED");
assert.ok(html.indexOf('id="organ-list"') >= 0, "desk must list PLUMB organs against current main");
assert.ok(html.toLowerCase().indexOf("take one and merge") >= 0, "desk must tell a window not to stop at organ talk");
assert.ok(/design jam/i.test(html), "desk must name design jam as CLAIMED");
var agents = fs.readFileSync(path.join(__dirname, "AGENTS.md"), "utf8");
assert.ok(/NEVER `git worktree add`/.test(agents), "AGENTS.md must tell Slack clones not to worktree");
assert.ok(/Unique work must reach `origin\/main`/.test(agents), "AGENTS.md must require a main land");
assert.ok(html.indexOf('id="bake-result"') >= 0, "desk must measure bake vs official HEAD");
assert.ok(html.indexOf('id="canary-list"') >= 0, "desk must expose path canaries");
assert.ok(html.indexOf('id="latency-result"') >= 0, "desk must time the official SHA GET");
assert.ok(html.indexOf("Prometheus is not this door") >= 0, "desk must refuse the Prometheus strawman");
assert.ok(/projections of git HEAD/i.test(html), "desk must say roads are projections of HEAD");

assert.ok(api.bakeState, "land.js must compare bake head to official SHA");
var currentBake = api.bakeState("abc123", { head: "abc123", httpStatus: 200 });
assert.strictEqual(currentBake.state, "CURRENT");
assert.ok(/still a bake/i.test(currentBake.note), "matching bake is still a bake");
var staleBake = api.bakeState("abc123", { head: "def456", httpStatus: 200 });
assert.strictEqual(staleBake.state, "STALE");
assert.ok(/not official main/i.test(staleBake.note), "mismatched bake must say STALE");
var missingBake = api.bakeState("abc123", { httpStatus: 404 });
assert.strictEqual(missingBake.state, "NOT_LANDED");
var noSha = api.bakeState("", { head: "abc123", httpStatus: 200 });
assert.strictEqual(noSha.state, "UNMEASURED");

assert.ok(api.canaryState, "land.js must classify canary HTTP");
var canaryOk = api.canaryState({ path: "ground/HEAD.md", httpStatus: 200, ms: 12.4 });
assert.strictEqual(canaryOk.state, "INTEGRATED");
assert.strictEqual(canaryOk.path, "ground/HEAD.md");
assert.strictEqual(canaryOk.ms, 12);
assert.ok(/12 ms/.test(canaryOk.note), "canary note must carry latency");
var canaryMiss = api.canaryState({ path: "p/nope.md", httpStatus: 404, ms: 8 });
assert.strictEqual(canaryMiss.state, "NOT_LANDED");

assert.ok(api.latencyState, "land.js must classify SHA GET latency");
assert.strictEqual(api.latencyState(400).state, "OK");
assert.strictEqual(api.latencyState(3000).state, "WAIT");
assert.strictEqual(api.latencyState(9000).state, "SLOW");
assert.strictEqual(api.latencyState(null).state, "UNMEASURED");

assert.ok(Array.isArray(api.CANARY_PATHS) && api.CANARY_PATHS.length >= 3, "canary list must stay named");
api.CANARY_PATHS.forEach(function (p) {
  assert.ok(fs.existsSync(path.join(__dirname, p)), "canary path must exist in the repo: " + p);
});

var health = fs.readFileSync(path.join(__dirname, "health.html"), "utf8");
assert.ok(health.indexOf('id="bake-result"') >= 0, "health.html must show live bake vs HEAD");
assert.ok(health.indexOf('id="canary-list"') >= 0, "health.html must show path canaries");
assert.ok(health.indexOf("land.js") >= 0, "health.html must reuse the land classifiers");
assert.ok(health.indexOf("MOUTH health") >= 0, "health.html must keep the mouth dump");
assert.ok(health.indexOf("Prometheus is not this door") >= 0, "health.html must not ship a Prometheus manifesto");

console.log("ok   test_land_desk.js");
