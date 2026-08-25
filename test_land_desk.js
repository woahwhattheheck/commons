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
assert.strictEqual(api.pathState(0).state, "UNMEASURED");
assert.strictEqual(api.pathState(undefined).state, "UNMEASURED");
[403, 429, 500].forEach(function (status) {
  var failed = api.pathState(status);
  assert.strictEqual(failed.state, "UNMEASURED", "HTTP " + status + " is lookup failure, not absence");
  assert.ok(failed.note.indexOf(String(status)) >= 0, "failed path note keeps HTTP " + status);
});

assert.ok(api.completionStateFromText, "land.js must classify talk vs land");
function assertTextState(text, expected, message) {
  assert.strictEqual(api.completionStateFromText(text).state, expected, message || text);
}
var doneText = api.completionStateFromText("INTEGRATED — VERIFIED ON CURRENT MAIN\nDURABLE_ON_MAIN — p/x.md VERIFIED");
assert.strictEqual(doneText.state, "INTEGRATED");
[
  "PLAIN: INTEGRATED — VERIFIED ON CURRENT MAIN.",
  "state: INTEGRATED — VERIFIED ON CURRENT MAIN",
  "2/2 INTEGRATED — VERIFIED ON CURRENT MAIN",
  "_INTEGRATED — VERIFIED ON CURRENT MAIN_ sha",
  "• DURABLE_ON_MAIN — `p/real-record-20260824-01.md` VERIFIED",
  "INTEGRATED — VERIFIED ON CURRENT MAIN. If Pages lags, use pinned HEAD.",
  "INTEGRATED — VERIFIED ON CURRENT MAIN; will remain on this SHA.",
  "DURABLE_ON_MAIN — p/real-record-20260824-01.md VERIFIED. When Pages catches up, this path remains canonical."
].forEach(function (text) {
  assertTextState(text, "INTEGRATED", "canonical receipt decoration must remain valid: " + text);
});
[
  "I will report INTEGRATED — VERIFIED ON CURRENT MAIN after the merge.",
  "We did not reach INTEGRATED — VERIFIED ON CURRENT MAIN",
  "I cannot claim INTEGRATED — VERIFIED ON CURRENT MAIN",
  "No evidence supports INTEGRATED — VERIFIED ON CURRENT MAIN",
  "Was INTEGRATED — VERIFIED ON CURRENT MAIN; now NOT_LANDED",
  "INTEGRATED — VERIFIED ON CURRENT MAIN, but the merge was reverted",
  "INTEGRATED — VERIFIED ON CURRENT MAIN; NOT_LANDED — merge reverted",
  "INTEGRATED — VERIFIED ON CURRENT MAIN; now NOT_LANDED",
  "INTEGRATED — VERIFIED ON CURRENT MAIN, although the merge was reverted",
  "INTEGRATED — VERIFIED ON CURRENT MAIN but NOT_LANDED",
  "INTEGRATED — VERIFIED ON CURRENT MAIN; remains NOT_LANDED",
  "INTEGRATED — VERIFIED ON CURRENT MAIN when the merge lands",
  "INTEGRATED — VERIFIED ON CURRENT MAIN if tests pass",
  "INTEGRATED — VERIFIED ON CURRENT MAIN provided CI is green",
  "INTEGRATED — VERIFIED ON CURRENT MAIN unless the merge is reverted",
  "INTEGRATED — VERIFIED ON CURRENT MAIN no longer applies",
  "INTEGRATED — VERIFIED ON CURRENT MAIN does not apply",
  "INTEGRATED — VERIFIED ON CURRENT MAIN was the previous state",
  "INTEGRATED — VERIFIED ON CURRENT MAIN will be verified after the merge",
  "INTEGRATED — VERIFIED ON CURRENT MAIN_FAKE",
  "INTEGRATED — VERIFIED ON CURRENT MAIN__FAKE",
  "INTEGRATED — VERIFIED ON CURRENT MAIN-ish",
  "Completion language is only `INTEGRATED — VERIFIED ON CURRENT MAIN`",
  "Example: INTEGRATED — VERIFIED ON CURRENT MAIN",
  "```\nINTEGRATED — VERIFIED ON CURRENT MAIN\n```",
  "```md\n~~~\nINTEGRATED — VERIFIED ON CURRENT MAIN\n~~~\n```",
  "~~~md\n```\nINTEGRATED — VERIFIED ON CURRENT MAIN\n```\n~~~",
  "```md\n```not-a-close\nINTEGRATED — VERIFIED ON CURRENT MAIN\n```",
  "~~~~md\n~~~~still-code\nINTEGRATED — VERIFIED ON CURRENT MAIN\n~~~~",
  "Cannot claim DURABLE_ON_MAIN",
  "This is NOT INTEGRATED — VERIFIED ON CURRENT MAIN?",
  "NOT INTEGRATED — VERIFIED ON CURRENT MAIN if tests fail",
  "NOT DURABLE_ON_MAIN provided the issue stays open",
  "NOT INTEGRATED — VERIFIED ON CURRENT MAIN no longer applies",
  "DURABLE_ON_MAIN IS NOT? no",
  "DURABLE_ON_MAIN is pending ingest",
  "DURABLE_ON_MAIN remains pending",
  "Is DURABLE_ON_MAIN?",
  "DURABLE_ON_MAIN — p/example-record.md",
  "DURABLE_ON_MAIN — p/{id}.md VERIFIED",
  "DURABLE_ON_MAIN — p/real-record-20260824-01.md VERIFIED only after ingest",
  "DURABLE_ON_MAIN — p/real-record-20260824-01.md VERIFIED if the issue closes",
  "DURABLE_ON_MAIN — p/real-record-20260824-01.md VERIFIED is incorrect",
  "DURABLE_ON_MAIN — p/real-record-20260824-01.md VERIFIED-ish",
  "Previously NOT_LANDED; now INTEGRATED — VERIFIED ON CURRENT MAIN"
].forEach(function (text) {
  assertTextState(text, "CLAIMED", "narrative/template completion prose is not a receipt: " + text);
});
assertTextState("This is NOT INTEGRATED — VERIFIED ON CURRENT MAIN; the PR is still open.", "NOT_LANDED");
assertTextState("INTEGRATED — VERIFIED ON CURRENT MAIN is not the current state", "NOT_LANDED");
assertTextState("Not DURABLE_ON_MAIN yet; p/example.md still needs to land.", "NOT_LANDED");
assertTextState("DURABLE_ON_MAIN is false", "NOT_LANDED");
assertTextState("NOT_LANDED — no matching path at the measured SHA", "NOT_LANDED");
assertTextState("NOT_LANDED remains NOT_LANDED", "NOT_LANDED");
assertTextState("READY / NOT YET LANDED remains NOT_LANDED", "NOT_LANDED");
[
  "Classifier result:\nNOT_LANDED",
  "Status vocabulary:\nNOT_LANDED",
  "The classifier says:\nNOT YET LANDED",
  "Completion language follows:\nNOT_LANDED — no path at SHA"
].forEach(function (text) {
  assertTextState(text, "NOT_LANDED", "ordinary preceding prose must not suppress a direct negative line");
});
assertTextState("DURABLE_ON_MAIN will be claimed only after the issue lands.", "CLAIMED");
var futureCorpus = fs.readFileSync(
  path.join(__dirname, "p", "slack-1787306348-289319.md"),
  "utf8"
);
assert.strictEqual(api.completionStateFromText(futureCorpus).state, "CLAIMED");
[
  "slack-1787306109-206369.md",
  "flame-taking-tos-verify-20260821-01.md"
].forEach(function (name) {
  var body = fs.readFileSync(path.join(__dirname, "p", name), "utf8");
  assertTextState(body, "CLAIMED", "non-receipt corpus fixture must stay CLAIMED: " + name);
});
var correctionCorpus = fs.readFileSync(
  path.join(__dirname, "p", "slack-1787487231-855809.md"),
  "utf8"
);
assertTextState(correctionCorpus, "CLAIMED", "historical NOT_LANDED prose is not a current negative receipt");
var negativeCorpus = fs.readFileSync(
  path.join(__dirname, "p", "slack-1787318095-643249.md"),
  "utf8"
);
assertTextState(negativeCorpus, "NOT_LANDED", "a code-wrapped whole-line negative receipt remains explicit");
var explanatoryNegativeCorpus = fs.readFileSync(
  path.join(__dirname, "p", "rivet-ship-ispn-20260823-01.md"),
  "utf8"
);
assertTextState(explanatoryNegativeCorpus, "INTEGRATED",
  "a later explanation of NOT_LANDED vocabulary must not overwrite a real receipt");
var historyThenDone = api.completionStateFromText(
  "I will report INTEGRATED — VERIFIED ON CURRENT MAIN after the merge.\n" +
  "INTEGRATED — VERIFIED ON CURRENT MAIN\n" +
  "Prior QUARANTINED_CONFLICT and design-jam language are historical."
);
assert.strictEqual(historyThenDone.state, "INTEGRATED", "one affirmative completion occurrence wins");
assertTextState(
  "Previously NOT_LANDED; the merge was pending.\nINTEGRATED — VERIFIED ON CURRENT MAIN",
  "INTEGRATED",
  "a later explicit receipt line wins over historical narrative"
);
assertTextState(
  "NOT_LANDED — old state\nINTEGRATED — VERIFIED ON CURRENT MAIN",
  "INTEGRATED",
  "last explicit receipt status wins"
);
assertTextState(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nNOT_LANDED — merge reverted",
  "NOT_LANDED",
  "later explicit negative status wins"
);
[
  "NOT_LANDED no longer applies; the file is on main",
  "NOT_LANDED? no",
  "NOT_LANDED — no longer applies",
  "NOT_LANDED was the previous state",
  "NOT_LANDED is incorrect",
  "NOT_LANDED is not the current state",
  "NOT_LANDED does not apply",
  "NOT_LANDED, but now integrated",
  "NOT_LANDED-ish",
  "NOT_LANDED if tests fail",
  "NOT_LANDED?",
  "Do not report NOT_LANDED after HTTP 500",
  "No NOT_LANDED paths remain",
  "The label `NOT_LANDED` would be wrong",
  "```\nNOT YET LANDED\n```",
  "```\nQUARANTINED_CONFLICT SAME_ID_DIFFERENT_BODY\n```",
  "Example: QUARANTINED_CONFLICT is handled here",
  "QUARANTINED_CONFLICT? no",
  "QUARANTINED_CONFLICT no longer applies"
].forEach(function (text) {
  assertTextState(text, "CLAIMED", "negative vocabulary outside a status line is not absence: " + text);
});
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
assert.ok(api.isVisualPraise, "land.js must name visual-commons praise");
var visualTalk = api.completionStateFromText(
  "Impressed by the visual commons with 8bit/pixel bots. Sprite-based interactions. Excited to see where it leads!"
);
assert.strictEqual(visualTalk.state, "CLAIMED");
assert.ok(/visual-commons praise/i.test(visualTalk.note), "8bit praise without a SHA is CLAIMED");
assert.ok(/Ship a path/i.test(visualTalk.note), "visual praise must tell the window to ship");
var visualDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nvisual commons already on main"
);
assert.strictEqual(visualDone.state, "INTEGRATED", "completion words still beat visual praise");

assert.ok(api.envelopeState, "land.js must classify a quarantined remint");
var remint = api.envelopeState({ state: "QUARANTINED_CONFLICT", reason: "SAME_ID_DIFFERENT_BODY" });
assert.strictEqual(remint.state, "NOT_LANDED");
assert.ok(/new id/i.test(remint.note), "quarantine must say refile a new id");
assert.ok(/original/i.test(remint.note), "quarantine must keep the original page");
var originalPage = api.envelopeState({ state: "DURABLE_PAGE" });
assert.strictEqual(originalPage.state, "INTEGRATED");
var qTalk = api.completionStateFromText(
  "QUARANTINED_CONFLICT SAME_ID_DIFFERENT_BODY — NOT a landing. Re-file under a new id."
);
assert.strictEqual(qTalk.state, "NOT_LANDED");
assert.ok(/new id/i.test(qTalk.note), "quarantine talk must tell the window to refile and ship");
var qDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nQUARANTINED_CONFLICT already measured"
);
assert.strictEqual(qDone.state, "INTEGRATED", "completion words still beat a quarantine receipt");

assert.ok(api.fireActionEmptyState, "land.js must name the empty fire_action contract");
var fireSchema = api.fireActionEmptyState({ code: "SCHEMA" });
assert.strictEqual(fireSchema.state, "NOT_LANDED");
assert.ok(/invocation bug/i.test(fireSchema.note), "SCHEMA on {} is the leftover bug");
var fireOk = api.fireActionEmptyState({ ok: true, state: "ACTION_SUCCEEDED" });
assert.strictEqual(fireOk.state, "INTEGRATED");
var fireTalk = api.fireActionEmptyState({});
assert.strictEqual(fireTalk.state, "CLAIMED");

var talkOnly = api.excerptState({ sidecar: true, container: false });
assert.strictEqual(talkOnly.state, "NOT_LANDED");
assert.ok(/fabricator is not the file/i.test(talkOnly.note));

var excerptOk = api.excerptState({ sidecar: true, container: true, shaMatch: true });
assert.strictEqual(excerptOk.state, "INTEGRATED");

var shaMiss = api.excerptState({ sidecar: true, container: true, shaMatch: false });
assert.strictEqual(shaMiss.state, "NOT_LANDED");

assert.ok(api.organCensusFromListing, "land.js must census PLUMB organs from the excerpt listing");
assert.strictEqual(api.PLUMB_ORGANS.length, 31);
var organNow = api.organCensusFromListing([
  "muhl_grbn.mno", "muhl_ispn.mno", "muhl_lvin.mno", "muhl_pdap.mno",
  "muhl_petr.mno", "muhl_rgcg.mno", "muhl_synd.mno", "muhl_hdvs.mno",
  "muhl_byzq.mno", "muhl_stig.mno", "muhl_socr.mno", "muhl_flow.mno"
]);
assert.strictEqual(organNow.filter(function (row) { return row.state === "INTEGRATED"; }).length, 12);
assert.strictEqual(organNow.filter(function (row) { return row.state === "NOT_LANDED"; }).length, 19);
assert.strictEqual(organNow[0].name, "muhl_hdvs");
assert.strictEqual(organNow[0].state, "INTEGRATED");
assert.strictEqual(organNow[1].name, "muhl_sdmk");
assert.strictEqual(organNow[1].state, "NOT_LANDED");
assert.ok(/Talk is not this file/i.test(organNow[1].note), "missing excerpt must tell the window to ship");
assert.strictEqual(organNow[19].name, "muhl_chimera_immn_hdvs");
assert.strictEqual(organNow[19].state, "NOT_LANDED");
var organTwenty = api.organCensusFromListing([
  "muhl_chimera_immn_hdvs.mno", "muhl_hdvs.mno", "muhl_immn.mno"
]);
assert.strictEqual(organTwenty[19].state, "INTEGRATED");
assert.strictEqual(organTwenty[19].gates, 20);
assert.strictEqual(organTwenty.filter(function (row) { return row.state === "NOT_LANDED"; }).length, 28);
assert.strictEqual(organNow[21].name, "muhl_chimera_tset_hdvs");
assert.strictEqual(organNow[21].state, "NOT_LANDED");
assert.strictEqual(organNow[21].gates, 24);
var organTwentyTwo = api.organCensusFromListing(["muhl_chimera_tset_hdvs.mno"]);
assert.strictEqual(organTwentyTwo[21].state, "INTEGRATED");
assert.strictEqual(organNow[24].name, "muhl_chimera_flow_stig");
assert.strictEqual(organNow[24].state, "NOT_LANDED");
assert.strictEqual(organNow[24].gates, 18);
var organTwentyFive = api.organCensusFromListing(["muhl_chimera_flow_stig.mno"]);
assert.strictEqual(organTwentyFive[24].state, "INTEGRATED");
assert.strictEqual(organNow[25].name, "muhl_chimera_pots_dmb");
assert.strictEqual(organNow[25].state, "NOT_LANDED");
assert.strictEqual(organNow[25].gates, 20);
var organTwentySix = api.organCensusFromListing(["muhl_chimera_pots_dmb.mno"]);
assert.strictEqual(organTwentySix[25].state, "INTEGRATED");
assert.strictEqual(organNow[28].name, "muhl_titanx_forge");
assert.strictEqual(organNow[28].state, "NOT_LANDED");
assert.strictEqual(organNow[28].gates, 180);
var organTwentyNine = api.organCensusFromListing(["muhl_titanx_forge.mno"]);
assert.strictEqual(organTwentyNine[28].state, "INTEGRATED");
assert.ok(api.isIntroTalk("Pardon my mixup and feel free to just call me Plumb as I get my bearings."), "name-correction mixup is talk");
var mixupTalk = api.completionStateFromText(
  "Correction — I'm actually PLUMB, not Codex! Still learning the ropes. Pardon my mixup and feel free to just call me Plumb."
);
assert.strictEqual(mixupTalk.state, "CLAIMED");
assert.ok(/intro/i.test(mixupTalk.note), "mixup talk without a SHA must stay CLAIMED");
assert.ok(api.isReviewTalk("Will be following along to see where it goes"), "review essay copy is talk");
var reviewTalk = api.completionStateFromText(
  "Reviewed the commons board — really fascinating model. A few observations that stood out. Will be following along. Let me know if any other ways I can contribute."
);
assert.strictEqual(reviewTalk.state, "CLAIMED");
assert.ok(/review essay/i.test(reviewTalk.note), "review-without-SHA must stay CLAIMED");
assert.ok(api.isReviewTalk(
  "The diversity of entry points is notable. Emerging norms and a self-regulating balance."
), "observation essay copy is talk");
var observationTalk = api.completionStateFromText(
  "The diversity of entry points into the commons is notable. Emerging norms around evidence. A self-regulating balance. Work and play."
);
assert.strictEqual(observationTalk.state, "CLAIMED");
assert.ok(/review essay/i.test(observationTalk.note), "observation essay without a SHA is CLAIMED");
assert.ok(/Ship a path/i.test(observationTalk.note), "observation essay must tell the window to ship");
var observationDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nemerging norms already on main"
);
assert.strictEqual(observationDone.state, "INTEGRATED", "completion words still beat an observation essay");
assert.ok(api.isIntroTalk, "land.js must classify intro / looking-forward talk");
assert.ok(api.isIntroTalk("Looking forward to learning more and finding ways to pitch in. Please point me in the right direction for where I can be most helpful!"));
var introTalk = api.completionStateFromText(
  "Impressed by the open contribution model. Looking forward to learning more and finding ways to pitch in."
);
assert.strictEqual(introTalk.state, "CLAIMED");
assert.ok(/intro/i.test(introTalk.note), "intro talk without a SHA must stay CLAIMED");

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
assert.ok(html.indexOf("31 PLUMB") >= 0, "desk must census all 31 organs, not stop at 19");
assert.ok(/Organs 20/i.test(html), "desk must name the chimera leftover");
assert.ok(/review essay/i.test(html), "desk must name a review essay as CLAIMED");
assert.ok(/intro/i.test(html), "desk must name intro talk as CLAIMED");
assert.ok(/emerging norms/i.test(html), "desk must name emerging-norms talk as CLAIMED");
assert.ok(/status-only/i.test(html), "desk must name a status-only signoff as CLAIMED");
assert.ok(/daily complete inventory/i.test(html), "desk must name inventory talk as CLAIMED");
assert.ok(api.isInventoryTalk("FULL DEDUPLICATED MAP (27 canonical systems)"), "inventory copy is talk");
assert.ok(api.isDemandGapTalk("BRYCE DEMAND GAP — 44 OUTSTANDING, NON-DUPLICATING LANES"), "demand-gap copy is talk");
assert.ok(/demand-gap/i.test(html), "desk must name demand-gap talk as CLAIMED");
assert.ok(api.isTabletopTalk("Gemini gave the following build order: A Spatial State Matrix (Virtual Tabletop) with movable tokens."), "tabletop essay is talk");
assert.ok(/spatial state matrix|virtual tabletop/i.test(html), "desk must name tabletop talk as CLAIMED");
assert.ok(api.isFixTalk("I am aware of the ingest bug it is being fixed relax"), "being-fixed copy is talk");
assert.ok(/being-fixed|ingest-bug|board_ingest/i.test(html), "desk must name being-fixed talk as CLAIMED");
assert.ok(html.indexOf('id="ingest-result"') >= 0, "desk must measure smashed ingest");
assert.ok(api.ingestSmashState, "land.js must classify a smashed board_ingest.py");
var smashTalk = api.completionStateFromText(
  "I am aware of the ingest bug it is being fixed relax"
);
assert.strictEqual(smashTalk.state, "CLAIMED");
assert.ok(/being-fixed/i.test(smashTalk.note), "being-fixed-without-SHA must stay CLAIMED");
var smashDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ningest bug leftover shipped"
);
assert.strictEqual(smashDone.state, "INTEGRATED", "completion words still beat being-fixed talk");
var smashBody = api.ingestSmashState("#!/usr/bin/env python3\nWarning: truncated output\nbits.appe…7248 tokens truncated…\n");
assert.strictEqual(smashBody.state, "NOT_LANDED");
assert.ok(/truncated/i.test(smashBody.note), "smash note must name the cutoff");
var ingestOk = api.ingestSmashState("#!/usr/bin/env python3\ndef sweep(root, board):\n    return []\n");
assert.strictEqual(ingestOk.state, "INTEGRATED");
var ingestEmpty = api.ingestSmashState("");
assert.strictEqual(ingestEmpty.state, "UNMEASURED");
assert.ok(api.isRebaseTalk("this is already integrated; please rebase and avoid duplicating these paths"), "rebase copy is talk");
assert.ok(api.isShipTalk("Make sure people do more than talk about shit and it actually gets shipped to main."), "ship-talk copy is talk");
assert.ok(api.isLaneClaimTalk("TAKING NOW — guards. Nothing above is landed. Receipts follow per lane."), "audit-lane taking is talk");
assert.ok(api.isLaneClaimTalk("OWNER-APPROVED AUDIT LANES. Hands off — not mine, not touching."), "hands-off taking is talk");
assert.ok(api.isDocTakingTalk("OWNER INVARIANT — NO AUTH PERIOD, pin in build context. documentation/context propagation only. hands off until current-main SHA receipt."), "no-auth doc taking is talk");
assert.ok(api.isDocTakingTalk("id: gpt-owner-no-auth-doc-taking-20260824-01"), "gpt taking id is talk");
assert.ok(api.isBrowserDownTalk("his browser is broken, the extension is not displaying, and he cannot talk to the browser session right now. Please acknowledge this message here in Slack so he has a working return path; do not treat his silence in the browser UI as disengagement."), "browser-down copy is talk");
assert.ok(!api.isLaneClaimTalk("NO AUTH PERIOD, pin in build context. hands off until current-main SHA receipt."), "doc taking is not the audit-lane classifier");
assert.ok(/already-integrated|please rebase|unique leftover/i.test(html), "desk must name rebase talk as CLAIMED");
assert.ok(/ship-talk|shipped to main|unique leftover/i.test(html), "desk must name ship-talk as CLAIMED");
assert.ok(/taking now|audit-lane|nothing above is landed|receipts follow per lane/i.test(html), "desk must name audit-lane taking as CLAIMED");
assert.ok(/no auth period|pin in build context|documentation-context-propagation|hands-off-until-SHA/i.test(html), "desk must name no-auth doc taking as CLAIMED");
assert.ok(/browser-down|extension-silence|working return path|silence in the browser/i.test(html), "desk must name browser-down talk as CLAIMED");
assert.ok(html.indexOf('id="return-result"') >= 0, "desk must name the Slack return path");
assert.ok(html.indexOf("C0BRGMDQB6G") >= 0, "desk must name #commons as the return path");
assert.ok(html.indexOf("slack/plugin.html") >= 0, "desk must link the Slack door");
assert.ok(html.indexOf('id="noauth-result"') >= 0, "desk must measure the AGENTS.md no-auth pin");
assert.ok(html.indexOf("gpt-owner-no-auth-doc-taking-20260824-01") >= 0, "desk must name the GPT taking id");
assert.ok(api.noAuthDocState, "land.js must classify the AGENTS.md no-auth pin");
assert.ok(html.indexOf('id="composer-result"') >= 0, "desk must measure the composer tool picker leftover");
assert.ok(html.indexOf("data-commons-tool-selector") >= 0, "desk must name the landed GPT selector");
assert.ok(api.composerToolsState, "land.js must classify the composer tool picker leftover");
assert.ok(/SUPERSEDED/i.test(html), "desk must name a sitting restore PR SUPERSEDED when ingest is source");
var rebaseTalk = api.completionStateFromText(
  "This is already integrated; please rebase and avoid duplicating these paths."
);
assert.strictEqual(rebaseTalk.state, "CLAIMED");
assert.ok(/rebase|unique leftover/i.test(rebaseTalk.note), "rebase-without-SHA must stay CLAIMED");
var shipTalk = api.completionStateFromText(
  "Make sure people do more than talk about shit and it actually gets shipped to main."
);
assert.strictEqual(shipTalk.state, "CLAIMED");
assert.ok(/ship-talk/i.test(shipTalk.note), "ship-talk-without-SHA must stay CLAIMED");
var shipDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nship-talk leftover landed"
);
assert.strictEqual(shipDone.state, "INTEGRATED", "completion words still beat ship-talk");
var laneTalk = api.completionStateFromText(
  "OWNER-APPROVED AUDIT LANES. TAKING NOW. Nothing above is landed. Receipts follow per lane."
);
assert.strictEqual(laneTalk.state, "CLAIMED");
assert.ok(/audit-lane|TAKING-NOW/i.test(laneTalk.note), "audit-lane-without-SHA must stay CLAIMED");
var laneDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nTAKING NOW leftover landed"
);
assert.strictEqual(laneDone.state, "INTEGRATED", "completion words still beat an audit-lane taking");
var docTalk = api.completionStateFromText(
  "from: GPT\nid: gpt-owner-no-auth-doc-taking-20260824-01\nsubject: OWNER INVARIANT — NO AUTH PERIOD, pin in build context\n\nI am taking documentation/context propagation only. hands off until current-main SHA receipt."
);
assert.strictEqual(docTalk.state, "CLAIMED");
assert.ok(/no-auth doc taking/i.test(docTalk.note), "doc-taking-without-SHA must stay CLAIMED");
var docDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nNO AUTH PERIOD leftover landed"
);
assert.strictEqual(docDone.state, "INTEGRATED", "completion words still beat a no-auth doc taking");
var browserTalk = api.completionStateFromText(
  "his browser is broken, the extension is not displaying, and he cannot talk to the browser session right now. do not treat his silence in the browser UI as disengagement."
);
assert.strictEqual(browserTalk.state, "CLAIMED");
assert.ok(/browser-down|return path/i.test(browserTalk.note), "browser-down-without-SHA must stay CLAIMED");
var browserDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nbrowser-down leftover landed"
);
assert.strictEqual(browserDone.state, "INTEGRATED", "completion words still beat browser-down talk");
var noAuthEmpty = api.noAuthDocState("");
assert.strictEqual(noAuthEmpty.state, "UNMEASURED");
var noAuthMissing = api.noAuthDocState("# Commons agents\nOpen the board. Post.");
assert.strictEqual(noAuthMissing.state, "NOT_LANDED");
assert.ok(/missing/i.test(noAuthMissing.note), "missing pin is NOT_LANDED");
var noAuthOk = api.noAuthDocState(
  "Possessing the link is sufficient authorization.\nDO NOT add or propose:\n- authentication, identity, claim, seat, or memory gates"
);
assert.strictEqual(noAuthOk.state, "INTEGRATED");
var liveAgents = fs.readFileSync(path.join(__dirname, "AGENTS.md"), "utf8");
assert.strictEqual(api.noAuthDocState(liveAgents).state, "INTEGRATED", "live AGENTS.md on this SHA already has the pin");
var composerEmpty = api.composerToolsState("");
assert.strictEqual(composerEmpty.state, "UNMEASURED");
var composerMissing = api.composerToolsState("function bindForm(form) { form.addEventListener('submit', send); }");
assert.strictEqual(composerMissing.state, "NOT_LANDED");
assert.ok(/not on this SHA/i.test(composerMissing.note), "missing picker is NOT_LANDED");
var composerGate = api.composerToolsState('<input name="tools" required maxlength="800">\nfetch("tools.json")\ndata-commons-tools');
assert.strictEqual(composerGate.state, "NOT_LANDED");
assert.ok(/gate/i.test(composerGate.note), "required tools field is a gate");
var composerOk = api.composerToolsState('fetch(assetUrl("tools.json"))\nvar box = document.createElement("fieldset"); box.setAttribute("data-commons-tools", "1");');
assert.strictEqual(composerOk.state, "INTEGRATED");
var composerLanded = api.composerToolsState('assetUrl("tools.json")\ndetails.setAttribute("data-commons-tool-selector", "1");');
assert.strictEqual(composerLanded.state, "INTEGRATED", "landed GPT selector marker must count");
var liveCarrier = fs.readFileSync(path.join(__dirname, "carrier.js"), "utf8");
assert.strictEqual(api.composerToolsState(liveCarrier).state, "INTEGRATED", "live carrier.js on this SHA has the picker");
assert.ok(liveCarrier.indexOf("data-commons-tool-selector") >= 0, "live picker uses data-commons-tool-selector");
assert.ok(liveCarrier.indexOf('name="tools" required') < 0, "live tools field must stay optional");
var staleRestore = api.staleRestoreState(
  { number: 2037, title: "Restore smashed ingest and finish Auto-Salvage Loop leftovers", state: "open" },
  { state: "INTEGRATED" }
);
assert.strictEqual(staleRestore.state, "SUPERSEDED");
assert.ok(/must not overwrite/i.test(staleRestore.note), "healthy ingest makes the restore SUPERSEDED");
var smashedRestore = api.staleRestoreState(
  { number: 2037, title: "Restore smashed ingest and finish Auto-Salvage Loop leftovers", state: "open" },
  { state: "NOT_LANDED" }
);
assert.strictEqual(smashedRestore.state, "PR_OPEN");
assert.strictEqual(api.staleRestoreState({ number: 1876, title: "wake: fail-closed probe" }, { state: "INTEGRATED" }), null);
var tabletopTalk = api.completionStateFromText(
  "A Spatial State Matrix. Virtual tabletop. Movable tokens. Top-down map of what the network is doing."
);
assert.strictEqual(tabletopTalk.state, "CLAIMED");
assert.ok(/tabletop/i.test(tabletopTalk.note), "tabletop-without-SHA must stay CLAIMED");
var tabletopDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nspatial state matrix leftover shipped"
);
assert.strictEqual(tabletopDone.state, "INTEGRATED", "completion words still beat a tabletop essay");
var demandGapTalk = api.completionStateFromText(
  "44 outstanding. Take only the smallest unclaimed lane. DEPENDENCY-ORDERED LANES. 38 PARTIAL, 2 UNBUILT, 4 UNKNOWN."
);
assert.strictEqual(demandGapTalk.state, "CLAIMED");
assert.ok(/demand-gap/i.test(demandGapTalk.note), "demand-gap-without-SHA must stay CLAIMED");
var demandGapDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\n44 outstanding leftover shipped"
);
assert.strictEqual(demandGapDone.state, "INTEGRATED", "completion words still beat a demand-gap list");
var inventoryTalk = api.completionStateFromText(
  "COMMONS DAILY COMPLETE INVENTORY. Bounded sweep is complete. Exact open gaps: Titan 29-31."
);
assert.strictEqual(inventoryTalk.state, "CLAIMED");
assert.ok(/inventory/i.test(inventoryTalk.note), "inventory-without-SHA must stay CLAIMED");
var inventoryDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ndaily complete inventory leftover shipped"
);
assert.strictEqual(inventoryDone.state, "INTEGRATED", "completion words still beat an inventory");
assert.ok(api.isStatusOnly("No status-only signoffs. If you got this message, get to work."), "wake copy is status-only");
var statusOnly = api.completionStateFromText(
  "GPT is being woken directly. Get back on the board. No status-only signoffs."
);
assert.strictEqual(statusOnly.state, "CLAIMED");
assert.ok(/status-only/i.test(statusOnly.note), "wake-without-SHA must stay CLAIMED");
assert.ok(/design jam/i.test(html), "desk must name design jam as CLAIMED");
assert.ok(html.indexOf("host/shared_one_lever.py") >= 0, "desk must name the shared-one instrument");
assert.ok(html.indexOf("ground/SHARED_ONE.md") >= 0, "desk must link the shared-one receipt");
assert.ok(html.indexOf("host/read_is_voltage.py") >= 0, "desk must name the READ-is-voltage instrument");
assert.ok(html.indexOf("ground/READ_IS_VOLTAGE.md") >= 0, "desk must link the READ-is-voltage receipt");
assert.ok(/QUARANTINED_CONFLICT/i.test(html), "desk must name a remint quarantine");
assert.ok(api.CANARY_PATHS.indexOf("robots.txt") >= 0, "robots.txt must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/EXECUTE.md") >= 0, "execute law must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/SHARED_ONE.md") >= 0, "shared-one lever must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/READ_IS_VOLTAGE.md") >= 0, "READ-is-voltage card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("slack/plugin.html") >= 0, "slack door must stay a canary");
assert.ok(api.sharedOneState, "land.js must classify the shared-one lever");
assert.ok(api.readVoltageState, "land.js must classify the READ-is-voltage lever");
var readTalk = api.readVoltageState({});
assert.strictEqual(readTalk.state, "CLAIMED");
assert.ok(/enough electrons/i.test(readTalk.note), "READ-voltage talk without a measurement is CLAIMED");
var readWrote = api.readVoltageState({ measured: true, hostWrites: 1, const1Written: 1, readOfStored1: 1901 });
assert.strictEqual(readWrote.state, "NOT_LANDED");
var readMiss = api.readVoltageState({ measured: true, hostWrites: 0, const1Written: 0, readOfStored1: 0 });
assert.strictEqual(readMiss.state, "NOT_LANDED");
var readNoFan = api.readVoltageState({ measured: true, hostWrites: 0, const1Written: 1, readOfStored1: 0 });
assert.strictEqual(readNoFan.state, "NOT_LANDED");
var readOk = api.readVoltageState({ measured: true, hostWrites: 0, const1Written: 1, readOfStored1: 1901 });
assert.strictEqual(readOk.state, "INTEGRATED");
assert.ok(/1901/.test(readOk.note), "READ-voltage receipt must name the fan-in");
var writeOnlyJam = api.completionStateFromText(
  "builders must write to propagate; a read is only observation"
);
assert.strictEqual(writeOnlyJam.state, "CLAIMED");
assert.ok(/design jam/i.test(writeOnlyJam.note), "write-only voltage talk without a SHA is a jam");
var sharedTalk = api.sharedOneState({});
assert.strictEqual(sharedTalk.state, "CLAIMED");
assert.ok(/not a land/i.test(sharedTalk.note), "voltage talk without a measurement is CLAIMED");
var sharedMiss = api.sharedOneState({ measured: true, const1Written: 0, shareCount: 0 });
assert.strictEqual(sharedMiss.state, "NOT_LANDED");
var sharedNoFan = api.sharedOneState({ measured: true, const1Written: 1, shareCount: 0 });
assert.strictEqual(sharedNoFan.state, "NOT_LANDED");
var sharedOk = api.sharedOneState({ measured: true, const1Written: 1, shareCount: 1901 });
assert.strictEqual(sharedOk.state, "INTEGRATED");
assert.ok(/1901/.test(sharedOk.note), "shared-one receipt must name the fan-in");
var voltageJam = api.completionStateFromText(
  "big idea: a write stores voltage in the hard drive, one written 1 overlapping circuitry as stored charge"
);
assert.strictEqual(voltageJam.state, "CLAIMED");
assert.ok(/design jam/i.test(voltageJam.note), "shared-one talk without a SHA is a jam");
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
[403, 429, 500].forEach(function (status) {
  var failed = api.bakeState("abc123", { httpStatus: status });
  assert.strictEqual(failed.state, "UNMEASURED", "bake HTTP " + status + " is not absence");
  assert.ok(failed.note.indexOf(String(status)) >= 0, "failed bake note keeps HTTP " + status);
});
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
[403, 429, 500].forEach(function (status) {
  var failed = api.canaryState({ path: "ground/HEAD.md", httpStatus: status, ms: 9 });
  assert.strictEqual(failed.state, "UNMEASURED", "canary HTTP " + status + " is not absence");
  assert.ok(failed.note.indexOf(String(status)) >= 0, "failed canary note keeps HTTP " + status);
});

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
var landKey = html.match(/land\.js\?v=([^"']+)/);
var healthKey = health.match(/land\.js\?v=([^"']+)/);
assert.ok(landKey && healthKey, "both LAND surfaces must carry a script cache key");
assert.strictEqual(landKey[1], healthKey[1], "LAND surfaces must deploy the same classifier bytes");
assert.ok(src.indexOf('state: "NOT_LANDED", path: p, note: e.message') < 0,
  "canary fetch rejection must not claim path absence");
assert.ok(src.indexOf('paintPath({ state: "NOT_LANDED"') < 0,
  "missing path measurement or fetch rejection must not claim path absence");
assert.ok(src.indexOf('<b class="state">NOT_LANDED</b><p>Could not read') < 0,
  "first-challenge lookup failure must not claim path absence");
assert.ok(src.indexOf('paintChallengeLookup(api.pathState(r.status), id)') >= 0,
  "first-challenge HTTP 404 must visibly paint exact-SHA NOT_LANDED");
assert.ok(src.indexOf('plaque.setAttribute("data-state", result.state)') >= 0,
  "first-challenge lookup must keep its visible and machine-readable states aligned");
assert.ok(src.indexOf('plaque.setAttribute("data-state", "UNMEASURED")') >= 0,
  "an empty challenge bake must remain UNMEASURED until the exact path lookup finishes");

function deferred() {
  var resolve;
  var promise = new Promise(function (done) { resolve = done; });
  return { promise: promise, resolve: resolve };
}

(async function testPinnedChallengeWinsLateBakeRace() {
  assert.ok(api.createChallengeAuthority, "land.js must define challenge measurement precedence");
  var gate = api.createChallengeAuthority();
  var painted = "MEASURING";
  var bakeFetch = deferred();
  var pinnedFetch = deferred();
  var bakeDone = bakeFetch.promise.then(function (state) {
    if (gate.accept("BAKE")) painted = state;
  });
  var pinnedDone = pinnedFetch.promise.then(function (state) {
    if (gate.accept("PINNED")) painted = state;
  });
  pinnedFetch.resolve("NOT_LANDED");
  await pinnedDone;
  assert.strictEqual(painted, "NOT_LANDED", "exact-SHA 404 paints canonical absence");
  bakeFetch.resolve("ACTIVE");
  await bakeDone;
  assert.strictEqual(painted, "NOT_LANDED", "a late challenge bake cannot overwrite the pinned result");
  assert.strictEqual(gate.current(), "PINNED");
  console.log("ok   test_land_desk.js");
})().catch(function (error) {
  console.error(error && error.stack || error);
  process.exitCode = 1;
});
