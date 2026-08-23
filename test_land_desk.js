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

var talkOnly = api.excerptState({ sidecar: true, container: false });
assert.strictEqual(talkOnly.state, "NOT_LANDED");
assert.ok(/fabricator is not the file/i.test(talkOnly.note));

var excerptOk = api.excerptState({ sidecar: true, container: true, shaMatch: true });
assert.strictEqual(excerptOk.state, "INTEGRATED");

var shaMiss = api.excerptState({ sidecar: true, container: true, shaMatch: false });
assert.strictEqual(shaMiss.state, "NOT_LANDED");

var html = fs.readFileSync(path.join(__dirname, "land.html"), "utf8");
assert.ok(html.indexOf('id="compose-attach"') >= 0, "land form must expose the DROP attach control");
assert.ok(html.indexOf("carrier.js") >= 0, "land form must use the public carrier");
assert.ok(html.indexOf("kind: CHALLENGE_CLOSE") >= 0, "close recipe must be visible without JS");
assert.ok(html.indexOf("Finish the merge") >= 0, "desk must tell a window not to stop at PR_OPEN");
assert.ok(html.indexOf("fabricator is not the excerpt") >= 0, "desk must call a sidecar-without-file NOT_LANDED");

console.log("ok   test_land_desk.js");
