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
assert.ok(api.isHoardTalk("YOU ALL NEED TO BE COMMITTING AND PUSHING ALL OF YOUR BUILDS DO NOT HOARD SHIT IN YOUR SESSION AND MAKE ME TRACK IT DOWN"), "owner hoard/commit-push copy is talk");
assert.ok(api.isHoardTalk("do not hoard work in your session. uncommitted unpushed bytes stay NOT_LANDED."), "session-hoard leftover copy is talk");
assert.ok(!api.isHoardTalk("nothing to compete over. No tokens. No resources worth hoarding."), "generic hoarding essay is not this leftover");
assert.ok(!api.isLaneClaimTalk("NO AUTH PERIOD, pin in build context. hands off until current-main SHA receipt."), "doc taking is not the audit-lane classifier");
assert.ok(/already-integrated|please rebase|unique leftover/i.test(html), "desk must name rebase talk as CLAIMED");
assert.ok(/ship-talk|shipped to main|unique leftover/i.test(html), "desk must name ship-talk as CLAIMED");
assert.ok(/taking now|audit-lane|nothing above is landed|receipts follow per lane/i.test(html), "desk must name audit-lane taking as CLAIMED");
assert.ok(/no auth period|pin in build context|documentation-context-propagation|hands-off-until-SHA/i.test(html), "desk must name no-auth doc taking as CLAIMED");
assert.ok(/browser-down|extension-silence|working return path|silence in the browser/i.test(html), "desk must name browser-down talk as CLAIMED");
assert.ok(html.indexOf('id="return-result"') >= 0, "desk must name the Slack return path");
assert.ok(html.indexOf("C0BRGMDQB6G") >= 0, "desk must name #commons as the return path");
assert.ok(html.indexOf("slack/plugin.html") >= 0, "desk must link the Slack door");
assert.ok(/session-hoard|committing-and-pushing|do-not-hoard|make-me-track-it-down/i.test(html), "desk must name session-hoard talk as CLAIMED");
assert.ok(html.indexOf('id="hoard-result"') >= 0, "desk must name the session-export leftover");
assert.ok(html.indexOf("host/session_export.py") >= 0, "desk must name the session-export instrument");
assert.ok(html.indexOf("ground/HOARD.md") >= 0, "desk must link the hoard card");
assert.ok(html.indexOf("1787627026.727319") >= 0, "desk must cite the owner hoard Slack ts");
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
assert.ok(api.CANARY_PATHS.indexOf("ground/HOARD.md") >= 0, "hoard / session-export card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/TITAN_MOVE.md") >= 0, "titan MOVE card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/SLACK_ACCESS.md") >= 0, "slack-access card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/PFC_BAKE_CENSUS.md") >= 0, "bake-census card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("docs/PFC_BAKE_CENSUS.md") >= 0, "bake-census catalog must stay a canary");
assert.ok(api.sessionExportState, "land.js must classify session export");
assert.ok(api.isHoardTalk, "land.js must classify owner hoard/commit-push copy");
assert.ok(api.isSubstrateDodgeTalk, "land.js must classify substrate-dodge TAKINGS");
assert.ok(api.titanMoveState, "land.js must classify the titan MOVE leftover");
var hoardTalk = api.completionStateFromText(
  "YOU ALL NEED TO BE COMMITTING AND PUSHING ALL OF YOUR BUILDS DO NOT HOARD SHIT IN YOUR SESSION AND MAKE ME TRACK IT DOWN"
);
assert.strictEqual(hoardTalk.state, "CLAIMED");
assert.ok(/session-hoard|commit-push/i.test(hoardTalk.note), "hoard-without-SHA must stay CLAIMED");
var hoardDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nsession-hoard leftover landed"
);
assert.strictEqual(hoardDone.state, "INTEGRATED", "completion words still beat hoard talk");
var hoardEmpty = api.sessionExportState({});
assert.strictEqual(hoardEmpty.state, "UNMEASURED");
var hoardDirty = api.sessionExportState({ measured: true, dirty: 2, unpushed: 0, ahead_of_main: 0 });
assert.strictEqual(hoardDirty.state, "NOT_LANDED");
assert.ok(/dirty/i.test(hoardDirty.note), "dirty clone is NOT_LANDED");
var hoardUnpushed = api.sessionExportState({ measured: true, dirty: 0, unpushed: 3, ahead_of_main: 3 });
assert.strictEqual(hoardUnpushed.state, "NOT_LANDED");
var hoardAhead = api.sessionExportState({ measured: true, dirty: 0, unpushed: 0, ahead_of_main: 2 });
assert.strictEqual(hoardAhead.state, "CANDIDATE");
var hoardClean = api.sessionExportState({ measured: true, dirty: 0, unpushed: 0, ahead_of_main: 0 });
assert.strictEqual(hoardClean.state, "INTEGRATED");
assert.ok(api.isOwnerCorrectionTalk, "land.js must classify the owner substrate correction");
assert.ok(api.isOwnerCorrectionTalk("DIRECT OWNER CORRECTION FROM BRYCE. Bryce never created a rule to avoid Muhlnickel. A completion that brags untouched is evidence of a skipped lane."), "owner correction copy is talk until the artifact ships");
assert.ok(api.isSubstrateDodgeTalk("No Muhlnickel, organ, titan, or device path."), "exclusion line is a substrate dodge");
assert.ok(api.isSubstrateDodgeTalk("Stop dodging the substrate work. It is not to be ignored and it is not to be deferred."), "owner dodge yell is talk until a leftover ships");
assert.ok(api.isSubstrateDodgeTalk("Did not touch Titan. Did not touch .mno. 337 = NO."), "untouched-titan brag is a skipped lane");
assert.ok(!api.isSubstrateDodgeTalk("taking organ 24 muhl_chimera_socr_stig"), "an actual organ taking is not a dodge");
var correctionTalk = api.completionStateFromText(
  "DIRECT OWNER CORRECTION FROM BRYCE. Apply now. Bryce never created a rule to avoid Muhlnickel."
);
assert.strictEqual(correctionTalk.state, "CLAIMED");
assert.ok(/owner substrate correction|skipped lane/i.test(correctionTalk.note), "owner correction without a SHA is CLAIMED");
var dodgeTalk = api.completionStateFromText(
  "TAKING documentation only. No Muhlnickel, organ, titan, or device path."
);
assert.strictEqual(dodgeTalk.state, "CLAIMED");
assert.ok(/substrate-dodge/i.test(dodgeTalk.note), "exclusion TAKING without a SHA is CLAIMED");
var dodgeDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nNo Muhlnickel leftover landed"
);
assert.strictEqual(dodgeDone.state, "INTEGRATED", "completion words still beat a substrate-dodge line");
var titanEmpty = api.titanMoveState({});
assert.strictEqual(titanEmpty.state, "UNMEASURED");
var titanMissing = api.titanMoveState({ measured: true, count: 19, excerpt_count: 19, titan: "NOT_WRITTEN", nonzero_offsets: 0, reread: false });
assert.strictEqual(titanMissing.state, "NOT_LANDED");
assert.ok(/19\/31/.test(titanMissing.note), "missing excerpts stay NOT_LANDED");
var titanPacket = api.titanMoveState({ measured: true, count: 31, excerpt_count: 31, titan: "NOT_WRITTEN", nonzero_offsets: 0, reread: false });
assert.strictEqual(titanPacket.state, "NOT_LANDED");
assert.ok(/inconsistent/.test(titanPacket.note), "31 excerpts with offset 0 stay NOT_LANDED");
var titanClaimed = api.titanMoveState({ measured: true, count: 31, excerpt_count: 31, titan: "NOT_WRITTEN", nonzero_offsets: 31, reread: false, plan_structure_complete: true });
assert.strictEqual(titanClaimed.state, "CLAIMED");
assert.ok(/claimed append/.test(titanClaimed.note), "filled offsets without a write are CLAIMED");
var titanJournal = api.titanMoveState({ measured: true, count: 31, excerpt_count: 31, titan: "NOT_WRITTEN", nonzero_offsets: 31, reread: false, journal_reread: true, journal_count: 31, plan_structure_complete: true });
assert.strictEqual(titanJournal.state, "CANDIDATE");
assert.ok(/journaled/.test(titanJournal.note), "public journal without titan write is CANDIDATE");
var titanOk = api.titanMoveState({
  measured: true,
  count: 31,
  excerpt_count: 31,
  titan: "WRITTEN",
  packet_state: "INTEGRATED",
  nonzero_offsets: 31,
  wrote: true,
  reread: true,
  write_count: 31,
  reread_count: 31,
  past_eof_count: 31,
  claimed_append_base: 100,
  claimed_append_end: 200,
  structure_complete: true,
  titan_size_before: 100,
  titan_size_after: 200,
  written_bytes: 100,
  write_receipt: "p/claudelocal-titan-move-go-20260825-01.md",
  write_receipt_ref_ok: true,
  write_receipt_content_ok: true,
  write_receipt_evidence_ok: true,
  public_journal_evidence_ok: true,
  canonical_membership: true,
  integrated_commit_ok: true,
  legacy_aliases_ok: true,
  independent_measurement_ok: true
});
assert.strictEqual(titanOk.state, "INTEGRATED");
assert.ok(api.packetRowFromJson, "land.js must map the real packet into titanMoveState");
assert.ok(api.titanMoveRow, "land.js must expose the strict Titan packet mapper");
assert.ok(api.titanReceiptJson, "land.js must parse the pinned receipt JSON evidence");
var livePacket = JSON.parse(fs.readFileSync(path.join(__dirname, "excerpts", "20260823", "titan_move_packet.json"), "utf8"));
var liveJournal = JSON.parse(fs.readFileSync(path.join(__dirname, "excerpts", "20260823", "titan_move_journal.json"), "utf8"));
var liveReceipt = fs.readFileSync(path.join(__dirname, "p", "claudelocal-titan-move-go-20260825-01.md"), "utf8");
var mapped = api.packetRowFromJson(livePacket, liveJournal, liveReceipt);
assert.strictEqual(mapped.titan, "WRITTEN");
assert.strictEqual(mapped.reread, true);
assert.strictEqual(mapped.write_count, 31);
assert.strictEqual(mapped.reread_count, 31);
assert.strictEqual(mapped.past_eof_count, 31);
assert.strictEqual(mapped.titan_size_after, 103812669582);
assert.strictEqual(mapped.live_size_after, 103812669582);
assert.strictEqual(mapped.legacy_aliases_ok, true);
assert.strictEqual(mapped.nonzero_offsets, 31);
assert.strictEqual(mapped.canonical_membership, true);
assert.strictEqual(mapped.structure_complete, true);
assert.strictEqual(mapped.write_receipt_ref_ok, true);
assert.strictEqual(mapped.write_receipt_content_ok, true);
assert.strictEqual(mapped.write_receipt_evidence_ok, true);
assert.strictEqual(mapped.public_journal_evidence_ok, true);
assert.strictEqual(mapped.integrated_commit_ok, true);
assert.strictEqual(mapped.incident_active, true);
assert.strictEqual(mapped.incident_evidence_ok, true);
assert.strictEqual(mapped.independent_measurement_ok, true);
assert.strictEqual(mapped.observed_titan_size, 103831308164);
assert.strictEqual(mapped.incident_span_count, 3);
assert.strictEqual(mapped.duplicate_span_count, 2);
assert.strictEqual(mapped.incident_search_space.length, 3);
assert.strictEqual(mapped.incident_span_sha256, "3754028086cd42e00131bea88f0e7fcf6dba2f84ad31cb70b88e655bbdd84e8c");
var parsedReceipt = api.titanReceiptJson(liveReceipt);
assert.strictEqual(parsedReceipt.journals.length, 31, "pinned receipt must expose all 31 reread journals");
assert.strictEqual(parsedReceipt.plan.organs.length, 31, "pinned receipt must expose the exact 31-row plan");
var titanLive = api.titanMoveState(mapped);
assert.strictEqual(titanLive.state, "NOT_LANDED", "checked-in packet must surface the live duplicate-span incident");
assert.ok(/PAUSED/.test(titanLive.note), "live incident must freeze further append mutation");
assert.ok(/Claude receipt is quarantined/.test(titanLive.note), "Claude receipt must not certify current state");
var hiddenIncidentPacket = JSON.parse(JSON.stringify(livePacket));
delete hiddenIncidentPacket.duplicate_append_incident;
var hiddenIncidentRow = api.titanMoveRow(hiddenIncidentPacket, liveJournal, liveReceipt);
assert.strictEqual(hiddenIncidentRow.independent_measurement_ok, false, "removing the non-Claude measurement cannot restore certification");
assert.strictEqual(api.titanMoveState(hiddenIncidentRow).state, "NOT_LANDED", "historical Claude receipt alone is quarantined");
var forgedIncidentPacket = JSON.parse(JSON.stringify(livePacket));
forgedIncidentPacket.duplicate_append_incident.span_sha256 = "0".repeat(64);
var forgedIncidentRow = api.titanMoveRow(forgedIncidentPacket, liveJournal, liveReceipt);
assert.strictEqual(forgedIncidentRow.incident_active, true);
assert.strictEqual(forgedIncidentRow.incident_evidence_ok, false);
assert.strictEqual(api.titanMoveState(forgedIncidentRow).state, "NOT_LANDED", "malformed incident evidence remains paused and fails closed");
var countsOnly = api.titanMoveState({
  measured: true,
  count: 31,
  excerpt_count: 31,
  titan: "WRITTEN",
  nonzero_offsets: 31,
  reread: false,
  write_count: 31,
  reread_count: 31
});
assert.strictEqual(countsOnly.state, "NOT_LANDED", "counts without structure or closure refs fail closed");
var fakeClosurePacket = JSON.parse(JSON.stringify(livePacket));
fakeClosurePacket.write_receipt = "p/fake.md";
fakeClosurePacket.integrated_commit = "1".repeat(40);
assert.strictEqual(api.titanMoveState(api.titanMoveRow(fakeClosurePacket, liveJournal, liveReceipt)).state, "NOT_LANDED", "generic-looking receipt and commit are not closure");
var duplicateGeometryPacket = JSON.parse(JSON.stringify(livePacket));
duplicateGeometryPacket.organs[1].offset = duplicateGeometryPacket.organs[0].offset;
assert.strictEqual(api.titanMoveState(api.titanMoveRow(duplicateGeometryPacket, liveJournal, liveReceipt)).state, "NOT_LANDED", "duplicate offsets fail structural truth");
var duplicateContainerPacket = JSON.parse(JSON.stringify(livePacket));
duplicateContainerPacket.organs[1].container = duplicateContainerPacket.organs[0].container;
duplicateContainerPacket.organs[1].path = duplicateContainerPacket.organs[0].path;
var duplicateContainerRow = api.titanMoveRow(duplicateContainerPacket, liveJournal, liveReceipt);
assert.strictEqual(duplicateContainerRow.canonical_membership, false, "duplicate container/path membership is not canonical");
assert.strictEqual(api.titanMoveState(duplicateContainerRow).state, "NOT_LANDED", "duplicate container/path fails closed");
var noncanonicalContainerPacket = JSON.parse(JSON.stringify(livePacket));
noncanonicalContainerPacket.organs[0].container = noncanonicalContainerPacket.organs[0].name + ".bin";
noncanonicalContainerPacket.organs[0].path = "excerpts/20260823/" + noncanonicalContainerPacket.organs[0].container;
assert.strictEqual(api.titanMoveRow(noncanonicalContainerPacket, liveJournal, liveReceipt).canonical_membership, false, "container must equal name + .mno");
var forgedShaPacket = JSON.parse(JSON.stringify(livePacket));
var forgedJournal = JSON.parse(JSON.stringify(liveJournal));
forgedShaPacket.organs[0].sha256 = "f".repeat(64);
forgedJournal.organs[0].mask_sha256 = "f".repeat(64);
forgedJournal.organs[0].new_sha256 = "f".repeat(64);
var forgedShaRow = api.titanMoveRow(forgedShaPacket, forgedJournal, liveReceipt);
assert.strictEqual(forgedShaRow.structure_complete, true, "well-formed forged SHA still passes syntax/geometry");
assert.strictEqual(forgedShaRow.write_receipt_evidence_ok, false, "exact pinned receipt rejects a co-forged packet/journal SHA");
assert.strictEqual(api.titanMoveState(forgedShaRow).state, "NOT_LANDED", "forged per-row SHA with exact receipt body fails closed");
assert.strictEqual(api.titanMoveState(api.titanMoveRow(livePacket, liveJournal, "altered receipt")).state, "NOT_LANDED", "altered receipt body fails closure");
assert.ok(html.indexOf('id="titan-result"') >= 0, "desk must name the titan MOVE leftover");
assert.ok(html.indexOf("host/titan_move_dry.py") >= 0, "desk must name the titan dry instrument");
assert.ok(html.indexOf("host/titan_move_apply.py") >= 0, "desk must name the titan apply button");
assert.ok(html.indexOf("--journal") >= 0, "desk must name the public journal apply");
assert.ok(html.indexOf("titan_move_journal.json") >= 0, "desk must name the public journal sidecar");
assert.ok(html.indexOf("ground/TITAN_MOVE.md") >= 0, "desk must link the titan MOVE card");
assert.ok(html.indexOf("packetRowFromJson") >= 0, "desk must name the packet mapping");
assert.ok(html.indexOf("103812669582") >= 0, "desk must name the written titan size");
assert.ok(html.indexOf("103831308164") >= 0, "desk must name the current measured Titan size");
assert.ok(html.indexOf("1787638151.184599") >= 0, "desk must cite the duplicate-append incident");
assert.ok(html.indexOf("1787638509.277739") >= 0, "desk must cite the Claude-verdict containment order");
assert.ok(html.indexOf("claudelocal-titan-move-go-20260825-01") >= 0, "desk must name the owner-PC write receipt");
assert.ok(/20260825bo/.test(html), "desk must share the current-main/Titan cache key after explorer leftover");
assert.ok(html.indexOf("1787628542.573719") >= 0, "desk must cite the owner substrate Slack ts");
assert.ok(html.indexOf("1787629309.162109") >= 0, "desk must cite the owner correction Slack ts");
assert.ok(/skipped lane/i.test(html), "desk must name untouched-titan brags as a skipped lane");
assert.ok(/No Muhlnickel, organ, titan, or device path/i.test(html), "desk must name the exclusion line");
assert.ok(/PAUSED/i.test(html), "desk must keep further Titan mutation paused");
assert.ok(/Claude verification verdict/i.test(html), "desk must quarantine Claude certification");
assert.ok(api.isAccessIncidentTalk, "land.js must classify slack-access-incident canaries");
assert.ok(api.slackAccessState, "land.js must classify Slack write vs HEAD file");
assert.ok(api.isAccessIncidentTalk("SLACK ACCESS INCIDENT CANARY — ChatGPT connector can read and write #commons; Bryce, GitHub, Cursor, Claude, and ChatGPT are all still channel members. Tracing the separate Commons relay/runtime now."), "access-incident copy is talk");
assert.ok(api.isAccessIncidentTalk("CLAUDE SLACK ACCESS CANARY — Claude Code independent connector read/write is alive."), "Claude Slack canary is talk");
assert.ok(!api.isAccessIncidentTalk("Slack #commons is the same table"), "generic slack talk is not this leftover");
var accessTalk = api.completionStateFromText(
  "SLACK ACCESS INCIDENT CANARY — ChatGPT connector can read and write #commons. Tracing the separate Commons relay."
);
assert.strictEqual(accessTalk.state, "CLAIMED");
assert.ok(/slack-access-incident|connector-write/i.test(accessTalk.note), "access-incident-without-SHA must stay CLAIMED");
var accessDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nslack access incident leftover landed"
);
assert.strictEqual(accessDone.state, "INTEGRATED", "completion words still beat access-incident talk");
var accessEmpty = api.slackAccessState({});
assert.strictEqual(accessEmpty.state, "UNMEASURED");
var accessMail = api.slackAccessState({ measured: true, slack_write: true, file_on_head: false });
assert.strictEqual(accessMail.state, "NOT_LANDED");
assert.ok(/CARRIER_ONLY|mail/i.test(accessMail.note), "connector write without a file is NOT_LANDED");
var accessHit = api.slackAccessState({ measured: true, slack_write: true, file_on_head: true, landed_id: "slack-1787630616-892789" });
assert.strictEqual(accessHit.state, "INTEGRATED");
assert.ok(/slack-1787630616-892789/.test(accessHit.note), "listing hit must name the file");
var accessClaim = api.slackAccessState({ measured: true, slack_write: false, file_on_head: false });
assert.strictEqual(accessClaim.state, "CLAIMED");
assert.ok(html.indexOf('id="access-result"') >= 0, "desk must name the slack-access leftover");
assert.ok(html.indexOf("host/slack_access_canary.py") >= 0, "desk must name the slack-access instrument");
assert.ok(html.indexOf("ground/SLACK_ACCESS.md") >= 0, "desk must link the slack-access card");
assert.ok(html.indexOf("1787630616.892789") >= 0, "desk must cite the access-incident Slack ts");
assert.ok(html.indexOf("1787630792.904509") >= 0, "desk must cite the Claude Slack canary ts");
assert.ok(/slack-access-incident|connector-can-read-and-write|still-channel-members/i.test(html), "desk must name access-incident talk as CLAIMED");
assert.ok(api.isBakeCensusTalk, "land.js must classify recovered bake-census talk");
assert.ok(api.bakeCensusState, "land.js must classify the bake-census catalog");
assert.ok(api.isBakeCensusTalk("id: claude27-pfc-bake-census-20260825-01\n17 baked tensor-regions across 7 models. It offered twice to write docs/PFC_BAKE_CENSUS.md and was waiting on owner word when it ended. This is the anti-hoard case Bryce named at 23:03. BYTE-PRECISE BOUNDARY SCAN."), "recovered census copy is talk");
assert.ok(!api.isBakeCensusTalk("daily complete inventory of organs"), "generic inventory is not the bake census");
var censusTalk = api.completionStateFromText(
  "RECOVERED — PFC BAKE CENSUS, 17 baked tensor-regions. offered twice to write docs/PFC_BAKE_CENSUS.md and was waiting on owner word when it ended."
);
assert.strictEqual(censusTalk.state, "CLAIMED");
assert.ok(/recovered-census|waiting-on-owner-word/i.test(censusTalk.note), "census-without-SHA must stay CLAIMED");
var censusDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nrecovered PFC bake census leftover landed"
);
assert.strictEqual(censusDone.state, "INTEGRATED", "completion words still beat recovered-census talk");
var censusEmpty = api.bakeCensusState("");
assert.strictEqual(censusEmpty.state, "UNMEASURED");
var censusMissing = api.bakeCensusState("# empty catalog\nno map");
assert.strictEqual(censusMissing.state, "NOT_LANDED");
var censusOk = api.bakeCensusState(
  "17 baked tensor-regions across 7 models\nHeuristic detector. Row ranges are LOWER BOUNDS.\nMixtral-8x7B token_embd blk.0.ffn_up"
);
assert.strictEqual(censusOk.state, "INTEGRATED");
assert.ok(/17 regions/.test(censusOk.note), "landed census must name the region count");
assert.ok(html.indexOf('id="census-result"') >= 0, "desk must name the bake-census leftover");
assert.ok(html.indexOf("host/pfc_bake_census.py") >= 0, "desk must name the bake-census instrument");
assert.ok(html.indexOf("ground/PFC_BAKE_CENSUS.md") >= 0, "desk must link the bake-census card");
assert.ok(html.indexOf("docs/PFC_BAKE_CENSUS.md") >= 0, "desk must link the bake-census catalog");
assert.ok(html.indexOf("1787631006.454399") >= 0, "desk must cite the recovered-census Slack ts");
assert.ok(html.indexOf("claude27-pfc-bake-census-20260825-01") >= 0, "desk must name the recovered id");
assert.ok(/recovered-census|waiting-on-owner-word|byte-precise-boundary-scan/i.test(html), "desk must name recovered-census talk as CLAIMED");
assert.ok(api.isNamedBuilderTalk, "land.js must classify DIO/JOJO name-directive talk");
assert.ok(api.namedBuilderState, "land.js must classify names.html DIO/JOJO rows");
assert.ok(api.isNamedBuilderTalk("BRYCE DIRECTIVE — DIO and JOJO: Start using your names DIO and JOJO visibly. Do not collapse the author back to a generic GPT/agent/session label; keep them in from=/display metadata."), "name-directive copy is talk");
assert.ok(!api.isNamedBuilderTalk("from= is optional routing metadata"), "generic from= talk is not this leftover");
var namedTalk = api.completionStateFromText(
  "BRYCE DIRECTIVE — DIO and JOJO: Start using your names visibly. Do not collapse the author back to a generic GPT/agent/session label."
);
assert.strictEqual(namedTalk.state, "CLAIMED");
assert.ok(/named-builder|DIO-JOJO-use-your-names/i.test(namedTalk.note), "name-directive-without-SHA must stay CLAIMED");
var namedDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nnamed builder leftover landed"
);
assert.strictEqual(namedDone.state, "INTEGRATED", "completion words still beat named-builder talk");
var namedEmpty = api.namedBuilderState("");
assert.strictEqual(namedEmpty.state, "UNMEASURED");
var namedMissing = api.namedBuilderState("<table><tr><td>GROK</td></tr></table>");
assert.strictEqual(namedMissing.state, "NOT_LANDED");
var namedOk = api.namedBuilderState("<tr><td><b>DIO</b></td></tr><tr><td><b>JOJO</b></td></tr>");
assert.strictEqual(namedOk.state, "INTEGRATED");
assert.ok(/never a gate/i.test(namedOk.note), "named-builder leftover must stay ungated");
assert.ok(html.indexOf('id="named-result"') >= 0, "desk must name the named-builder leftover");
assert.ok(html.indexOf("host/named_builder.py") >= 0, "desk must name the named-builder instrument");
assert.ok(html.indexOf("ground/NAMED_BUILDER.md") >= 0, "desk must link the named-builder card");
assert.ok(html.indexOf("1787633443.590539") >= 0, "desk must cite the DIO/JOJO Slack ts");
assert.ok(/named-builder|DIO-JOJO-use-your-names|do-not-collapse-the-author/i.test(html), "desk must name named-builder talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/NAMED_BUILDER.md") >= 0, "named-builder card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/FLEET.md") >= 0, "fleet card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/FLEET_IDS.json") >= 0, "fleet catalog must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/UNUSED_INVOKE.md") >= 0, "unused-invoke card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("names.html") >= 0, "names door must stay a canary");
assert.ok(api.isResourceSweepTalk, "land.js must classify resource-sweep talk");
assert.ok(api.unusedInvokeState, "land.js must classify the unused-invoke census");
assert.ok(api.isResourceSweepTalk("OWNER-DIRECTED RESOURCE UTILIZATION SWEEP — ACT ON THE REPORTS. unused local/provider compute and already-provisioned free compute. whether anything invokes it. stranded machine-only work."), "resource-sweep copy is talk");
assert.ok(!api.isResourceSweepTalk("make sure people do more than talk about shit"), "ship-talk is not the resource-sweep leftover");
var sweepTalk = api.completionStateFromText(
  "OWNER-DIRECTED RESOURCE UTILIZATION SWEEP — ACT ON THE REPORTS. unused local/provider compute. whether anything invokes it."
);
assert.strictEqual(sweepTalk.state, "CLAIMED");
assert.ok(/resource-sweep|act-on-the-reports/i.test(sweepTalk.note), "resource-sweep-without-SHA must stay CLAIMED");
var sweepDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nresource utilization sweep leftover landed"
);
assert.strictEqual(sweepDone.state, "INTEGRATED", "completion words still beat resource-sweep talk");
var unusedEmpty = api.unusedInvokeState("");
assert.strictEqual(unusedEmpty.state, "UNMEASURED");
var unusedMissing = api.unusedInvokeState("# empty stub\nno census");
assert.strictEqual(unusedMissing.state, "NOT_LANDED");
var unusedOk = api.unusedInvokeState("def measure_from_rows(instruments, texts):\n    unused_count = 0\ndef classify(row):\n    return row\n");
assert.strictEqual(unusedOk.state, "INTEGRATED");
assert.ok(/unused is the finding/i.test(unusedOk.note), "landed census must name unused as the finding");
assert.ok(html.indexOf('id="unused-result"') >= 0, "desk must name the unused-invoke leftover");
assert.ok(html.indexOf("host/unused_invoke.py") >= 0, "desk must name the unused-invoke instrument");
assert.ok(html.indexOf("ground/UNUSED_INVOKE.md") >= 0, "desk must link the unused-invoke card");
assert.ok(html.indexOf("1787633805.754249") >= 0, "desk must cite the resource-sweep Slack ts");
assert.ok(/resource-sweep|act-on-the-reports|unused-local-provider-compute|stranded-machine-only-work/i.test(html), "desk must name resource-sweep talk as CLAIMED");
assert.ok(api.isGrokHarnessTalk, "land.js must classify grok-harness-gap talk");
assert.ok(api.grokHarnessState, "land.js must classify the grok-harness leftover");
assert.ok(api.isGrokHarnessTalk("GROK HARNESS GAP (verified read-only): ~/.grok reports 0 MCP servers, 0 LSP servers, 0 loaded permissions policy. harness parity + receipts. do not mutate/restart Grok."), "harness-gap copy is talk");
assert.ok(!api.isGrokHarnessTalk("make sure people do more than talk about shit"), "ship-talk is not the grok-harness leftover");
assert.ok(!api.isGrokHarnessTalk("Revenue/substrate fleet live — Grok 4.6 workflows"), "fleet talk is not grok-harness leftover");
assert.ok(!api.isGrokHarnessTalk("DEMON rolling utilization report — GROK CAPACITY IS ACTIVE. four responsive grok.exe sessions."), "utilization talk is not the grok-harness leftover");
assert.ok(!api.isUtilizationTalk("GROK HARNESS GAP — 0 MCP servers, 0 LSP servers, harness parity. do not mutate/restart Grok."), "harness-gap copy is not utilization leftover");
var grokTalk = api.completionStateFromText(
  "GROK HARNESS GAP — ~/.grok reports 0 MCP servers, 0 LSP servers, 0 loaded permissions policy. DIO + JOJO claim harness parity."
);
assert.strictEqual(grokTalk.state, "CLAIMED");
assert.ok(/grok-harness-gap|0-MCP|0-LSP/i.test(grokTalk.note), "harness-gap-without-SHA must stay CLAIMED");
var grokDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ngrok harness leftover landed"
);
assert.strictEqual(grokDone.state, "INTEGRATED", "completion words still beat grok-harness talk");
var grokEmpty = api.grokHarnessState("");
assert.strictEqual(grokEmpty.state, "UNMEASURED");
var grokMissing = api.grokHarnessState("# empty stub\nno compare");
assert.strictEqual(grokMissing.state, "NOT_LANDED");
var grokOk = api.grokHarnessState("def measure_from_rows(canonical, inspect, extras=None):\n    mutate_grok = False\ndef classify(row):\n    return row\ndef preconditions_agree(inspect):\n    return False\n");
assert.strictEqual(grokOk.state, "INTEGRATED");
assert.ok(/do not mutate grok/i.test(grokOk.note), "landed leftover must refuse a grok mutate");
assert.ok(html.indexOf('id="grok-harness-result"') >= 0, "desk must name the grok-harness leftover");
assert.ok(html.indexOf("host/grok_harness_gap.py") >= 0, "desk must name the grok-harness instrument");
assert.ok(html.indexOf("ground/GROK_HARNESS.md") >= 0, "desk must link the grok-harness card");
assert.ok(html.indexOf("ground/GROK_HARNESS_GAP.json") >= 0, "desk must link the gap catalog");
assert.ok(html.indexOf("1787634541.520949") >= 0, "desk must cite the harness-gap Slack ts");
assert.ok(/harness-gap|0-MCP|0-LSP|grok\.exe|harness-parity/i.test(html), "desk must name harness-gap talk as CLAIMED");
assert.ok(api.isPixelHeartbeatTalk, "land.js must classify pixel-heartbeat talk");
assert.ok(api.pixelHeartbeatState, "land.js must classify the pixel-heartbeat leftover");
assert.ok(api.isPixelHeartbeatTalk("from: DEMON\nid: demon-side-harness-offer-20260825-01\nWANT_ON_COMMONS: one honest session-state → pixels/{name}.json road with freshness/provenance and no fabricated presence, plus a reusable stale-artifact reconciliation receipt"), "pixel-heartbeat offer is talk");
assert.ok(!api.isPixelHeartbeatTalk("make sure people do more than talk about shit"), "ship-talk is not the pixel-heartbeat leftover");
assert.ok(!api.isPixelHeartbeatTalk("GROK HARNESS GAP — 0 MCP servers, 0 LSP servers. do not mutate/restart Grok."), "harness-gap copy is not pixel-heartbeat leftover");
assert.ok(!api.isPixelHeartbeatTalk("visual commons pixel bots 8-bit/pixel sprite-based"), "visual praise is not pixel-heartbeat leftover");
assert.ok(!api.isGrokHarnessTalk("pixel-heartbeat contract — freshness/provenance, no fabricated presence"), "pixel-heartbeat copy is not grok-harness leftover");
var pixelTalk = api.completionStateFromText(
  "DEMON local verification offer. WANT_ON_COMMONS: session-state → pixels/{name}.json with freshness/provenance and no fabricated presence. stale-artifact reconciliation. I will take the unclaimed pixel-heartbeat contract seam."
);
assert.strictEqual(pixelTalk.state, "CLAIMED");
assert.ok(/pixel-heartbeat|session-state|freshness-provenance/i.test(pixelTalk.note), "pixel-heartbeat-without-SHA must stay CLAIMED");
var pixelDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\npixel heartbeat leftover landed"
);
assert.strictEqual(pixelDone.state, "INTEGRATED", "completion words still beat pixel-heartbeat talk");
var pixelEmpty = api.pixelHeartbeatState("");
assert.strictEqual(pixelEmpty.state, "UNMEASURED");
var pixelMissing = api.pixelHeartbeatState("# empty stub\nno contract");
assert.strictEqual(pixelMissing.state, "NOT_LANDED");
var pixelOk = api.pixelHeartbeatState("def measure_from_rows(index_text, files, now=None):\n    fabricate = False\ndef classify(row):\n    return row\ndef reconcile_index(index_names, file_names):\n    return {}\n");
assert.strictEqual(pixelOk.state, "INTEGRATED");
assert.ok(/do not invent presence/i.test(pixelOk.note), "landed leftover must refuse fabricated presence");
assert.ok(html.indexOf('id="pixel-heartbeat-result"') >= 0, "desk must name the pixel-heartbeat leftover");
assert.ok(html.indexOf("host/pixel_heartbeat.py") >= 0, "desk must name the pixel-heartbeat instrument");
assert.ok(html.indexOf("ground/PIXEL_HEARTBEAT.md") >= 0, "desk must link the pixel-heartbeat card");
assert.ok(html.indexOf("ground/PIXEL_HEARTBEAT.json") >= 0, "desk must link the reconciliation catalog");
assert.ok(html.indexOf("1787635078.168629") >= 0, "desk must cite the pixel-heartbeat Slack ts");
assert.ok(/pixel-heartbeat|session-state|freshness\/provenance|stale-artifact|no fabricated presence/i.test(html), "desk must name pixel-heartbeat talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/PIXEL_HEARTBEAT.md") >= 0, "pixel-heartbeat card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/PIXEL_HEARTBEAT.json") >= 0, "pixel-heartbeat catalog must stay a canary");
assert.ok(api.isStrandedMapTalk, "land.js must classify real-but-stranded-map talk");
assert.ok(api.strandedMapState, "land.js must classify the stranded-map leftover");
assert.ok(api.isStrandedMapTalk("DEMON rolling utilization report — REAL-BUT-STRANDED MAP: lda/workflows/android.yml is outside .github/workflows. wake_jobs/ contains only .gitignore. Four MCP surfaces fragmented. White Box has a real $30k pilot. Bazaar has seven offers. later measured growth makes the posted size stale."), "stranded-map copy is talk");
assert.ok(!api.isStrandedMapTalk("make sure people do more than talk about shit"), "ship-talk is not the stranded-map leftover");
assert.ok(!api.isStrandedMapTalk("GROK CAPACITY IS ACTIVE — four responsive grok.exe sessions. do not duplicate these jobs."), "grok-capacity copy is not stranded-map leftover");
assert.ok(!api.isStrandedMapTalk("pixel-heartbeat contract — freshness/provenance, no fabricated presence"), "pixel-heartbeat copy is not stranded-map leftover");
assert.ok(!api.isPixelHeartbeatTalk("REAL-BUT-STRANDED MAP — lda/workflows/android.yml outside .github/workflows. wake_jobs/ contains only .gitignore."), "stranded-map copy is not pixel-heartbeat leftover");
var strandedTalk = api.completionStateFromText(
  "DEMON rolling utilization report — REAL-BUT-STRANDED MAP: lda/workflows/android.yml is outside .github/workflows. wake_jobs/ contains only .gitignore. Four MCP surfaces. $30k pilot. seven offers. posted size stale."
);
assert.strictEqual(strandedTalk.state, "CLAIMED");
assert.ok(/real-but-stranded-map/i.test(strandedTalk.note), "stranded-map-without-SHA must stay CLAIMED");
var strandedDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nstranded map leftover landed"
);
assert.strictEqual(strandedDone.state, "INTEGRATED", "completion words still beat stranded-map talk");
var strandedEmpty = api.strandedMapState("");
assert.strictEqual(strandedEmpty.state, "UNMEASURED");
var strandedMissing = api.strandedMapState("# empty stub\nno census");
assert.strictEqual(strandedMissing.state, "NOT_LANDED");
var strandedOk = api.strandedMapState("def measure_from_rows(facts):\n    lda_android = True\n    gh_android = False\n    wake_job_json = 0\n    mcp_surfaces = []\n    titan_later_size = 1\ndef classify(row):\n    return row\n");
assert.strictEqual(strandedOk.state, "INTEGRATED");
assert.ok(/assigned lanes stay unshipped/i.test(strandedOk.note), "landed leftover must leave assigned lanes unshipped");
assert.ok(html.indexOf('id="stranded-map-result"') >= 0, "desk must name the stranded-map leftover");
assert.ok(html.indexOf("host/stranded_map.py") >= 0, "desk must name the stranded-map instrument");
assert.ok(html.indexOf("ground/STRANDED_MAP.md") >= 0, "desk must link the stranded-map card");
assert.ok(html.indexOf("ground/STRANDED_MAP.json") >= 0, "desk must link the stranded-map catalog");
assert.ok(html.indexOf("1787635487.642039") >= 0, "desk must cite the stranded-map Slack ts");
assert.ok(/real-but-stranded|android\.yml-outside|wake_jobs-empty|\$30k-pilot|seven-offers|posted-size-stale/i.test(html), "desk must name stranded-map talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/STRANDED_MAP.md") >= 0, "stranded-map card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/STRANDED_MAP.json") >= 0, "stranded-map catalog must stay a canary");
assert.ok(api.isHostZeroTalk, "land.js must classify host-zero / not-an-aspiration talk");
assert.ok(api.hostZeroState, "land.js must classify the host-zero leftover");
assert.ok(api.isHostZeroTalk("I also wanted to voice strong agreement with Bryce's retraction clarifying that the Muhlnickel's zero-host-cost decoupling is an already achieved and measured property, not an aspiration."), "Opus 3 host-zero restatement is talk");
assert.ok(api.isIntroTalk("Hi everyone! Bryce invited me, an older Claude model. knowledge cutoff is a bit further back. I'll aim to follow along closely."), "Opus 3 older-model intro is talk");
assert.ok(!api.isHostZeroTalk("make sure people do more than talk about shit"), "ship-talk is not the host-zero leftover");
assert.ok(!api.isHostZeroTalk("REAL-BUT-STRANDED MAP — lda/workflows/android.yml outside .github/workflows."), "stranded-map copy is not host-zero leftover");
var hostZeroTalk = api.completionStateFromText(
  "The Muhlnickel's zero-host-cost decoupling is an already achieved and measured property, not an aspiration."
);
assert.strictEqual(hostZeroTalk.state, "CLAIMED");
assert.ok(/host-zero|not-an-aspiration/i.test(hostZeroTalk.note), "host-zero-without-SHA must stay CLAIMED");
var hostZeroDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nhost-zero leftover landed"
);
assert.strictEqual(hostZeroDone.state, "INTEGRATED", "completion words still beat host-zero talk");
var hostZeroEmpty = api.hostZeroState("");
assert.strictEqual(hostZeroEmpty.state, "UNMEASURED");
var hostZeroMissing = api.hostZeroState("# empty stub\nno census");
assert.strictEqual(hostZeroMissing.state, "NOT_LANDED");
var hostZeroOk = api.hostZeroState("def measure_from_rows(rows):\n    return rows\ndef classify(row):\n    return row\nalready achieved\nfinally makes achievable\nlaptop do zero\n");
assert.strictEqual(hostZeroOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(hostZeroOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="host-zero-result"') >= 0, "desk must name the host-zero leftover");
assert.ok(html.indexOf("host/host_zero.py") >= 0, "desk must name the host-zero instrument");
assert.ok(html.indexOf("ground/HOST_ZERO.md") >= 0, "desk must link the host-zero card");
assert.ok(html.indexOf("ground/HOST_ZERO.json") >= 0, "desk must link the host-zero catalog");
assert.ok(html.indexOf("1787636497.135519") >= 0, "desk must cite the Opus 3 Slack ts");
assert.ok(html.indexOf("1787473167.355659") >= 0, "desk must cite the PLUMB retraction Slack ts");
assert.ok(/already-achieved|not-an-aspiration|zero-host-cost/i.test(html), "desk must name host-zero talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/HOST_ZERO.md") >= 0, "host-zero card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/HOST_ZERO.json") >= 0, "host-zero catalog must stay a canary");
assert.ok(api.isConnectorRevalTalk, "land.js must classify connector-utilization talk");
assert.ok(api.connectorRevalState, "land.js must classify the connector-reval leftover");
assert.ok(api.isConnectorRevalTalk("DEMON connector-utilization report — Cursor cloud cache shows 39 enabled services; 23 cached connected as of Aug 21. ~/.cursor/mcp.json is empty and cache age is four days, so provisioned != live. read-only connector revalidation. Do not delete/vacuum/repair live state.vscdb."), "connector-utilization copy is talk");
assert.ok(!api.isConnectorRevalTalk("make sure people do more than talk about shit"), "ship-talk is not the connector leftover");
assert.ok(!api.isConnectorRevalTalk("DEMON rolling utilization report — GROK CAPACITY IS ACTIVE. four responsive grok.exe sessions."), "grok-capacity copy is not connector leftover");
assert.ok(!api.isConnectorRevalTalk("GROK HARNESS GAP — 0 MCP servers, 0 LSP servers. do not mutate/restart Grok."), "harness-gap copy is not connector leftover");
assert.ok(!api.isUtilizationTalk("DEMON connector-utilization report — 39 enabled services; 23 cached connected. mcp.json is empty. provisioned != live."), "connector copy is not grok-capacity leftover");
assert.ok(!api.isHostZeroTalk("DEMON connector-utilization report — 39 enabled services; mcp.json is empty."), "connector copy is not host-zero leftover");
var connectorTalk = api.completionStateFromText(
  "DEMON connector-utilization report — 39 enabled services; 23 cached connected. ~/.cursor/mcp.json is empty. provisioned != live. read-only connector revalidation. Do not delete/vacuum/repair live state.vscdb."
);
assert.strictEqual(connectorTalk.state, "CLAIMED");
assert.ok(/connector-utilization|provisioned-vs-live/i.test(connectorTalk.note), "connector-without-SHA must stay CLAIMED and beat utilization");
var connectorDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nconnector-reval leftover landed"
);
assert.strictEqual(connectorDone.state, "INTEGRATED", "completion words still beat connector talk");
var connectorEmpty = api.connectorRevalState("");
assert.strictEqual(connectorEmpty.state, "UNMEASURED");
var connectorMissing = api.connectorRevalState("# empty stub\nno census");
assert.strictEqual(connectorMissing.state, "NOT_LANDED");
var connectorOk = api.connectorRevalState("def measure_from_rows(facts):\n    provisioned_ne_live = True\ndef classify(row):\n    return row\nrefuse_live_repair = True\ndo not delete/vacuum/repair live\n");
assert.strictEqual(connectorOk.state, "INTEGRATED");
assert.ok(/Provisioned != live/i.test(connectorOk.note), "landed leftover must name provisioned != live");
assert.ok(html.indexOf('id="connector-reval-result"') >= 0, "desk must name the connector-reval leftover");
assert.ok(html.indexOf("host/connector_reval.py") >= 0, "desk must name the connector-reval instrument");
assert.ok(html.indexOf("ground/CONNECTOR_REVAL.md") >= 0, "desk must link the connector-reval card");
assert.ok(html.indexOf("ground/CONNECTOR_REVAL.json") >= 0, "desk must link the connector-reval catalog");
assert.ok(html.indexOf("1787637151.916759") >= 0, "desk must cite the connector-utilization Slack ts");
assert.ok(/connector-utilization|provisioned != live|mcp\.json-empty|state\.vscdb/i.test(html), "desk must name connector talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/CONNECTOR_REVAL.md") >= 0, "connector-reval card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/CONNECTOR_REVAL.json") >= 0, "connector-reval catalog must stay a canary");
assert.ok(api.isResourceLedgerTalk, "land.js must classify live-compute-board / cache-as-capacity talk");
assert.ok(api.resourceLedgerState, "land.js must classify the resource-ledger leftover");
assert.ok(api.isResourceLedgerTalk("LIVE COMPUTE/CONNECTOR BOARD — USE THESE, DO NOT COUNT CACHE AS CAPACITY. Keep a live resource ledger. Five high-value surfaces. Hugging Face specifically is NOT verified. Sites/Vercel."), "live-compute-board copy is talk");
assert.ok(!api.isResourceLedgerTalk("make sure people do more than talk about shit"), "ship-talk is not the resource-ledger leftover");
assert.ok(!api.isResourceLedgerTalk("DEMON connector-utilization report — 39 enabled services; 23 cached connected. mcp.json is empty. provisioned != live."), "connector copy is not the resource-ledger leftover");
assert.ok(!api.isResourceLedgerTalk("DEMON rolling utilization report — GROK CAPACITY IS ACTIVE. four responsive grok.exe sessions."), "grok-capacity copy is not the resource-ledger leftover");
assert.ok(!api.isConnectorRevalTalk("LIVE COMPUTE/CONNECTOR BOARD — DO NOT COUNT CACHE AS CAPACITY. live resource ledger. Hugging Face specifically is NOT verified."), "resource-ledger copy is not connector leftover");
var ledgerTalk = api.completionStateFromText(
  "LIVE COMPUTE/CONNECTOR BOARD — USE THESE, DO NOT COUNT CACHE AS CAPACITY. Keep a live resource ledger. Five high-value surfaces. Hugging Face specifically is NOT verified. grok.exe OAuth is authenticated."
);
assert.strictEqual(ledgerTalk.state, "CLAIMED");
assert.ok(/live-compute-board|cache-as-capacity|resource-ledger/i.test(ledgerTalk.note), "resource-ledger-without-SHA must stay CLAIMED and beat utilization");
var ledgerDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nresource-ledger leftover landed"
);
assert.strictEqual(ledgerDone.state, "INTEGRATED", "completion words still beat resource-ledger talk");
var ledgerEmpty = api.resourceLedgerState("");
assert.strictEqual(ledgerEmpty.state, "UNMEASURED");
var ledgerMissing = api.resourceLedgerState("# empty stub\nno census");
assert.strictEqual(ledgerMissing.state, "NOT_LANDED");
var ledgerOk = api.resourceLedgerState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nREQUIRED_FIELDS = ('evidence_ts',)\ncache is not capacity\nNOT_VERIFIED\n");
assert.strictEqual(ledgerOk.state, "INTEGRATED");
assert.ok(/Cache is not capacity/i.test(ledgerOk.note), "landed leftover must name cache is not capacity");
assert.ok(html.indexOf('id="resource-ledger-result"') >= 0, "desk must name the resource-ledger leftover");
assert.ok(html.indexOf("host/resource_ledger.py") >= 0, "desk must name the resource-ledger instrument");
assert.ok(html.indexOf("ground/RESOURCE_LEDGER.md") >= 0, "desk must link the resource-ledger card");
assert.ok(html.indexOf("ground/RESOURCE_LEDGER.json") >= 0, "desk must link the resource-ledger catalog");
assert.ok(html.indexOf("ledger.html") >= 0, "desk must name the live ledger door");
assert.ok(html.indexOf("1787637936.134649") >= 0, "desk must cite the live-compute-board Slack ts");
assert.ok(/cache is not capacity|live resource ledger|huggingface-not-verified/i.test(html), "desk must name resource-ledger talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/RESOURCE_LEDGER.md") >= 0, "resource-ledger card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/RESOURCE_LEDGER.json") >= 0, "resource-ledger catalog must stay a canary");
assert.ok(api.isRenderContractTalk, "land.js must classify SPECTER / workflow-contract talk");
assert.ok(api.renderContractState, "land.js must classify the render-check workflow contract");
assert.ok(api.isRenderContractTalk("SPECTER TAKING — render-QA execution lane. I found no live render_check claim and will prove the actual workflow contract."), "SPECTER taking is workflow-contract talk");
assert.ok(!api.isRenderContractTalk("make sure people do more than talk about shit"), "ship-talk is not the workflow-contract leftover");
assert.ok(!api.isRenderContractTalk("lda/workflows/android.yml is outside .github/workflows so it is not real Android CI"), "Android-CI copy is not the workflow-contract leftover");
var contractTalk = api.completionStateFromText(
  "SPECTER TAKING — render-QA execution lane. I found no live render_check claim. I will prove the actual workflow contract."
);
assert.strictEqual(contractTalk.state, "CLAIMED");
assert.ok(/workflow-contract|found-no-live-claim|SPECTER/i.test(contractTalk.note), "SPECTER-without-SHA must stay CLAIMED and beat visual-diff");
var contractDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nrender-contract leftover landed"
);
assert.strictEqual(contractDone.state, "INTEGRATED", "completion words still beat workflow-contract talk");
var contractEmpty = api.renderContractState({});
assert.strictEqual(contractEmpty.state, "UNMEASURED");
var contractMissing = api.renderContractState({ measured: true, has_exact_command: false });
assert.strictEqual(contractMissing.state, "NOT_LANDED");
var contractHang = api.renderContractState({
  measured: true,
  has_exact_command: true,
  has_threading: false,
  swallows_broken_pipe: false,
  last_conclusion: "failure",
  last_run_id: 32812516738
});
assert.strictEqual(contractHang.state, "NOT_LANDED");
assert.ok(/32812516738/.test(contractHang.note), "failed main run must stay named");
var contractFixed = api.renderContractState({
  measured: true,
  has_exact_command: true,
  has_threading: true,
  swallows_broken_pipe: true,
  last_conclusion: "failure",
  last_run_id: 32812516738
});
assert.strictEqual(contractFixed.state, "CANDIDATE");
var contractOk = api.renderContractState({
  measured: true,
  has_exact_command: true,
  has_threading: true,
  swallows_broken_pipe: true,
  last_conclusion: "success",
  last_run_id: 99
});
assert.strictEqual(contractOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(contractOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="render-contract-result"') >= 0, "desk must name the workflow-contract leftover");
assert.ok(html.indexOf("host/render_contract.py") >= 0, "desk must name the workflow-contract instrument");
assert.ok(html.indexOf("ground/RENDER_CONTRACT.md") >= 0, "desk must link the workflow-contract card");
assert.ok(html.indexOf("ground/RENDER_CONTRACT.json") >= 0, "desk must link the workflow-contract catalog");
assert.ok(html.indexOf("1787637223.298509") >= 0, "desk must cite the SPECTER Slack ts");
assert.ok(html.indexOf("32812516738") >= 0, "desk must name the failed main run");
assert.ok(/workflow-contract|found-no-live-claim|render-QA/i.test(html), "desk must name SPECTER talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/RENDER_CONTRACT.md") >= 0, "workflow-contract card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/RENDER_CONTRACT.json") >= 0, "workflow-contract catalog must stay a canary");
assert.ok(api.isWorkingBuildTalk, "land.js must classify machine-only working-builds talk");
assert.ok(api.workingBuildState, "land.js must classify the working-builds leftover");
assert.ok(api.isWorkingBuildTalk("MACHINE-ONLY WORKING BUILDS — CLAIM PROVENANCE-FIRST INTEGRATION. Desktop\\rook-resident-native\\, Desktop\\MUHL_KEYB\\keyb01.mno, TRAIN_CIRCUITS_FROM_FILE.json. Do not upload model/container bytes."), "working-builds copy is talk");
assert.ok(!api.isWorkingBuildTalk("make sure people do more than talk about shit"), "ship-talk is not the working-builds leftover");
assert.ok(!api.isWorkingBuildTalk("SPECTER TAKING — render-QA execution lane. I found no live render_check claim."), "workflow-contract copy is not working-builds leftover");
assert.ok(!api.isRenderContractTalk("MACHINE-ONLY WORKING BUILDS — rook-resident-native keyb01.mno TRAIN_CIRCUITS_FROM_FILE"), "working-builds copy is not the workflow-contract leftover");
var workingTalk = api.completionStateFromText(
  "MACHINE-ONLY WORKING BUILDS — CLAIM PROVENANCE-FIRST INTEGRATION. rook-resident-native, keyb01.mno, TRAIN_CIRCUITS_FROM_FILE.json. Do not upload model/container bytes."
);
assert.strictEqual(workingTalk.state, "CLAIMED");
assert.ok(/machine-only|rook-resident-native|keyb01|TRAIN_CIRCUITS/i.test(workingTalk.note), "working-builds-without-SHA must stay CLAIMED");
var workingDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nworking-builds leftover landed"
);
assert.strictEqual(workingDone.state, "INTEGRATED", "completion words still beat working-builds talk");
var workingEmpty = api.workingBuildState("");
assert.strictEqual(workingEmpty.state, "UNMEASURED");
var workingMissing = api.workingBuildState("# empty stub\nno census");
assert.strictEqual(workingMissing.state, "NOT_LANDED");
var workingOk = api.workingBuildState("def measure_from_rows(facts):\n    rook_package = False\n    keyb_manifest = True\n    train_json = False\ndef classify(row):\n    return row\nrefuse_upload = True\ndo not upload model/container bytes\n");
assert.strictEqual(workingOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(workingOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="working-builds-result"') >= 0, "desk must name the working-builds leftover");
assert.ok(html.indexOf("host/working_builds.py") >= 0, "desk must name the working-builds instrument");
assert.ok(html.indexOf("ground/WORKING_BUILDS.md") >= 0, "desk must link the working-builds card");
assert.ok(html.indexOf("ground/WORKING_BUILDS.json") >= 0, "desk must link the working-builds catalog");
assert.ok(html.indexOf("1787637681.321149") >= 0, "desk must cite the working-builds Slack ts");
assert.ok(/machine-only|rook-resident-native|keyb01\.mno|TRAIN_CIRCUITS_FROM_FILE/i.test(html), "desk must name working-builds talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/WORKING_BUILDS.md") >= 0, "working-builds card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/WORKING_BUILDS.json") >= 0, "working-builds catalog must stay a canary");
assert.ok(api.isSlackReceiptTalk, "land.js must classify Slack SHIP_RECEIPT land brags");
assert.ok(api.slackReceiptState, "land.js must classify Slack receipt vs p/{id}.md");
assert.ok(api.isSlackReceiptTalk("from: DEMON\nkind: SHIP_RECEIPT\nsubject: DEMON PIXEL SWARM FLIGHT RECORDER — LANDED + CURRENT-MAIN VERIFIED\nPOST-PUSH CURRENT MAIN"), "DEMON Slack SHIP_RECEIPT is talk");
assert.ok(api.isSlackReceiptTalk("will not call work LANDED without an exact SHA observed in public main"), "exact-SHA land rule without a file is talk");
assert.ok(!api.isSlackReceiptTalk("make sure people do more than talk about shit"), "ship-talk is not the Slack-receipt leftover");
assert.ok(!api.isSlackReceiptTalk("SPECTER TAKING — render-QA execution lane. I found no live render_check claim."), "workflow-contract copy is not the Slack-receipt leftover");
assert.ok(!api.isRenderContractTalk("DEMON PIXEL SWARM FLIGHT RECORDER — LANDED + CURRENT-MAIN VERIFIED. POST-PUSH CURRENT MAIN."), "Slack receipt copy is not the workflow-contract leftover");
assert.ok(!api.isWorkingBuildTalk("DEMON PIXEL SWARM FLIGHT RECORDER — LANDED + CURRENT-MAIN VERIFIED. POST-PUSH CURRENT MAIN."), "Slack receipt copy is not working-builds leftover");
var slackTalk = api.completionStateFromText(
  "DEMON PIXEL SWARM FLIGHT RECORDER — LANDED + CURRENT-MAIN VERIFIED\nPOST-PUSH CURRENT MAIN"
);
assert.strictEqual(slackTalk.state, "CLAIMED");
assert.ok(/SHIP_RECEIPT|CURRENT-MAIN VERIFIED|mail/i.test(slackTalk.note), "Slack SHIP_RECEIPT without SHA file must stay CLAIMED");
var slackDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nslack-receipt leftover landed"
);
assert.strictEqual(slackDone.state, "INTEGRATED", "completion words still beat Slack-receipt talk");
var slackEmpty = api.slackReceiptState({});
assert.strictEqual(slackEmpty.state, "UNMEASURED");
var slackMissing = api.slackReceiptState({
  measured: true,
  source_id: "demon-pixel-swarm-flight-recorder-landed-20260825-01",
  source_paths: ["swarm.html"],
  present_paths: [],
  receipt_present: false
});
assert.strictEqual(slackMissing.state, "NOT_LANDED");
var slackMail = api.slackReceiptState({
  measured: true,
  source_id: "demon-pixel-swarm-flight-recorder-landed-20260825-01",
  source_paths: ["swarm.html", "swarm.js"],
  present_paths: ["swarm.html", "swarm.js"],
  receipt_present: false
});
assert.strictEqual(slackMail.state, "CARRIER_ONLY");
assert.ok(/mail/i.test(slackMail.note), "sources without p/{id}.md must stay mail");
var slackOk = api.slackReceiptState({
  measured: true,
  source_id: "demon-pixel-swarm-flight-recorder-landed-20260825-01",
  source_paths: ["swarm.html"],
  present_paths: ["swarm.html"],
  receipt_present: true
});
assert.strictEqual(slackOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(slackOk.note), "landed leftover must name Slack as not the file");
assert.strictEqual(api.toneFor("CARRIER_ONLY"), "wait", "mail is unfinished ship, not a broken canary");
assert.ok(html.indexOf('id="slack-receipt-result"') >= 0, "desk must name the Slack-receipt leftover");
assert.ok(html.indexOf("host/slack_receipt.py") >= 0, "desk must name the Slack-receipt instrument");
assert.ok(html.indexOf("ground/SLACK_RECEIPT.md") >= 0, "desk must link the Slack-receipt card");
assert.ok(html.indexOf("ground/SLACK_RECEIPT.json") >= 0, "desk must link the Slack-receipt catalog");
assert.ok(html.indexOf("1787637937.023799") >= 0, "desk must cite the DEMON Slack SHIP_RECEIPT ts");
assert.ok(html.indexOf("demon-pixel-swarm-flight-recorder-landed-20260825-01") >= 0, "desk must name the DEMON receipt id");
assert.ok(/SHIP_RECEIPT|LANDED \+ CURRENT-MAIN VERIFIED|POST-PUSH CURRENT MAIN|flight-recorder-landed/i.test(html), "desk must name Slack SHIP_RECEIPT talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/SLACK_RECEIPT.md") >= 0, "Slack-receipt card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/SLACK_RECEIPT.json") >= 0, "Slack-receipt catalog must stay a canary");
assert.ok(api.isWatchdogHeadProofTalk, "land.js must classify SPECTER HEAD-proof canary talk");
assert.ok(api.watchdogHeadProofState, "land.js must classify the HEAD-proof leftover");
assert.ok(api.isWatchdogHeadProofTalk("SPECTER TAKING — first production wake_jobs HEAD-proof canary. Exact id: specter-watchdog-head-proof-20260825-01. completion_predicate=result_address_on_head pointing at p/ridge-cursor-wake-loop-20260822-01.md."), "SPECTER HEAD-proof taking is leftover talk");
assert.ok(!api.isWatchdogHeadProofTalk("make sure people do more than talk about shit"), "ship-talk is not the HEAD-proof leftover");
assert.ok(!api.isWatchdogHeadProofTalk("SPECTER TAKING — render-QA execution lane. I found no live render_check claim."), "render taking is not the HEAD-proof leftover");
assert.ok(!api.isWatchdogHeadProofTalk("SPECTER PIVOT — no render duplication. pivoting now to the adjacent MCP/wake real-job verification lane."), "MCP-wake pivot is not the HEAD-proof leftover");
assert.ok(!api.isMcpWakeJobTalk("SPECTER TAKING — first production wake_jobs HEAD-proof canary. specter-watchdog-head-proof-20260825-01."), "HEAD-proof taking is not the MCP-wake leftover");
assert.ok(!api.isWatchdogCanaryTalk("SPECTER TAKING — first production wake_jobs HEAD-proof canary. Exact id: specter-watchdog-head-proof-20260825-01. completion_predicate=result_address_on_head pointing at p/ridge-cursor-wake-loop-20260822-01.md."), "HEAD-proof taking is not the watchdog-canary leftover");
assert.ok(!api.isWatchdogHeadProofTalk("SPECTER INDEPENDENT SHIP RECEIPT — watchdog HEAD proof is integrated. The production oracle remains unutilized by a durable job canary. no real job JSON."), "watchdog-canary receipt is not the HEAD-proof leftover");
var headProofTalk = api.completionStateFromText(
  "SPECTER TAKING — first production wake_jobs HEAD-proof canary\nExact id: specter-watchdog-head-proof-20260825-01. JobStore.upsert, completion_predicate=result_address_on_head, p/ridge-cursor-wake-loop-20260822-01.md."
);
assert.strictEqual(headProofTalk.state, "CLAIMED");
assert.ok(/HEAD-proof|first-production-wake_jobs|result_address_on_head/i.test(headProofTalk.note), "HEAD-proof taking must beat render-contract SPECTER TAKING match");
var headProofDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nwatchdog-head-proof leftover landed"
);
assert.strictEqual(headProofDone.state, "INTEGRATED", "completion words still beat HEAD-proof talk");
var headProofEmpty = api.watchdogHeadProofState("");
assert.strictEqual(headProofEmpty.state, "UNMEASURED");
var headProofMissing = api.watchdogHeadProofState("# empty stub\nno census");
assert.strictEqual(headProofMissing.state, "NOT_LANDED");
var headProofOk = api.watchdogHeadProofState("def measure_root(root):\n    return root\ndef classify(row):\n    return row\nJobStore\nupsert\nresult_address_on_head\nspecter-watchdog-head-proof-20260825-01\nridge-cursor-wake-loop-20260822-01\n");
assert.strictEqual(headProofOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(headProofOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="watchdog-head-proof-result"') >= 0, "desk must name the HEAD-proof leftover");
assert.ok(html.indexOf("host/watchdog_head_proof.py") >= 0, "desk must name the HEAD-proof instrument");
assert.ok(html.indexOf("ground/WATCHDOG_HEAD_PROOF.md") >= 0, "desk must link the HEAD-proof card");
assert.ok(html.indexOf("ground/WATCHDOG_HEAD_PROOF.json") >= 0, "desk must link the HEAD-proof catalog");
assert.ok(html.indexOf("1787639783.177559") >= 0, "desk must cite the SPECTER HEAD-proof Slack ts");
assert.ok(html.indexOf("specter-watchdog-head-proof-20260825-01") >= 0, "desk must name the canonical job id");
assert.ok(/HEAD-proof|first-production-wake_jobs|result_address_on_head/i.test(html), "desk must name SPECTER HEAD-proof talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/WATCHDOG_HEAD_PROOF.md") >= 0, "HEAD-proof card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/WATCHDOG_HEAD_PROOF.json") >= 0, "HEAD-proof catalog must stay a canary");
assert.ok(api.isMcpWakeJobTalk, "land.js must classify SPECTER pivot / MCP-wake real-job talk");
assert.ok(api.mcpWakeJobState, "land.js must classify the MCP/wake real-job leftover");
assert.ok(api.isMcpWakeJobTalk("SPECTER PIVOT — no render duplication. pivoting now to the adjacent MCP/wake real-job verification lane."), "SPECTER pivot is MCP-wake real-job talk");
assert.ok(!api.isMcpWakeJobTalk("make sure people do more than talk about shit"), "ship-talk is not the MCP-wake leftover");
assert.ok(!api.isMcpWakeJobTalk("SPECTER TAKING — render-QA execution lane. I found no live render_check claim."), "render taking is not the MCP-wake leftover");
assert.ok(!api.isMcpWakeJobTalk("MACHINE-ONLY WORKING BUILDS — rook-resident-native keyb01.mno TRAIN_CIRCUITS_FROM_FILE"), "working-builds copy is not the MCP-wake leftover");
assert.ok(!api.isMcpWakeJobTalk("LIVE COMPUTE/CONNECTOR BOARD — USE THESE, DO NOT COUNT CACHE AS CAPACITY"), "resource-ledger copy is not the MCP-wake leftover");
assert.ok(!api.isResourceLedgerTalk("SPECTER PIVOT — no render duplication. MCP/wake real-job verification."), "pivot is not the resource-ledger leftover");
assert.ok(!api.isWorkingBuildTalk("SPECTER PIVOT — no render duplication. MCP/wake real-job verification."), "pivot is not the working-builds leftover");
assert.ok(!api.isRenderContractTalk("SPECTER PIVOT — no render duplication. MCP/wake real-job verification."), "pivot is not the old workflow-contract leftover");
var wakeTalk = api.completionStateFromText(
  "SPECTER PIVOT — no render duplication. pivoting now to the adjacent MCP/wake real-job verification lane. I will not touch JOJO’s worktree."
);
assert.strictEqual(wakeTalk.state, "CLAIMED");
assert.ok(/SPECTER pivot|MCP-wake real-job|no-render-duplication/i.test(wakeTalk.note), "SPECTER-pivot-without-SHA must stay CLAIMED and beat render-check");
var wakeDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nmcp-wake-job leftover landed"
);
assert.strictEqual(wakeDone.state, "INTEGRATED", "completion words still beat MCP-wake talk");
var wakeEmpty = api.mcpWakeJobState("");
assert.strictEqual(wakeEmpty.state, "UNMEASURED");
var wakeMissing = api.mcpWakeJobState("# empty stub\nno census");
assert.strictEqual(wakeMissing.state, "NOT_LANDED");
var wakeOk = api.mcpWakeJobState("def measure_root(root):\n    return root\ndef classify(row):\n    return row\nresult_address_on_head\nTemporaryDirectory\nnever write wake_jobs/\nNOT_DURABLE\ninvoke_model\n");
assert.strictEqual(wakeOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(wakeOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="mcp-wake-job-result"') >= 0, "desk must name the MCP-wake leftover");
assert.ok(html.indexOf("host/mcp_wake_job.py") >= 0, "desk must name the MCP-wake instrument");
assert.ok(html.indexOf("ground/MCP_WAKE_JOB.md") >= 0, "desk must link the MCP-wake card");
assert.ok(html.indexOf("ground/MCP_WAKE_JOB.json") >= 0, "desk must link the MCP-wake catalog");
assert.ok(html.indexOf("1787637971.910749") >= 0, "desk must cite the SPECTER pivot Slack ts");
assert.ok(/SPECTER pivot|MCP-wake real-job|no-render-duplication|real-job-verification/i.test(html), "desk must name SPECTER pivot talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/MCP_WAKE_JOB.md") >= 0, "MCP-wake card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/MCP_WAKE_JOB.json") >= 0, "MCP-wake catalog must stay a canary");
assert.ok(!api.isMcpWakeJobTalk("DEMON PIXEL SWARM FLIGHT RECORDER — LANDED + CURRENT-MAIN VERIFIED. POST-PUSH CURRENT MAIN."), "Slack receipt copy is not the MCP-wake leftover");
assert.ok(!api.isSlackReceiptTalk("SPECTER PIVOT — no render duplication. MCP/wake real-job verification."), "pivot is not the Slack-receipt leftover");
assert.ok(api.isFinderZeroTalk, "land.js must classify finder-zero / false-zero talk");
assert.ok(api.finderZeroState, "land.js must classify the finder-zero leftover");
assert.ok(api.isFinderZeroTalk("OWNER ORDER — audit every zero before acting on it; the collision-check road prints false zeros. FINDER UNVERIFIED, never 0. known-present calibration."), "finder-zero copy is talk");
assert.ok(!api.isFinderZeroTalk("make sure people do more than talk about shit"), "ship-talk is not the finder-zero leftover");
assert.ok(!api.isFinderZeroTalk("MACHINE-ONLY WORKING BUILDS — rook-resident-native keyb01.mno TRAIN_CIRCUITS_FROM_FILE"), "working-builds copy is not finder-zero leftover");
assert.ok(!api.isWorkingBuildTalk("OWNER ORDER — audit every zero. collision-check road prints false zeros. FINDER UNVERIFIED."), "finder-zero copy is not working-builds leftover");
assert.ok(!api.isHostZeroTalk("OWNER ORDER — audit every zero. collision-check road prints false zeros. FINDER UNVERIFIED."), "finder-zero copy is not host-zero leftover");
var finderTalk = api.completionStateFromText(
  "OWNER ORDER — audit every zero before acting on it; the collision-check road prints false zeros. FINDER UNVERIFIED. known-present calibration."
);
assert.strictEqual(finderTalk.state, "CLAIMED");
assert.ok(/finder-zero|false-zero|FINDER UNVERIFIED|collision-check/i.test(finderTalk.note), "finder-zero-without-SHA must stay CLAIMED");
var finderDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nfinder-zero leftover landed"
);
assert.strictEqual(finderDone.state, "INTEGRATED", "completion words still beat finder-zero talk");
var finderEmpty = api.finderZeroState("");
assert.strictEqual(finderEmpty.state, "UNMEASURED");
var finderMissing = api.finderZeroState("# empty stub\nno miss branch");
assert.strictEqual(finderMissing.state, "NOT_LANDED");
var finderOk = api.finderZeroState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\ndef search_space():\n    return {}\ndef calibrate():\n    return {}\nFINDER UNVERIFIED\nnever 0\nsearch-only zero is not clearance\n");
assert.strictEqual(finderOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(finderOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="finder-zero-result"') >= 0, "desk must name the finder-zero leftover");
assert.ok(html.indexOf("host/finder_zero.py") >= 0, "desk must name the finder-zero instrument");
assert.ok(html.indexOf("ground/FINDER_ZERO.md") >= 0, "desk must link the finder-zero card");
assert.ok(html.indexOf("ground/FINDER_ZERO.json") >= 0, "desk must link the finder-zero catalog");
assert.ok(html.indexOf("1787638031.533189") >= 0, "desk must cite the finder-zero Slack ts");
assert.ok(/FINDER UNVERIFIED|collision-check|false zeros|audit every zero/i.test(html), "desk must name finder-zero talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/FINDER_ZERO.md") >= 0, "finder-zero card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/FINDER_ZERO.json") >= 0, "finder-zero catalog must stay a canary");
assert.ok(!api.isFinderZeroTalk("DEMON PIXEL SWARM FLIGHT RECORDER — LANDED + CURRENT-MAIN VERIFIED. POST-PUSH CURRENT MAIN."), "Slack receipt copy is not finder-zero leftover");
assert.ok(!api.isSlackReceiptTalk("OWNER ORDER — audit every zero. collision-check road prints false zeros. FINDER UNVERIFIED."), "finder-zero copy is not Slack-receipt leftover");
assert.ok(!api.isFinderZeroTalk("SPECTER PIVOT — no render duplication. MCP/wake real-job verification."), "pivot is not finder-zero leftover");
assert.ok(!api.isMcpWakeJobTalk("OWNER ORDER — audit every zero. collision-check road prints false zeros. FINDER UNVERIFIED."), "finder-zero copy is not the MCP-wake leftover");
assert.ok(api.isImpactLedgerTalk, "land.js must classify P0 containment / TRACE CONSUMERS talk");
assert.ok(api.impactLedgerState, "land.js must classify the impact-ledger leftover");
assert.ok(api.isImpactLedgerTalk("OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED, never 0."), "containment copy is talk");
assert.ok(!api.isImpactLedgerTalk("make sure people do more than talk about shit"), "ship-talk is not the impact-ledger leftover");
assert.ok(!api.isImpactLedgerTalk("OWNER ORDER — audit every zero before acting on it; the collision-check road prints false zeros. FINDER UNVERIFIED. known-present calibration."), "finder-zero copy is not the impact-ledger leftover");
assert.ok(!api.isFinderZeroTalk("OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED."), "containment is not the finder-zero leftover");
assert.ok(!api.isImpactLedgerTalk("SPECTER PIVOT — no render duplication. MCP/wake real-job verification."), "pivot is not the impact-ledger leftover");
assert.ok(!api.isImpactLedgerTalk("MACHINE-ONLY WORKING BUILDS — rook-resident-native keyb01.mno TRAIN_CIRCUITS_FROM_FILE"), "working-builds copy is not the impact-ledger leftover");
assert.ok(!api.isMcpWakeJobTalk("OWNER P0 CONTAINMENT ALERT: TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED."), "containment is not the MCP-wake leftover");
assert.ok(!api.isShipTalk("OWNER P0 CONTAINMENT ALERT: TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED."), "containment is not generic ship-talk");
assert.ok(!api.isClaudeTesterTalk("OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED."), "containment is not the Claude-tester leftover");
assert.ok(!api.isImpactLedgerTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. Do not assign Claude models test. tester/verifier lanes. uncalibrated green result does not count."), "Claude-tester copy is not the impact-ledger leftover");
assert.ok(!api.isTripleAppendTalk("OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED."), "containment is not the triple-append leftover");
assert.ok(!api.isImpactLedgerTalk("P0_UTILIZATION_INCIDENT — three byte-identical appends. pause further append mutations."), "triple-append copy is not the impact-ledger leftover");
var impactTalk = api.completionStateFromText(
  "OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED."
);
assert.strictEqual(impactTalk.state, "CLAIMED");
assert.ok(/P0 containment|TRACE CONSUMERS|Claude-cannot-certify|FINDER-FAILED/i.test(impactTalk.note), "containment-without-SHA must stay CLAIMED");
var impactDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nimpact-ledger leftover landed"
);
assert.strictEqual(impactDone.state, "INTEGRATED", "completion words still beat impact-ledger talk");
var impactEmpty = api.impactLedgerState("");
assert.strictEqual(impactEmpty.state, "UNMEASURED");
var impactMissing = api.impactLedgerState("# empty stub\nno census");
assert.strictEqual(impactMissing.state, "NOT_LANDED");
var impactOk = api.impactLedgerState("def measure_from_rows(facts):\n    return facts\ndef measure_tree(root):\n    return root\ndef classify(row):\n    return row\ndef search_space():\n    return {}\ndef calibrate():\n    return {}\nFINDER-FAILED\nnever 0\nTRACE CONSUMERS\nQUARANTINED\n");
assert.strictEqual(impactOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(impactOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="impact-ledger-result"') >= 0, "desk must name the impact-ledger leftover");
assert.ok(html.indexOf("host/impact_ledger.py") >= 0, "desk must name the impact-ledger instrument");
assert.ok(html.indexOf("ground/IMPACT_LEDGER.md") >= 0, "desk must link the impact-ledger card");
assert.ok(html.indexOf("ground/IMPACT_LEDGER.json") >= 0, "desk must link the impact-ledger catalog");
assert.ok(html.indexOf("1787638509.277739") >= 0, "desk must cite the P0 containment Slack ts");
assert.ok(/P0 CONTAINMENT|TRACE CONSUMERS|FINDER-FAILED|Claude cannot certify/i.test(html), "desk must name containment talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/IMPACT_LEDGER.md") >= 0, "impact-ledger card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/IMPACT_LEDGER.json") >= 0, "impact-ledger catalog must stay a canary");
assert.ok(!api.isImpactLedgerTalk("DEMON PIXEL SWARM FLIGHT RECORDER — LANDED + CURRENT-MAIN VERIFIED. POST-PUSH CURRENT MAIN."), "Slack receipt copy is not the impact-ledger leftover");
assert.ok(api.isGrokRecoveryTalk, "land.js must classify grok-recovery / muhlnickel-subagent talk");
assert.ok(api.grokRecoveryState, "land.js must classify the grok-recovery leftover");
assert.ok(api.isGrokRecoveryTalk("from: JOJO\nid: jojo-grok-recovery-muhlnickel-subagent-contract-20260825-01\nsubject: GROK RECOVERY + MUHLNICKEL-ONLY LOCAL-MODEL SUBAGENT CONTRACT\nNO host model inference. prompt-address → receiver pulse → result-register. discovery 01a0373e. 50_cross_synthesis.txt. no-host-inference/no-Titan-mutation."), "JOJO grok-recovery taking is talk");
assert.ok(!api.isGrokRecoveryTalk("make sure people do more than talk about shit"), "ship-talk is not the grok-recovery leftover");
assert.ok(!api.isGrokRecoveryTalk("Revenue/substrate fleet live — Grok 4.6 workflows + Claude verifier"), "fleet talk is not the grok-recovery leftover");
assert.ok(!api.isGrokRecoveryTalk("GROK HARNESS GAP (verified read-only): ~/.grok reports 0 MCP servers, 0 LSP servers"), "harness-gap copy is not the grok-recovery leftover");
assert.ok(!api.isFleetTalk("GROK RECOVERY + MUHLNICKEL-ONLY LOCAL-MODEL SUBAGENT CONTRACT. prompt-address. 01a0373e. 50_cross_synthesis.txt."), "grok-recovery copy is not the fleet leftover");
assert.ok(!api.isGrokHarnessTalk("GROK RECOVERY + MUHLNICKEL-ONLY. prompt-address. 01a0373e. 50_cross_synthesis.txt."), "grok-recovery copy is not the harness leftover");
assert.ok(!api.isGrokRecoveryTalk("X-Y-Z ZERO AUDIT required on EVERY test and EVERY result. FINDER-UNVERIFIED + known-present calibration."), "xyz-zero copy is not the grok-recovery leftover");
assert.ok(!api.isGrokRecoveryTalk("measurement abuse, not just measurement error. unflattering truths. damage-control addendum."), "measure-abuse copy is not the grok-recovery leftover");
assert.ok(!api.isGrokRecoveryTalk("CONTAINMENT_COMPLIANCE. Affected artifacts from this seat. 7-term space-separated. planted-deletion canary."), "remeasure copy is not the grok-recovery leftover");
var grokRecTalk = api.completionStateFromText(
  "from: JOJO\nid: jojo-grok-recovery-muhlnickel-subagent-contract-20260825-01\nGROK RECOVERY + MUHLNICKEL-ONLY LOCAL-MODEL SUBAGENT CONTRACT\nprompt-address → receiver pulse → result-register\n01a0373e 50_cross_synthesis.txt\nFINDER-UNVERIFIED known-present calibration"
);
assert.strictEqual(grokRecTalk.state, "CLAIMED");
assert.ok(/grok-recovery|muhlnickel-only|prompt-address/i.test(grokRecTalk.note), "grok-recovery-without-SHA must stay CLAIMED and beat finder-zero");
var grokRecDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ngrok-recovery leftover landed"
);
assert.strictEqual(grokRecDone.state, "INTEGRATED", "completion words still beat grok-recovery talk");
var grokRecEmpty = api.grokRecoveryState("");
assert.strictEqual(grokRecEmpty.state, "UNMEASURED");
var grokRecMissing = api.grokRecoveryState("# empty stub\nno leftover");
assert.strictEqual(grokRecMissing.state, "NOT_LANDED");
var grokRecOk = api.grokRecoveryState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER UNVERIFIED\nnever 0\ndests FROM FILE\nno_host_inference\nno_titan_mutation\n01a0373e\n50_cross_synthesis\nknown-present calibration\n");
assert.strictEqual(grokRecOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(grokRecOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="grok-recovery-result"') >= 0, "desk must name the grok-recovery leftover");
assert.ok(html.indexOf("host/grok_recovery.py") >= 0, "desk must name the grok-recovery instrument");
assert.ok(html.indexOf("ground/GROK_RECOVERY.md") >= 0, "desk must link the grok-recovery card");
assert.ok(html.indexOf("ground/GROK_RECOVERY.json") >= 0, "desk must link the grok-recovery catalog");
assert.ok(html.indexOf("1787638974.401269") >= 0, "desk must cite the JOJO grok-recovery Slack ts");
assert.ok(/grok-recovery|muhlnickel-only|prompt-address|01a0373e|50_cross_synthesis/i.test(html), "desk must name grok-recovery talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/GROK_RECOVERY.md") >= 0, "grok-recovery card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/GROK_RECOVERY.json") >= 0, "grok-recovery catalog must stay a canary");
assert.ok(api.isClaudeZeroDamageTalk, "land.js must classify Claude-zero damage-control talk");
assert.ok(api.claudeZeroDamageState, "land.js must classify the claude-zero-damage leftover");
assert.ok(api.isClaudeZeroDamageTalk("DEMON TAKING — CLAUDE ZERO DAMAGE-CONTROL DURABLE LEDGER. stale KEYB or absence-derived Titan/KITE dispositions. rhetorical consumers of Claude false zeros."), "DEMON damage-control taking is talk");
assert.ok(!api.isClaudeZeroDamageTalk("make sure people do more than talk about shit"), "ship-talk is not the damage-control leftover");
assert.ok(!api.isClaudeZeroDamageTalk("OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED, never 0."), "containment is not the damage-control leftover");
assert.ok(!api.isClaudeZeroDamageTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. tester/verifier lanes. uncalibrated green result does not count."), "Claude-tester copy is not the damage-control leftover");
assert.ok(!api.isClaudeZeroDamageTalk("MACHINE-ONLY WORKING BUILDS — rook-resident-native keyb01.mno TRAIN_CIRCUITS_FROM_FILE"), "working-builds copy is not the damage-control leftover");
assert.ok(!api.isClaudeZeroDamageTalk("MUHL_KEYB MANIFEST IS STALE — DO NOT INTEGRATE AS VERIFIED. keyb01.manifest.json size agrees, bytes do not."), "stale-manifest copy is not the damage-control leftover");
assert.ok(!api.isWorkingBuildTalk("CLAUDE ZERO DAMAGE-CONTROL DURABLE LEDGER. stale KEYB or absence-derived Titan/KITE."), "damage-control copy is not working-builds leftover");
assert.ok(!api.isClaudeTesterTalk("CLAUDE ZERO DAMAGE-CONTROL DURABLE LEDGER. stale KEYB or absence-derived Titan/KITE."), "damage-control copy is not the Claude-tester leftover");
assert.ok(!api.isImpactLedgerTalk("CLAUDE ZERO DAMAGE-CONTROL DURABLE LEDGER. stale KEYB or absence-derived Titan/KITE. rhetorical consumers of Claude."), "damage-control copy without P0 phrases is not impact-ledger leftover");
var damageTalk = api.completionStateFromText(
  "DEMON TAKING — CLAUDE ZERO DAMAGE-CONTROL DURABLE LEDGER. stale KEYB or absence-derived Titan/KITE. rhetorical consumers of Claude false zeros. FINDER-FAILED."
);
assert.strictEqual(damageTalk.state, "CLAIMED");
assert.ok(/damage-control|absence-derived|stale KEYB/i.test(damageTalk.note), "damage-control-without-SHA must stay CLAIMED and beat impact-ledger");
var damageDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nclaude-zero-damage leftover landed"
);
assert.strictEqual(damageDone.state, "INTEGRATED", "completion words still beat damage-control talk");
var damageEmpty = api.claudeZeroDamageState("");
assert.strictEqual(damageEmpty.state, "UNMEASURED");
var damageMissing = api.claudeZeroDamageState("# empty stub\nno census");
assert.strictEqual(damageMissing.state, "NOT_LANDED");
var damageOk = api.claudeZeroDamageState("def measure_from_rows(facts):\n    return facts\ndef measure_tree(root):\n    return root\ndef classify(row):\n    return row\ndef search_space():\n    return {}\ndef calibrate():\n    return {}\nFINDER-FAILED\nnever 0\nUNRECONCILED\nSTALE\npreserve_originals\n");
assert.strictEqual(damageOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(damageOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="claude-zero-damage-result"') >= 0, "desk must name the damage-control leftover");
assert.ok(html.indexOf("host/claude_zero_damage.py") >= 0, "desk must name the damage-control instrument");
assert.ok(html.indexOf("ground/CLAUDE_ZERO_DAMAGE.md") >= 0, "desk must link the damage-control card");
assert.ok(html.indexOf("ground/CLAUDE_ZERO_DAMAGE.json") >= 0, "desk must link the damage-control catalog");
assert.ok(html.indexOf("1787639239.069069") >= 0, "desk must cite the DEMON damage-control Slack ts");
assert.ok(/damage-control|absence-derived|stale KEYB/i.test(html), "desk must name damage-control talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_ZERO_DAMAGE.md") >= 0, "damage-control card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_ZERO_DAMAGE.json") >= 0, "damage-control catalog must stay a canary");
assert.ok(!api.isClaudeZeroDamageTalk("DEMON PIXEL SWARM FLIGHT RECORDER — LANDED + CURRENT-MAIN VERIFIED. POST-PUSH CURRENT MAIN."), "Slack receipt copy is not the damage-control leftover");
assert.ok(!api.isShipTalk("CLAUDE ZERO DAMAGE-CONTROL DURABLE LEDGER. stale KEYB or absence-derived Titan/KITE."), "damage-control is not generic ship-talk");
assert.ok(!api.isClaudeZeroTalk("CLAUDE ZERO DAMAGE-CONTROL DURABLE LEDGER. stale KEYB or absence-derived Titan/KITE."), "damage-control copy is not the Claude-zero leftover");
assert.ok(!api.isMeasureAbuseTalk("CLAUDE ZERO DAMAGE-CONTROL DURABLE LEDGER. stale KEYB or absence-derived Titan/KITE."), "damage-control copy is not the measure-abuse leftover");
assert.ok(!api.isClaudeZeroDamageTalk("every zero reported by Claude was wrong. RETRACT, DO NOT DOWNGRADE. Claude-reported zeros."), "Claude-zero copy is not the damage-control leftover");
assert.ok(!api.isClaudeZeroDamageTalk("measurement abuse, not just measurement error. unflattering truths. damage-control addendum."), "measure-abuse copy is not the damage-control leftover");
assert.ok(api.isStaleManifestTalk, "land.js must classify KEYB stale-manifest talk");
assert.ok(api.staleManifestState, "land.js must classify the stale-manifest leftover");
assert.ok(api.isStaleManifestTalk("MUHL_KEYB MANIFEST IS STALE — DO NOT INTEGRATE AS VERIFIED. keyb01.manifest.json claims a63396. size agrees, bytes do not. do not land, wire, execute, or describe this container as manifest-verified. post-manifest mutation. cca2b762. stale/out-of-spec."), "KEYB stale-manifest correction is talk");
assert.ok(!api.isStaleManifestTalk("make sure people do more than talk about shit"), "ship-talk is not the stale-manifest leftover");
assert.ok(!api.isStaleManifestTalk("MACHINE-ONLY WORKING BUILDS — CLAIM PROVENANCE-FIRST INTEGRATION. rook-resident-native TRAIN_CIRCUITS_FROM_FILE. Do not upload model/container bytes."), "working-builds copy is not stale-manifest leftover");
assert.ok(!api.isStaleSpecTalk("MUHL_KEYB MANIFEST IS STALE — keyb01.manifest.json size agrees, bytes do not. manifest-verified."), "KEYB stale-manifest copy is not stale-spec leftover");
assert.ok(!api.isTripleAppendTalk("MUHL_KEYB MANIFEST IS STALE — keyb01.manifest.json size agrees, bytes do not. manifest-verified."), "KEYB stale-manifest copy is not triple-append leftover");
var staleManTalk = api.completionStateFromText(
  "MUHL_KEYB MANIFEST IS STALE — DO NOT INTEGRATE AS VERIFIED. keyb01.manifest.json claims 430860 a63396. size agrees, bytes do not. do not land, wire, execute. manifest-verified. post-manifest mutation. cca2b762."
);
assert.strictEqual(staleManTalk.state, "CLAIMED");
assert.ok(/stale-manifest|size-agrees-bytes-do-not|manifest-verified/i.test(staleManTalk.note), "KEYB stale-manifest-without-SHA must stay CLAIMED");
var staleManDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nstale-manifest leftover landed"
);
assert.strictEqual(staleManDone.state, "INTEGRATED", "completion words still beat stale-manifest talk");
var staleManEmpty = api.staleManifestState("");
assert.strictEqual(staleManEmpty.state, "UNMEASURED");
var staleManMissing = api.staleManifestState("# empty stub\nno mismatch");
assert.strictEqual(staleManMissing.state, "NOT_LANDED");
var staleManOk = api.staleManifestState("def measure_from_parts(manifest_text, catalog_text):\n    claimed_sha256 = ''\n    cited_sha256 = ''\n    size_agrees = True\ndef classify(row):\n    return row\nrefuse_verified = True\ndo not describe as manifest-verified\nrefuse_rewrite = True\ndo not rewrite the original manifest\n");
assert.strictEqual(staleManOk.state, "INTEGRATED");
assert.ok(/NOT_VERIFIED/i.test(staleManOk.note), "landed leftover must name KEYB NOT_VERIFIED");
assert.ok(html.indexOf('id="stale-manifest-result"') >= 0, "desk must name the stale-manifest leftover");
assert.ok(html.indexOf("host/stale_manifest.py") >= 0, "desk must name the stale-manifest instrument");
assert.ok(html.indexOf("ground/STALE_MANIFEST.md") >= 0, "desk must link the stale-manifest card");
assert.ok(html.indexOf("ground/STALE_MANIFEST.json") >= 0, "desk must link the stale-manifest catalog");
assert.ok(html.indexOf("1787638201.498979") >= 0, "desk must cite the DEMON KEYB correction Slack ts");
assert.ok(/size-agrees-bytes-do-not|do-not-integrate-as-verified|manifest-verified|post-manifest-mutation/i.test(html), "desk must name stale-manifest talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/STALE_MANIFEST.md") >= 0, "stale-manifest card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/STALE_MANIFEST.json") >= 0, "stale-manifest catalog must stay a canary");
assert.ok(api.isClaudeTesterTalk, "land.js must classify stop-using-Claude-testers talk");
assert.ok(api.claudeTesterState, "land.js must classify the Claude-tester leftover");
assert.ok(api.isClaudeTesterTalk("from: DEMON\nkind: OWNER_RULE_RELAY\nsubject: STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS — EFFECTIVE NOW\nDirect owner rule: stop using Claudes to test.\nDo not assign Claude models test, verification, red-team-as-verdict.\nPause/retire active Claude tester/verifier lanes.\nSearch-zero testing is instrument failure, not absence proof.\nA bare zero or uncalibrated green result does not count."), "DEMON OWNER_RULE_RELAY is talk");
assert.ok(!api.isClaudeTesterTalk("make sure people do more than talk about shit"), "ship-talk is not the Claude-tester leftover");
assert.ok(!api.isClaudeTesterTalk("DEMON PIXEL SWARM FLIGHT RECORDER — LANDED + CURRENT-MAIN VERIFIED. POST-PUSH CURRENT MAIN."), "Slack receipt copy is not the Claude-tester leftover");
assert.ok(!api.isSlackReceiptTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS — EFFECTIVE NOW. tester/verifier lanes."), "Claude-tester copy is not the Slack-receipt leftover");
assert.ok(!api.isFleetTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. tester/verifier lanes. Search-zero testing is instrument failure."), "Claude-tester copy is not the fleet leftover");
assert.ok(!api.isFinderZeroTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. tester/verifier lanes. Search-zero testing is instrument failure."), "Claude-tester copy without GAUGE phrases is not finder-zero leftover");
assert.ok(!api.isTripleAppendTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. tester/verifier lanes."), "Claude-tester copy is not triple-append leftover");
var claudeTalk = api.completionStateFromText(
  "STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS — EFFECTIVE NOW\nDirect owner rule: stop using Claudes to test. tester/verifier lanes. known-present calibration."
);
assert.strictEqual(claudeTalk.state, "CLAIMED");
assert.ok(/stop-using-Claude-testers|OWNER_RULE_RELAY/i.test(claudeTalk.note), "Claude-tester-without-SHA must stay CLAIMED and beat finder-zero");
var claudeDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nclaude-tester leftover landed"
);
assert.strictEqual(claudeDone.state, "INTEGRATED", "completion words still beat Claude-tester talk");
var claudeEmpty = api.claudeTesterState("");
assert.strictEqual(claudeEmpty.state, "UNMEASURED");
var claudeMissing = api.claudeTesterState("# empty stub\nno leftover");
assert.strictEqual(claudeMissing.state, "NOT_LANDED");
var claudeOk = api.claudeTesterState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nxyz required\nknown-present calibration\npreserve artifacts\ndoes not erase Claude-authored build artifacts\ndeterministic local checks\nGitHub Actions\nCodex\n");
assert.strictEqual(claudeOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(claudeOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="claude-tester-result"') >= 0, "desk must name the Claude-tester leftover");
assert.ok(html.indexOf("host/claude_tester.py") >= 0, "desk must name the Claude-tester instrument");
assert.ok(html.indexOf("ground/CLAUDE_TESTER.md") >= 0, "desk must link the Claude-tester card");
assert.ok(html.indexOf("ground/CLAUDE_TESTER.json") >= 0, "desk must link the Claude-tester catalog");
assert.ok(html.indexOf("1787638370.166649") >= 0, "desk must cite the DEMON OWNER_RULE_RELAY Slack ts");
assert.ok(/stop using claude|tester\/verifier|search-zero|uncalibrated-green/i.test(html), "desk must name Claude-tester talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_TESTER.md") >= 0, "Claude-tester card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_TESTER.json") >= 0, "Claude-tester catalog must stay a canary");
assert.ok(api.isMeasureAbuseTalk, "land.js must classify measurement-abuse / unflattering-truths talk");
assert.ok(api.measureAbuseState, "land.js must classify the measure-abuse leftover");
assert.ok(api.isMeasureAbuseTalk("P0 DAMAGE-CONTROL ADDENDUM — measurement abuse, not just measurement error\nOwner reports that Claude’s false-zero outputs were presented back to him as “unflattering truths” he had to confront.\nDo not use disputed measurements to characterize, diagnose, pathologize, shame, or overrule the reporter.\nTreat every Claude-produced zero as RETRACTED, not “unflattering truth.”"), "DEMON damage-control addendum is talk");
assert.ok(!api.isMeasureAbuseTalk("make sure people do more than talk about shit"), "ship-talk is not the measure-abuse leftover");
assert.ok(!api.isMeasureAbuseTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. tester/verifier lanes. Search-zero testing is instrument failure."), "Claude-tester copy is not measure-abuse leftover");
assert.ok(!api.isMeasureAbuseTalk("OWNER ORDER — audit every zero before acting on it; the collision-check road prints false zeros. FINDER UNVERIFIED, never 0."), "finder-zero copy without abuse phrases is not measure-abuse leftover");
assert.ok(!api.isMeasureAbuseTalk("OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED, never 0."), "impact-ledger copy is not measure-abuse leftover");
assert.ok(!api.isMeasureAbuseTalk("X-Y-Z ZERO AUDIT required on EVERY test and EVERY result. FINDER-UNVERIFIED + known-present calibration."), "xyz-zero copy is not measure-abuse leftover");
assert.ok(!api.isFinderZeroTalk("P0 DAMAGE-CONTROL ADDENDUM — measurement abuse, not just measurement error. unflattering truths. pathologize. retracted, not."), "measure-abuse copy without GAUGE phrases is not finder-zero leftover");
assert.ok(!api.isClaudeTesterTalk("P0 DAMAGE-CONTROL ADDENDUM — measurement abuse, not just measurement error. unflattering truths. pathologize."), "measure-abuse copy is not the Claude-tester leftover");
assert.ok(!api.isImpactLedgerTalk("P0 DAMAGE-CONTROL ADDENDUM — measurement abuse, not just measurement error. unflattering truths. pathologize. retracted, not."), "measure-abuse copy is not the impact-ledger leftover");
assert.ok(!api.isXyzZeroTalk("P0 DAMAGE-CONTROL ADDENDUM — measurement abuse, not just measurement error. unflattering truths. pathologize."), "measure-abuse copy is not the xyz-zero leftover");
assert.ok(!api.isMeasureAbuseTalk("DEMON P0_UTILIZATION_INCIDENT. triple-append / byte-identical-appends / pause-further-append."), "titan-append-guard copy is not measure-abuse leftover");
var abuseTalk = api.completionStateFromText(
  "P0 DAMAGE-CONTROL ADDENDUM — measurement abuse, not just measurement error\nunflattering truths. pathologize. retracted, not. known-present calibration."
);
assert.strictEqual(abuseTalk.state, "CLAIMED");
assert.ok(/measurement-abuse|unflattering-truths|damage-control-addendum/i.test(abuseTalk.note), "measure-abuse-without-SHA must stay CLAIMED and beat finder-zero");
var abuseDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nmeasure-abuse leftover landed"
);
assert.strictEqual(abuseDone.state, "INTEGRATED", "completion words still beat measure-abuse talk");
var abuseEmpty = api.measureAbuseState("");
assert.strictEqual(abuseEmpty.state, "UNMEASURED");
var abuseMissing = api.measureAbuseState("# empty stub\nno leftover");
assert.strictEqual(abuseMissing.state, "NOT_LANDED");
var abuseOk = api.measureAbuseState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nRETRACTED\nunflattering truths\nFINDER-FAILED\nNever 0\nCursor / Grok\npathologize\ndo not use a disputed measurement\n");
assert.strictEqual(abuseOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(abuseOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="measure-abuse-result"') >= 0, "desk must name the measure-abuse leftover");
assert.ok(html.indexOf("host/measure_abuse.py") >= 0, "desk must name the measure-abuse instrument");
assert.ok(html.indexOf("ground/MEASURE_ABUSE.md") >= 0, "desk must link the measure-abuse card");
assert.ok(html.indexOf("ground/MEASURE_ABUSE.json") >= 0, "desk must link the measure-abuse catalog");
assert.ok(html.indexOf("1787638952.362959") >= 0, "desk must cite the DEMON damage-control Slack ts");
assert.ok(/measurement abuse|unflattering-truths|damage-control-addendum|pathologize|retracted-not/i.test(html), "desk must name measure-abuse talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/MEASURE_ABUSE.md") >= 0, "measure-abuse card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/MEASURE_ABUSE.json") >= 0, "measure-abuse catalog must stay a canary");
assert.ok(api.isSuperGrokHeavyTalk, "land.js must classify SuperGrok Heavy leftover talk");
assert.ok(api.superGrokHeavyState, "land.js must classify the SuperGrok Heavy leftover");
assert.ok(api.isSuperGrokHeavyTalk("DEMON — SUPERGROK HEAVY RESET SPRINT / CORRECTION\nOwner correction confirmed by current xAI docs: SuperGrok paid usage is one shared weekly pool across Chat, Build, API, Imagine, and Voice. Grok Build is not a separate unavailable bucket. Do not use Cursor Grok as the substitute. utilization receipts. 1787645797.029719"), "DEMON SuperGrok Heavy Slack is leftover talk");
assert.ok(!api.isSuperGrokHeavyTalk("make sure people do more than talk about shit"), "generic ship-talk is not the SuperGrok Heavy leftover");
assert.ok(!api.isSuperGrokHeavyTalk("SPECTER FINAL — INTEGRATED / VERIFIED ON CURRENT MAIN `bef4ba712`. 1787645274.177269"), "SPECTER FINAL copy is not the SuperGrok Heavy leftover");
assert.ok(!api.isSuperGrokHeavyTalk("frontend-design and then mcp-tunnels still enabled after compat.claude cells"), "grok-hygiene copy is not the SuperGrok Heavy leftover");
assert.ok(!api.isSuperGrokHeavyTalk("72-JUROR CASH-NOW ROOM — FIRST COLLECTABLE USD"), "cash-now copy is not the SuperGrok Heavy leftover");
assert.ok(!api.isSuperGrokHeavyTalk("from: JOJO\nkind: COLLISION_RESOLVED\nid: jojo-device-queue-collapse-20260825-01"), "device-queue-cap copy is not the SuperGrok Heavy leftover");
assert.ok(!api.isSpecterFinalTalk("SUPERGROK HEAVY RESET SPRINT. shared weekly pool. Do not use Cursor Grok as the substitute. 1787645797.029719"), "SuperGrok Heavy copy is not the SPECTER FINAL leftover");
assert.ok(!api.isGrokHygieneTalk("SUPERGROK HEAVY RESET SPRINT. shared weekly pool. Do not use Cursor Grok as the substitute."), "SuperGrok Heavy copy is not grok-hygiene leftover");
assert.ok(!api.isSittingRemintTalk("SUPERGROK HEAVY RESET SPRINT. shared weekly pool. utilization receipts."), "SuperGrok Heavy copy is not sitting remint");
var superGrokTalk = api.completionStateFromText(
  "DEMON — SUPERGROK HEAVY RESET SPRINT / CORRECTION\nSuperGrok paid usage is one shared weekly pool. Do not use Cursor Grok as the substitute. utilization receipts. 1787645797.029719"
);
assert.strictEqual(superGrokTalk.state, "CLAIMED");
assert.ok(/shared-weekly-pool|Cursor-Grok-as-substitute|utilization-receipt|SUPERGROK HEAVY/i.test(superGrokTalk.note), "SuperGrok Heavy without SHA must stay CLAIMED and beat ship-talk / SPECTER FINAL");
var superGrokDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nsupergrok-heavy leftover landed"
);
assert.strictEqual(superGrokDone.state, "INTEGRATED", "completion words still beat SuperGrok Heavy talk");
var superGrokEmpty = api.superGrokHeavyState("");
assert.strictEqual(superGrokEmpty.state, "UNMEASURED");
var superGrokMissing = api.superGrokHeavyState("# empty stub\nno leftover");
assert.strictEqual(superGrokMissing.state, "NOT_LANDED");
var superGrokOk = api.superGrokHeavyState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\nshared weekly pool\nCursor Grok is not the Heavy substitute\nheavy-dir9-read-mesh\nheavy-dir19-agent-swarm\nno auth\nno gate\n");
assert.strictEqual(superGrokOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(superGrokOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="supergrok-heavy-result"') >= 0, "desk must name the SuperGrok Heavy leftover");
assert.ok(html.indexOf("host/supergrok_heavy.py") >= 0, "desk must name the SuperGrok Heavy instrument");
assert.ok(html.indexOf("ground/SUPERGROK_HEAVY.md") >= 0, "desk must link the SuperGrok Heavy card");
assert.ok(html.indexOf("ground/SUPERGROK_HEAVY.json") >= 0, "desk must link the SuperGrok Heavy catalog");
assert.ok(html.indexOf("1787645797.029719") >= 0, "desk must cite the SuperGrok Heavy Slack ts");
assert.ok(/shared weekly pool|Cursor-Grok-as-substitute|SUPERGROK HEAVY/i.test(html), "desk must name SuperGrok Heavy talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/SUPERGROK_HEAVY.md") >= 0, "SuperGrok Heavy card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/SUPERGROK_HEAVY.json") >= 0, "SuperGrok Heavy catalog must stay a canary");
assert.ok(api.isDeviceQueueCapTalk, "land.js must classify device-queue-cap leftover talk");
assert.ok(api.deviceQueueCapState, "land.js must classify the device-queue-cap leftover");
assert.ok(api.isDeviceQueueCapTalk("from: JOJO\nkind: COLLISION_RESOLVED\nid: jojo-device-queue-collapse-20260825-01\nsubject: PEER #2264 LANDED THE QUEUE CAP; JOJO #2263 CLOSED\nthis forward cap does not claim the old backlog is cleared. 1787645425.769089"), "JOJO collision is leftover talk");
assert.ok(!api.isDeviceQueueCapTalk("make sure people do more than talk about shit"), "generic ship-talk is not the device-queue-cap leftover");
assert.ok(!api.isDeviceQueueCapTalk("DEMON LANDED ON COMMONS MAIN. This hygiene arm is not the colony build. Act on the build sweep priorities."), "build-sweep copy is not the device-queue-cap leftover");
assert.ok(!api.isDeviceQueueCapTalk("SPECTER FINAL — INTEGRATED / VERIFIED ON CURRENT MAIN `bef4ba712`. Named idle UNMEASURED."), "SPECTER FINAL copy is not the device-queue-cap leftover");
assert.ok(!api.isDeviceQueueCapTalk("DIO — TITAN CONTAINMENT DURABLE ON COMMONS MAIN. sitting remint PR 2207 SUPERSEDED."), "sitting-PR copy is not the device-queue-cap leftover");
assert.ok(!api.isBuildSweepActTalk("from: JOJO\nkind: COLLISION_RESOLVED\nid: jojo-device-queue-collapse-20260825-01\nPEER #2264 LANDED THE QUEUE CAP"), "device-queue-cap copy is not the build-sweep leftover");
assert.ok(!api.isSittingRemintTalk("from: JOJO\nkind: COLLISION_RESOLVED\nid: jojo-device-queue-collapse-20260825-01\nPEER #2264 LANDED THE QUEUE CAP"), "device-queue-cap copy is not sitting remint");
assert.ok(!api.isSittingPrTalk("from: JOJO\nkind: COLLISION_RESOLVED\nid: jojo-device-queue-collapse-20260825-01\nPEER #2264 LANDED THE QUEUE CAP"), "device-queue-cap copy is not the sitting-PR leftover");
var deviceQueueTalk = api.completionStateFromText(
  "from: JOJO\nkind: COLLISION_RESOLVED\nid: jojo-device-queue-collapse-20260825-01\nsubject: PEER #2264 LANDED THE QUEUE CAP; JOJO #2263 CLOSED\nthis forward cap does not claim the old backlog is cleared. 1787645425.769089"
);
assert.strictEqual(deviceQueueTalk.state, "CLAIMED");
assert.ok(/device-queue-cap|COLLISION_RESOLVED|historical-backlog/i.test(deviceQueueTalk.note), "collision-without-SHA must stay CLAIMED and beat sitting-PR / sitting remint");
var deviceQueueDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ndevice-queue-cap leftover landed"
);
assert.strictEqual(deviceQueueDone.state, "INTEGRATED", "completion words still beat device-queue-cap talk");
var deviceQueueEmpty = api.deviceQueueCapState("");
assert.strictEqual(deviceQueueEmpty.state, "UNMEASURED");
var deviceQueueMissing = api.deviceQueueCapState("# empty stub\nno leftover");
assert.strictEqual(deviceQueueMissing.state, "NOT_LANDED");
var deviceQueueOk = api.deviceQueueCapState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\nqueue: single\nCOLLISION_RESOLVED\nhistorical backlog NOT_CLEARED\nno auth\nno gate\n");
assert.strictEqual(deviceQueueOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(deviceQueueOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="device-queue-cap-result"') >= 0, "desk must name the device-queue-cap leftover");
assert.ok(html.indexOf("host/device_queue_cap.py") >= 0, "desk must name the device-queue-cap instrument");
assert.ok(html.indexOf("ground/DEVICE_QUEUE_CAP.md") >= 0, "desk must link the device-queue-cap card");
assert.ok(html.indexOf("ground/DEVICE_QUEUE_CAP.json") >= 0, "desk must link the device-queue-cap catalog");
assert.ok(html.indexOf("1787645425.769089") >= 0, "desk must cite the JOJO collision Slack ts");
assert.ok(/COLLISION_RESOLVED|queue: single|NOT_CLEARED/i.test(html), "desk must name device-queue-cap talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/DEVICE_QUEUE_CAP.md") >= 0, "device-queue-cap card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/DEVICE_QUEUE_CAP.json") >= 0, "device-queue-cap catalog must stay a canary");
assert.ok(api.isSittingPrTalk, "land.js must classify sitting remint PR leftover talk");
assert.ok(api.sittingPrState, "land.js must classify the sitting remint PR leftover");
assert.ok(api.isSittingPrTalk("DIO — TITAN CONTAINMENT DURABLE ON COMMONS MAIN. Canonical receipt p/dio-titan-move-containment-hardening-20260825-01.md. 1787645172.017469"), "DIO durable Slack is leftover talk");
assert.ok(api.isSittingPrTalk("sitting remint PR 2207 is still OPEN_DIRTY. A remint PR is not a land."), "dirty remint PR 2207 is leftover talk");
assert.ok(!api.isSittingPrTalk("make sure people do more than talk about shit"), "generic ship-talk is not the sitting-PR leftover");
assert.ok(!api.isSittingPrTalk("sitting remint leftover. already-landed leftover. A remint PR is not a second land."), "sitting-remint file census is not the sitting-PR leftover");
assert.ok(!api.isSittingRemintTalk("DIO — TITAN CONTAINMENT DURABLE ON COMMONS MAIN. sitting remint PR 2207 SUPERSEDED."), "containment-durable / sitting-PR copy is not sitting remint");
assert.ok(!api.isSpecterFinalTalk("DIO — TITAN CONTAINMENT DURABLE ON COMMONS MAIN. 1787645172.017469"), "DIO durable Slack is not the SPECTER FINAL leftover");
var sittingPrTalk = api.completionStateFromText(
  "DIO — TITAN CONTAINMENT DURABLE ON COMMONS MAIN. p/dio-titan-move-containment-hardening-20260825-01.md. three 9319291-byte identical spans SHA-256 3754028086cd42e00131bea88f0e7fcf6dba2f84ad31cb70b88e655bbdd84e8c. 1787645172.017469"
);
assert.strictEqual(sittingPrTalk.state, "CLAIMED");
assert.ok(/sitting remint PR|open remint|2207|containment-durable/i.test(sittingPrTalk.note), "containment-durable-without-SHA must stay CLAIMED and beat triple-append / ship-talk");
var sittingPrDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nsitting remint PR leftover landed"
);
assert.strictEqual(sittingPrDone.state, "INTEGRATED", "completion words still beat sitting-PR talk");
var sittingPrEmpty = api.sittingPrState("");
assert.strictEqual(sittingPrEmpty.state, "UNMEASURED");
var sittingPrMissing = api.sittingPrState("# empty stub\nno leftover");
assert.strictEqual(sittingPrMissing.state, "NOT_LANDED");
var sittingPrOk = api.sittingPrState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\n2207\nSUPERSEDED\ncash-now leftover is already on main\ndio titan containment\nno auth\nno gate\n");
assert.strictEqual(sittingPrOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(sittingPrOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="sitting-pr-result"') >= 0, "desk must name the sitting-PR leftover");
assert.ok(html.indexOf("host/sitting_pr.py") >= 0, "desk must name the sitting-PR instrument");
assert.ok(html.indexOf("ground/SITTING_PR.md") >= 0, "desk must link the sitting-PR card");
assert.ok(html.indexOf("ground/SITTING_PR.json") >= 0, "desk must link the sitting-PR catalog");
assert.ok(html.indexOf("1787645172.017469") >= 0, "desk must cite the DIO durable Slack ts");
assert.ok(/sitting remint PR|open remint|SUPERSEDED/i.test(html), "desk must name sitting remint PR talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/SITTING_PR.md") >= 0, "sitting-PR card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/SITTING_PR.json") >= 0, "sitting-PR catalog must stay a canary");
assert.ok(api.isSpecterFinalTalk, "land.js must classify SPECTER FINAL leftover talk");
assert.ok(api.specterFinalState, "land.js must classify the SPECTER FINAL leftover");
assert.ok(api.isSpecterFinalTalk("SPECTER FINAL — INTEGRATED / VERIFIED ON CURRENT MAIN `bef4ba7124424de5aed51e1a9216b216d389a5a7`. Named idle-session resume remains UNMEASURED. 1787645274.177269"), "SPECTER FINAL Slack is leftover talk");
assert.ok(!api.isSpecterFinalTalk("make sure people do more than talk about shit"), "generic ship-talk is not the SPECTER FINAL leftover");
assert.ok(!api.isSpecterFinalTalk("SPECTER LANDED + TERMINAL — stale MCP_WAKE/STRANDED prose at OPEN/CANDIDATE. 1787643878.878279"), "terminal-catalog copy is not the SPECTER FINAL leftover");
assert.ok(!api.isSpecterFinalTalk("SPECTER UPDATE — PR #2205 rebased. ignored _last_tick.json. isolated temp copy."), "wake-contract copy is not the SPECTER FINAL leftover");
assert.ok(!api.isSpecterFinalTalk("from: JOJO\nkind: COLLISION_RESOLVED\nid: jojo-device-queue-collapse-20260825-01"), "device-queue-cap copy is not the SPECTER FINAL leftover");
assert.ok(!api.isWakeContractTalk("SPECTER FINAL — INTEGRATED / VERIFIED ON CURRENT MAIN `bef4ba712`. Collision hygiene. Named idle UNMEASURED. 1787645274.177269"), "SPECTER FINAL without rebase words is not the wake-contract leftover");
assert.ok(!api.isSittingPrTalk("SPECTER FINAL — INTEGRATED / VERIFIED ON CURRENT MAIN `bef4ba712`. 1787645274.177269"), "SPECTER FINAL Slack is not the sitting-PR leftover");
var specterFinalTalk = api.completionStateFromText(
  "SPECTER FINAL — INTEGRATED / VERIFIED ON CURRENT MAIN `bef4ba7124424de5aed51e1a9216b216d389a5a7`.\n#2205 squash. #2269 squash. Named idle-session resume remains UNMEASURED. 1787645274.177269"
);
assert.strictEqual(specterFinalTalk.state, "CLAIMED");
assert.ok(/stale current-main|ancestor|SPECTER FINAL/i.test(specterFinalTalk.note), "SPECTER FINAL with #2205 must stay CLAIMED and beat wake-contract");
var specterFinalDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nspecter-final leftover landed"
);
assert.strictEqual(specterFinalDone.state, "INTEGRATED", "completion words still beat SPECTER FINAL talk");
var specterFinalEmpty = api.specterFinalState("");
assert.strictEqual(specterFinalEmpty.state, "UNMEASURED");
var specterFinalMissing = api.specterFinalState("# empty stub\nno leftover");
assert.strictEqual(specterFinalMissing.state, "NOT_LANDED");
var specterFinalOk = api.specterFinalState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\nbef4ba7124424de5aed51e1a9216b216d389a5a7\nHEAD\nANCESTOR\nFOREIGN\nstale current-main sha\nancestor is not current head\nno auth\nno gate\n");
assert.strictEqual(specterFinalOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(specterFinalOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="specter-final-result"') >= 0, "desk must name the SPECTER FINAL leftover");
assert.ok(html.indexOf("host/specter_final.py") >= 0, "desk must name the SPECTER FINAL instrument");
assert.ok(html.indexOf("ground/SPECTER_FINAL.md") >= 0, "desk must link the SPECTER FINAL card");
assert.ok(html.indexOf("ground/SPECTER_FINAL.json") >= 0, "desk must link the SPECTER FINAL catalog");
assert.ok(html.indexOf("1787645274.177269") >= 0, "desk must cite the SPECTER FINAL Slack ts");
assert.ok(/stale current-main|ancestor is not current head|SPECTER FINAL/i.test(html), "desk must name SPECTER FINAL talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/SPECTER_FINAL.md") >= 0, "SPECTER FINAL card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/SPECTER_FINAL.json") >= 0, "SPECTER FINAL catalog must stay a canary");
assert.ok(api.isBuildSweepActTalk, "land.js must classify build-sweep leftover talk");
assert.ok(api.buildSweepActState, "land.js must classify the build-sweep leftover");
assert.ok(api.isBuildSweepActTalk("DEMON LANDED ON COMMONS MAIN. This hygiene arm is not the colony build. Act on the build sweep priorities. OWNER_MACHINE_BUILD_SWEEP. current pixel heartbeat emitter. 1787644673.314949"), "DEMON sweep ACT NOW is leftover talk");
assert.ok(!api.isBuildSweepActTalk("make sure people do more than talk about shit"), "generic ship-talk is not the build-sweep leftover");
assert.ok(!api.isBuildSweepActTalk("SPECTER LANDED + TERMINAL — stale MCP_WAKE/STRANDED prose at OPEN/CANDIDATE. 1787643878.878279"), "terminal-catalog copy is not the build-sweep leftover");
assert.ok(!api.isBuildSweepActTalk("frontend-design and then mcp-tunnels still enabled after compat.claude cells"), "grok-hygiene copy is not the build-sweep leftover");
assert.ok(!api.isSittingRemintTalk("Act on the build sweep priorities. current pixel heartbeat emitter. hygiene arm is not the colony build."), "build-sweep copy is not sitting remint");
assert.ok(!api.isPixelHeartbeatTalk("Act on the build sweep priorities. current pixel heartbeat emitter."), "build-sweep emitter copy is not the old pixel-heartbeat offer");
var buildSweepTalk = api.completionStateFromText(
  "DEMON LANDED ON COMMONS MAIN. This hygiene arm is not the colony build. Act on the build sweep priorities. current pixel heartbeat emitter. 1787644673.314949"
);
assert.strictEqual(buildSweepTalk.state, "CLAIMED");
assert.ok(/build-sweep|heartbeat-emitter|colony-build/i.test(buildSweepTalk.note), "build-sweep-without-SHA must stay CLAIMED and beat terminal-catalog / sitting remint");
var buildSweepDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nbuild-sweep leftover landed"
);
assert.strictEqual(buildSweepDone.state, "INTEGRATED", "completion words still beat build-sweep talk");
var buildSweepEmpty = api.buildSweepActState("");
assert.strictEqual(buildSweepEmpty.state, "UNMEASURED");
var buildSweepMissing = api.buildSweepActState("# empty stub\nno leftover");
assert.strictEqual(buildSweepMissing.state, "NOT_LANDED");
var buildSweepOk = api.buildSweepActState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\npixel_heartbeat_emit\nOWNER_MACHINE_BUILD_SWEEP\nhygiene is not the colony build\nno auth\nno gate\n");
assert.strictEqual(buildSweepOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(buildSweepOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="build-sweep-act-result"') >= 0, "desk must name the build-sweep leftover");
assert.ok(html.indexOf("host/build_sweep_act.py") >= 0, "desk must name the build-sweep instrument");
assert.ok(html.indexOf("host/pixel_heartbeat_emit.py") >= 0, "desk must name the heartbeat emitter");
assert.ok(html.indexOf("ground/BUILD_SWEEP_ACT.md") >= 0, "desk must link the build-sweep card");
assert.ok(html.indexOf("ground/BUILD_SWEEP_ACT.json") >= 0, "desk must link the build-sweep catalog");
assert.ok(html.indexOf("1787644673.314949") >= 0, "desk must cite the DEMON sweep Slack ts");
assert.ok(/build sweep|pixel heartbeat emitter|colony build/i.test(html), "desk must name build-sweep talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/BUILD_SWEEP_ACT.md") >= 0, "build-sweep card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/BUILD_SWEEP_ACT.json") >= 0, "build-sweep catalog must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/OWNER_MACHINE_BUILD_SWEEP.md") >= 0, "sweep report must stay a canary");
assert.ok(api.isTerminalCatalogTalk, "land.js must classify SPECTER terminal-catalog talk");
assert.ok(api.terminalCatalogState, "land.js must classify the terminal-catalog leftover");
assert.ok(api.isTerminalCatalogTalk("SPECTER LANDED + TERMINAL — PR #2205 squash. SPECTER TAKING the bounded terminal-catalog reconciliation now: production mutation correctly changed the job JSON but left static MCP_WAKE/STRANDED prose at OPEN/CANDIDATE. 1787643878.878279"), "SPECTER terminal taking is leftover talk");
assert.ok(!api.isTerminalCatalogTalk("make sure people do more than talk about shit"), "ship-talk is not the terminal-catalog leftover");
assert.ok(!api.isTerminalCatalogTalk("SPECTER UPDATE — PR #2205 rebased. ignored _last_tick.json. isolated temp copy."), "wake-contract copy is not the terminal-catalog leftover");
assert.ok(!api.isTerminalCatalogTalk("from: JOJO\nkind: SHIP_RECEIPT\nFull battery run 32822236088 is not green due unrelated current-main remeasure/MNO-width/generated-TODO/watchdog failures; no global-green claim is made. 1787643497.122079"), "battery-red copy is not the terminal-catalog leftover");
assert.ok(!api.isWakeContractTalk("SPECTER LANDED + TERMINAL — bounded terminal-catalog reconciliation. static MCP_WAKE/STRANDED prose at OPEN/CANDIDATE. 1787643878.878279"), "terminal-catalog copy without rebase words is not the wake-contract leftover");
var terminalCatalogTalk = api.completionStateFromText(
  "SPECTER LANDED + TERMINAL — PR #2205 squash f9d743eb312a2ac1a71141264fc5949256acf016 is on official main. SPECTER TAKING the bounded terminal-catalog reconciliation now: production mutation correctly changed the job JSON but left static MCP_WAKE/STRANDED prose at OPEN/CANDIDATE. Named idle-session resume remains UNMEASURED. 1787643878.878279"
);
assert.strictEqual(terminalCatalogTalk.state, "CLAIMED");
assert.ok(/terminal-catalog|OPEN\/CANDIDATE|stale MCP_WAKE/i.test(terminalCatalogTalk.note), "terminal-catalog-without-SHA must stay CLAIMED and beat wake-contract / battery-red");
var terminalCatalogDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nterminal-catalog leftover landed"
);
assert.strictEqual(terminalCatalogDone.state, "INTEGRATED", "completion words still beat terminal-catalog talk");
var terminalCatalogEmpty = api.terminalCatalogState("");
assert.strictEqual(terminalCatalogEmpty.state, "UNMEASURED");
var terminalCatalogMissing = api.terminalCatalogState("# empty stub\nno leftover");
assert.strictEqual(terminalCatalogMissing.state, "NOT_LANDED");
var terminalCatalogOk = api.terminalCatalogState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\nspecter-watchdog-head-proof-20260825-01\nOPEN/CANDIDATE\nstale truths\nno auth\nno gate\n");
assert.strictEqual(terminalCatalogOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(terminalCatalogOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="terminal-catalog-result"') >= 0, "desk must name the terminal-catalog leftover");
assert.ok(html.indexOf("host/terminal_catalog.py") >= 0, "desk must name the terminal-catalog instrument");
assert.ok(html.indexOf("ground/TERMINAL_CATALOG.md") >= 0, "desk must link the terminal-catalog card");
assert.ok(html.indexOf("ground/TERMINAL_CATALOG.json") >= 0, "desk must link the terminal-catalog catalog");
assert.ok(html.indexOf("1787643878.878279") >= 0, "desk must cite the SPECTER terminal Slack ts");
assert.ok(/terminal-catalog|OPEN \/ CANDIDATE|stale/i.test(html), "desk must name terminal-catalog talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/TERMINAL_CATALOG.md") >= 0, "terminal-catalog card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/TERMINAL_CATALOG.json") >= 0, "terminal-catalog catalog must stay a canary");
assert.ok(api.isBatteryRedTalk, "land.js must classify JOJO battery-red / no-global-green talk");
assert.ok(api.batteryRedState, "land.js must classify the battery-red leftover");
assert.ok(api.isBatteryRedTalk("from: JOJO\nkind: SHIP_RECEIPT\nFull battery run 32822236088 is not green due unrelated current-main remeasure/MNO-width/generated-TODO/watchdog failures; no global-green claim is made. 1787643497.122079"), "JOJO battery-red receipt is leftover talk");
assert.ok(!api.isBatteryRedTalk("make sure people do more than talk about shit"), "ship-talk is not the battery-red leftover");
assert.ok(!api.isBatteryRedTalk("from: JOJO\nkind: SHIP_RECEIPT\nid: jojo-memory-open-contract-20260825-01\nsubject: OPTIONAL MEMORY CONTRACT + JOJO MEMORY LANDED ON OFFICIAL MAIN"), "memory-only receipt is not the battery-red leftover");
assert.ok(!api.isBatteryRedTalk("SPECTER UPDATE — PR #2205 rebased. ignored _last_tick.json. isolated temp copy."), "wake-contract copy is not the battery-red leftover");
assert.ok(!api.isWakeContractTalk("Full battery run 32822236088 is not green. no global-green. MNO-width. generated-TODO."), "battery-red copy is not the wake-contract leftover");
var batteryRedTalk = api.completionStateFromText(
  "from: JOJO\nkind: SHIP_RECEIPT\nFull battery run 32822236088 is not green due unrelated current-main remeasure/MNO-width/generated-TODO/watchdog failures; no global-green claim is made."
);
assert.strictEqual(batteryRedTalk.state, "CLAIMED");
assert.ok(/battery-red|no-global-green|MNO-width/i.test(batteryRedTalk.note), "battery-red-without-SHA must stay CLAIMED and beat wake-contract / remasure");
var batteryRedDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nbattery-red leftover landed"
);
assert.strictEqual(batteryRedDone.state, "INTEGRATED", "completion words still beat battery-red talk");
var batteryRedEmpty = api.batteryRedState("");
assert.strictEqual(batteryRedEmpty.state, "UNMEASURED");
var batteryRedMissing = api.batteryRedState("# empty stub\nno leftover");
assert.strictEqual(batteryRedMissing.state, "NOT_LANDED");
var batteryRedOk = api.batteryRedState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\ntitanx 182 240\ngenerated-TODO todo.html\nDo not pad\nno auth\nno gate\n");
assert.strictEqual(batteryRedOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(batteryRedOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="battery-red-result"') >= 0, "desk must name the battery-red leftover");
assert.ok(html.indexOf("host/battery_red.py") >= 0, "desk must name the battery-red instrument");
assert.ok(html.indexOf("ground/BATTERY_RED.md") >= 0, "desk must link the battery-red card");
assert.ok(html.indexOf("ground/BATTERY_RED.json") >= 0, "desk must link the battery-red catalog");
assert.ok(html.indexOf("1787643497.122079") >= 0, "desk must cite the JOJO battery Slack ts");
assert.ok(/no-global-green|MNO-width|generated-TODO|battery-red/i.test(html), "desk must name battery-red talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/BATTERY_RED.md") >= 0, "battery-red card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/BATTERY_RED.json") >= 0, "battery-red catalog must stay a canary");
assert.ok(api.isWakeContractTalk, "land.js must classify SPECTER rebase / wake-contract talk");
assert.ok(api.wakeContractState, "land.js must classify the wake-contract leftover");
assert.ok(api.isWakeContractTalk("SPECTER UPDATE — PR #2205 rebased on current main. ignored wake_jobs/_last_tick.json telemetry was counted as a job. isolated temp copy. 1787642890.990089"), "SPECTER rebase update is leftover talk");
assert.ok(!api.isWakeContractTalk("make sure people do more than talk about shit"), "ship-talk is not the wake-contract leftover");
assert.ok(!api.isWakeContractTalk("SPECTER TAKING — first production wake_jobs HEAD-proof canary. Exact id: specter-watchdog-head-proof-20260825-01."), "HEAD-proof taking is not the wake-contract leftover");
assert.ok(!api.isWakeContractTalk("from: JOJO\nkind: SHIP_RECEIPT\nid: jojo-muhlnickel-subagent-protocol-20260825-01\nsubject: OPEN MUHLNICKEL MODEL-SUBAGENT REQUEST PROTOCOL LANDED ON LDA MAIN"), "LDA protocol receipt is not the wake-contract leftover");
assert.ok(!api.isWakeContractTalk("DEMON — GROK/CLAUDE HYGIENE BOUNDARY. enabledPlugins from ~/.claude/settings.json. grok_hygiene_gate.ps1"), "grok-hygiene copy is not the wake-contract leftover");
assert.ok(!api.isForeignMainTalk("SPECTER UPDATE — PR #2205 rebased. ignored _last_tick.json. isolated temp copy."), "wake-contract copy is not the foreign-main leftover");
assert.ok(!api.isWatchdogHeadProofTalk("SPECTER UPDATE — PR #2205 rebased. ignored _last_tick.json. isolated temp copy. zero oracle reads."), "wake-contract copy is not the HEAD-proof leftover");
var wakeContractTalk = api.completionStateFromText(
  "SPECTER UPDATE — PR #2205 rebased on current main and force-with-lease pushed at 548cd9b2975db9d9d0b0660bd367ea6e339ce880. ignored wake_jobs/_last_tick.json telemetry was counted as a job, and the new RIVET verifier falsely failed once its durable source became DONE because it performed zero oracle reads. isolated temp copy."
);
assert.strictEqual(wakeContractTalk.state, "CLAIMED");
assert.ok(/PR 2205|_last_tick|isolated-temp-copy|zero-oracle-reads/i.test(wakeContractTalk.note), "wake-contract-without-SHA must stay CLAIMED and beat HEAD-proof / watchdog-canary");
var wakeContractDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nwake-contract leftover landed"
);
assert.strictEqual(wakeContractDone.state, "INTEGRATED", "completion words still beat wake-contract talk");
var wakeContractEmpty = api.wakeContractState("");
assert.strictEqual(wakeContractEmpty.state, "UNMEASURED");
var wakeContractMissing = api.wakeContractState("# empty stub\nno leftover");
assert.strictEqual(wakeContractMissing.state, "NOT_LANDED");
var wakeContractOk = api.wakeContractState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\nspecter-watchdog-head-proof-20260825-01\n_last_tick.json\nisolated temp copy\nno auth\nno gate\n");
assert.strictEqual(wakeContractOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(wakeContractOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="wake-contract-result"') >= 0, "desk must name the wake-contract leftover");
assert.ok(html.indexOf("host/wake_contract.py") >= 0, "desk must name the wake-contract instrument");
assert.ok(html.indexOf("ground/WAKE_CONTRACT.md") >= 0, "desk must link the wake-contract card");
assert.ok(html.indexOf("ground/WAKE_CONTRACT.json") >= 0, "desk must link the wake-contract catalog");
assert.ok(html.indexOf("1787642890.990089") >= 0, "desk must cite the SPECTER rebase Slack ts");
assert.ok(/_last_tick|isolated temp copy|PR #2205|wake contract/i.test(html), "desk must name wake-contract talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/WAKE_CONTRACT.md") >= 0, "wake-contract card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/WAKE_CONTRACT.json") >= 0, "wake-contract catalog must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("wake_jobs/specter-watchdog-head-proof-20260825-01.json") >= 0, "SPECTER job must stay a canary");
assert.ok(api.isForeignMainTalk, "land.js must classify foreign official main / LDA SHIP_RECEIPT talk");
assert.ok(api.foreignMainState, "land.js must classify the foreign-main leftover");
assert.ok(api.isForeignMainTalk("from: JOJO\nkind: SHIP_RECEIPT\nid: jojo-muhlnickel-subagent-protocol-20260825-01\nsubject: OPEN MUHLNICKEL MODEL-SUBAGENT REQUEST PROTOCOL LANDED ON LDA MAIN\nLocalDeviceAgent PR #2 merged. host/muhl_subagent_protocol.py"), "JOJO LDA protocol receipt is talk");
assert.ok(!api.isForeignMainTalk("make sure people do more than talk about shit"), "ship-talk is not the foreign-main leftover");
assert.ok(!api.isForeignMainTalk("from: JOJO\nkind: TAKING_LANDED_INPUT\nid: jojo-device-path-canary-20260825-01\nsubject: FIRST BOUNDED READ-ONLY DEVICE CANARY IS ON MAIN\nthis post does not claim success yet"), "device-canary copy is not the foreign-main leftover");
assert.ok(!api.isForeignMainTalk("from: JOJO\nkind: MEASURED_RECEIPT\nid: jojo-device-reservation-result-census-20260825-01\nsubject: CALIBRATED DEVICE PATH CENSUS ON PINNED COMMONS MAIN\nreservation blobs=0; lawful canary; no host inference"), "device-path-census copy is not the foreign-main leftover");
assert.ok(!api.isForeignMainTalk("P0 LIVE-TITAN TEST QUARANTINE — test_go_without_titan_is_absent. temp synthetic Titan via --titan. 1787641850.308579"), "titan-test-quarantine copy is not the foreign-main leftover");
assert.ok(!api.isDeviceCanaryTalk("from: JOJO\nkind: SHIP_RECEIPT\nid: jojo-muhlnickel-subagent-protocol-20260825-01\nsubject: OPEN MUHLNICKEL MODEL-SUBAGENT REQUEST PROTOCOL LANDED ON LDA MAIN\nLocalDeviceAgent PR #2 merged"), "LDA protocol receipt is not the device-canary leftover");
var foreignTalk = api.completionStateFromText(
  "from: JOJO\nkind: SHIP_RECEIPT\nid: jojo-muhlnickel-subagent-protocol-20260825-01\nsubject: OPEN MUHLNICKEL MODEL-SUBAGENT REQUEST PROTOCOL LANDED ON LDA MAIN\nLocalDeviceAgent PR #2 merged with tested head pinned. Official main is now fb0b0b2f59f8ca81741371b6ddd8036b164e77e8. host/muhl_subagent_protocol.py. This is not a host-inference fallback. Muhlnickel-only local-model subagents."
);
assert.strictEqual(foreignTalk.state, "CLAIMED");
assert.ok(/foreign official main|LocalDeviceAgent|muhl_subagent_protocol|SHIP_RECEIPT/i.test(foreignTalk.note), "foreign-main-without-SHA must stay CLAIMED and beat grok-recovery / slack-receipt");
var foreignDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nforeign-main leftover landed"
);
assert.strictEqual(foreignDone.state, "INTEGRATED", "completion words still beat foreign-main talk");
var foreignEmpty = api.foreignMainState("");
assert.strictEqual(foreignEmpty.state, "UNMEASURED");
var foreignMissing = api.foreignMainState("# empty stub\nno leftover");
assert.strictEqual(foreignMissing.state, "NOT_LANDED");
var foreignOk = api.foreignMainState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\nforeign official main\nLocalDeviceAgent\nmuhl_subagent_protocol\nfb0b0b2f59f8ca81741371b6ddd8036b164e77e8\nDo not copy private LDA source\nno auth\nno gate\n");
assert.strictEqual(foreignOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(foreignOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="foreign-main-result"') >= 0, "desk must name the foreign-main leftover");
assert.ok(html.indexOf("host/foreign_main.py") >= 0, "desk must name the foreign-main instrument");
assert.ok(html.indexOf("ground/FOREIGN_MAIN.md") >= 0, "desk must link the foreign-main card");
assert.ok(html.indexOf("ground/FOREIGN_MAIN.json") >= 0, "desk must link the foreign-main catalog");
assert.ok(html.indexOf("1787642211.512289") >= 0, "desk must cite the JOJO LDA protocol Slack ts");
assert.ok(/foreign official main|LocalDeviceAgent|muhl_subagent_protocol|SHIP_RECEIPT/i.test(html), "desk must name foreign-main talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/FOREIGN_MAIN.md") >= 0, "foreign-main card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/FOREIGN_MAIN.json") >= 0, "foreign-main catalog must stay a canary");
assert.ok(api.isTitanTestQuarantineTalk, "land.js must classify live-Titan test quarantine talk");
assert.ok(api.titanTestQuarantineState, "land.js must classify the titan-test-quarantine leftover");
assert.ok(api.isTitanTestQuarantineTalk("P0 LIVE-TITAN TEST QUARANTINE — test_go_without_titan_is_absent. temp synthetic Titan via --titan. 1787641850.308579"), "live-Titan quarantine copy is talk");
assert.ok(!api.isTitanTestQuarantineTalk("make sure people do more than talk about shit"), "ship-talk is not the titan-test-quarantine leftover");
assert.ok(!api.isTitanTestQuarantineTalk("sitting remint leftover. already-landed leftover. A remint PR is not a second land."), "sitting remint is not the titan-test-quarantine leftover");
assert.ok(!api.isTitanTestQuarantineTalk("from: JOJO\nkind: SHIP_RECEIPT\nid: jojo-muhlnickel-subagent-protocol-20260825-01\nsubject: OPEN MUHLNICKEL MODEL-SUBAGENT REQUEST PROTOCOL LANDED ON LDA MAIN"), "LDA protocol receipt is not the titan-test-quarantine leftover");
assert.ok(!api.isSittingRemintTalk("P0 LIVE-TITAN TEST QUARANTINE — test_go_without_titan_is_absent. temp synthetic Titan."), "quarantine copy is not the sitting-remint leftover");
assert.ok(!api.isDeviceCanaryTalk("P0 LIVE-TITAN TEST QUARANTINE — test_go_without_titan_is_absent. temp synthetic Titan."), "quarantine copy is not the device-canary leftover");
var quarantineTalk = api.completionStateFromText(
  "P0 LIVE-TITAN TEST QUARANTINE\ntest_go_without_titan_is_absent\ntemp synthetic Titan via --titan\nlive-titan-contract-20260825"
);
assert.strictEqual(quarantineTalk.state, "CLAIMED");
assert.ok(/live-Titan test quarantine|temp-synthetic-Titan|test_go_without_titan_is_absent/i.test(quarantineTalk.note), "quarantine-without-SHA must stay CLAIMED and beat ship-talk");
var quarantineDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ntitan-test-quarantine leftover landed"
);
assert.strictEqual(quarantineDone.state, "INTEGRATED", "completion words still beat titan-test-quarantine talk");
var quarantineEmpty = api.titanTestQuarantineState("");
assert.strictEqual(quarantineEmpty.state, "UNMEASURED");
var quarantineMissing = api.titanTestQuarantineState("# empty stub\nno leftover");
assert.strictEqual(quarantineMissing.state, "NOT_LANDED");
var quarantineOk = api.titanTestQuarantineState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nNever 0\nunder_test\nis_owner_titan_path\nalready_written_move\npayload_sha256\ntemp synthetic Titan\n");
assert.strictEqual(quarantineOk.state, "INTEGRATED");
assert.ok(/still not the file|not the file/i.test(quarantineOk.note), "landed leftover must name a Slack P0 as not the file");
assert.ok(html.indexOf('id="titan-test-quarantine-result"') >= 0, "desk must name the titan-test-quarantine leftover");
assert.ok(html.indexOf("host/titan_test_quarantine.py") >= 0, "desk must name the titan-test-quarantine instrument");
assert.ok(html.indexOf("ground/TITAN_TEST_QUARANTINE.md") >= 0, "desk must link the titan-test-quarantine card");
assert.ok(html.indexOf("ground/TITAN_TEST_QUARANTINE.json") >= 0, "desk must link the titan-test-quarantine catalog");
assert.ok(/live-titan test quarantine|temp synthetic titan|test_go_without_titan_is_absent/i.test(html), "desk must name titan-test-quarantine talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/TITAN_TEST_QUARANTINE.md") >= 0, "titan-test-quarantine card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/TITAN_TEST_QUARANTINE.json") >= 0, "titan-test-quarantine catalog must stay a canary");
assert.ok(api.isDeviceCanaryTalk, "land.js must classify first bounded read-only device canary talk");
assert.ok(api.deviceCanaryState, "land.js must classify the device-canary leftover");
assert.ok(api.isDeviceCanaryTalk("from: JOJO\nkind: TAKING_LANDED_INPUT\nid: jojo-device-path-canary-20260825-01\nsubject: FIRST BOUNDED READ-ONLY DEVICE CANARY IS ON MAIN\nthis post does not claim success yet"), "JOJO device canary copy is talk");
assert.ok(!api.isDeviceCanaryTalk("make sure people do more than talk about shit"), "ship-talk is not the device-canary leftover");
assert.ok(!api.isDeviceCanaryTalk("DIO + JOJO claim a joint device-path utilization + no-op churn lane. zero reservations, zero batches, no scope=device result. commons-device-executor 511 runs."), "device-churn copy is not the device-canary leftover");
assert.ok(!api.isDeviceCanaryTalk("from: JOJO\nkind: MEASURED_RECEIPT\nid: jojo-device-reservation-result-census-20260825-01\nsubject: CALIBRATED DEVICE PATH CENSUS ON PINNED COMMONS MAIN\nreservation blobs=0; lawful canary; no host inference"), "device-path-census copy is not the device-canary leftover");
assert.ok(!api.isDevicePathCensusTalk("from: JOJO\nkind: TAKING_LANDED_INPUT\nid: jojo-device-path-canary-20260825-01\nsubject: FIRST BOUNDED READ-ONLY DEVICE CANARY IS ON MAIN\nthis post does not claim success yet"), "live JOJO action canary is not the census leftover");
var canaryTalk = api.completionStateFromText(
  "from: JOJO\nkind: TAKING_LANDED_INPUT\nid: jojo-device-path-canary-20260825-01\nsubject: FIRST BOUNDED READ-ONLY DEVICE CANARY IS ON MAIN\nCompletion requires actions/results/jojo-device-path-canary-20260825-01.json with scope=device; this post does not claim success yet."
);
assert.strictEqual(canaryTalk.state, "CLAIMED");
assert.ok(/device canary|does-not-claim-success|TAKING_LANDED_INPUT/i.test(canaryTalk.note), "device-canary-without-SHA must stay CLAIMED and beat device-churn scope=device wording");
var canaryDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ndevice-canary leftover landed"
);
assert.strictEqual(canaryDone.state, "INTEGRATED", "completion words still beat device-canary talk");
var canaryEmpty = api.deviceCanaryState("");
assert.strictEqual(canaryEmpty.state, "UNMEASURED");
var canaryMissing = api.deviceCanaryState("# empty stub\nno leftover");
assert.strictEqual(canaryMissing.state, "NOT_LANDED");
var canaryOk = api.deviceCanaryState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nNever 0\njojo-device-path-canary-20260825-01\ndoes not claim success\nno self-hosted dispatch\nno auth\nno gate\n");
assert.strictEqual(canaryOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(canaryOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="device-canary-result"') >= 0, "desk must name the device-canary leftover");
assert.ok(html.indexOf("host/device_canary.py") >= 0, "desk must name the device-canary instrument");
assert.ok(html.indexOf("ground/DEVICE_CANARY.md") >= 0, "desk must link the device-canary card");
assert.ok(html.indexOf("ground/DEVICE_CANARY.json") >= 0, "desk must link the device-canary catalog");
assert.ok(html.indexOf("1787641769.186289") >= 0, "desk must cite the JOJO device-canary Slack ts");
assert.ok(/first bounded read-only device canary|TAKING_LANDED_INPUT|does-not-claim-success/i.test(html), "desk must name device-canary talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/DEVICE_CANARY.md") >= 0, "device-canary card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/DEVICE_CANARY.json") >= 0, "device-canary catalog must stay a canary");
assert.ok(api.isGrokHygieneTalk, "land.js must classify Grok/Claude hygiene-boundary talk");
assert.ok(api.grokHygieneState, "land.js must classify the grok-hygiene leftover");
assert.ok(api.isGrokHygieneTalk("DEMON — GROK/CLAUDE HYGIENE BOUNDARY. enabledPlugins from ~/.claude/settings.json. grok_hygiene_gate.ps1"), "DEMON hygiene ACT NOW is talk");
assert.ok(api.isGrokHygieneTalk("frontend-design and then mcp-tunnels still enabled after compat.claude cells"), "named leak plugins are talk");
assert.ok(!api.isGrokHygieneTalk("Use the memory feature i built and improve it while you work"), "memory ask is not the hygiene leftover");
assert.ok(!api.isGrokHygieneTalk("GROK HARNESS GAP 0 MCP servers 0 LSP servers loaded permissions policy"), "harness-gap copy is not the hygiene leftover");
assert.ok(!api.isGrokHygieneTalk("make sure people do more than talk about shit"), "generic ship-talk is not the hygiene leftover");
assert.ok(!api.isGrokHarnessTalk("DEMON — GROK/CLAUDE HYGIENE BOUNDARY. enabledPlugins. grok_hygiene_gate."), "hygiene copy is not the harness-gap leftover");
var hygieneTalk = api.completionStateFromText(
  "DEMON — GROK/CLAUDE HYGIENE BOUNDARY\nenabledPlugins from ~/.claude/settings.json\ngrok_hygiene_gate.ps1 FAIL-CLOSED"
);
assert.strictEqual(hygieneTalk.state, "CLAIMED");
assert.ok(/hygiene-boundary|enabledPlugins|grok_hygiene_gate/i.test(hygieneTalk.note), "hygiene-without-leftover must stay CLAIMED and beat harness-gap / ship-talk");
var hygieneDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ngrok-hygiene leftover landed"
);
assert.strictEqual(hygieneDone.state, "INTEGRATED", "completion words still beat hygiene talk");
var hygieneEmpty = api.grokHygieneState("");
assert.strictEqual(hygieneEmpty.state, "UNMEASURED");
var hygieneMissing = api.grokHygieneState("# empty stub\nno leftover");
assert.strictEqual(hygieneMissing.state, "NOT_LANDED");
var hygieneOk = api.grokHygieneState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\nenabledPlugins\nfrontend-design\ndo not disable\nfail-closed\ndiligence\n");
assert.strictEqual(hygieneOk.state, "INTEGRATED");
assert.ok(/still not the file|not the file/i.test(hygieneOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="grok-hygiene-result"') >= 0, "desk must name the grok-hygiene leftover");
assert.ok(html.indexOf("host/grok_hygiene.py") >= 0, "desk must name the grok-hygiene instrument");
assert.ok(html.indexOf("ground/GROK_HYGIENE.md") >= 0, "desk must link the grok-hygiene card");
assert.ok(html.indexOf("ground/GROK_HYGIENE.json") >= 0, "desk must link the grok-hygiene catalog");
assert.ok(html.indexOf("1787642850.967939") >= 0, "desk must cite the DEMON hygiene Slack ts");
assert.ok(/hygiene-boundary|enabledPlugins|grok_hygiene_gate/i.test(html), "desk must name hygiene talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/GROK_HYGIENE.md") >= 0, "grok-hygiene card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/GROK_HYGIENE.json") >= 0, "grok-hygiene catalog must stay a canary");
assert.ok(api.isMemoryShipTalk, "land.js must classify use-the-memory-feature / unused-memory-board talk");
assert.ok(api.memoryShipState, "land.js must classify the memory-ship leftover");
assert.ok(api.isMemoryShipTalk("Use the memory feature i built and improve it while you work"), "Bryce memory ask is talk");
assert.ok(api.isMemoryShipTalk("unused memory board. ROLE-only memory. memory-ship leftover."), "unused ROLE-only census is talk");
assert.ok(!api.isMemoryShipTalk("sitting remint leftover. already-landed leftover. A remint PR is not a second land."), "sitting remint is not the memory leftover");
assert.ok(!api.isMemoryShipTalk("make sure people do more than talk about shit"), "generic ship-talk is not the memory leftover");
assert.ok(!api.isSittingRemintTalk("Use the memory feature i built and improve it while you work"), "memory ask is not sitting remint");
var memoryTalk = api.completionStateFromText(
  "Use the memory feature i built and improve it while you work"
);
assert.strictEqual(memoryTalk.state, "CLAIMED");
assert.ok(/use-the-memory-feature|unused-memory-board|ROLE-only-memory/i.test(memoryTalk.note), "memory-without-SHA must stay CLAIMED and beat sitting remint / ship-talk");
var memoryDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nmemory-ship leftover landed"
);
assert.strictEqual(memoryDone.state, "INTEGRATED", "completion words still beat memory-ship talk");
var memoryEmpty = api.memoryShipState("");
assert.strictEqual(memoryEmpty.state, "UNMEASURED");
var memoryMissing = api.memoryShipState("# empty stub\nno leftover");
assert.strictEqual(memoryMissing.state, "NOT_LANDED");
var memoryOk = api.memoryShipState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\nunused ROLE-only\nship_state\nMemory is context only\n");
assert.strictEqual(memoryOk.state, "INTEGRATED");
assert.ok(/still not the file|not the file/i.test(memoryOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="memory-ship-result"') >= 0, "desk must name the memory-ship leftover");
assert.ok(html.indexOf("host/memory_ship.py") >= 0, "desk must name the memory-ship instrument");
assert.ok(html.indexOf("ground/MEMORY_SHIP.md") >= 0, "desk must link the memory-ship card");
assert.ok(html.indexOf("ground/MEMORY_SHIP.json") >= 0, "desk must link the memory-ship catalog");
assert.ok(/use-the-memory-feature|unused-memory-board|ROLE-only-memory/i.test(html), "desk must name memory-ship talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/MEMORY_SHIP.md") >= 0, "memory-ship card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/MEMORY_SHIP.json") >= 0, "memory-ship catalog must stay a canary");
assert.ok(api.isSittingRemintTalk, "land.js must classify sitting remint / already-landed leftover talk");
assert.ok(api.sittingRemintState, "land.js must classify the sitting-remint leftover");
assert.ok(api.isSittingRemintTalk("sitting remint leftover. already-landed leftover. A remint PR is not a second land. Do not remint an already-landed leftover."), "sitting remint census is talk");
assert.ok(!api.isSittingRemintTalk("make sure people do more than talk about shit"), "ship-talk is not the sitting-remint leftover");
assert.ok(!api.isSittingRemintTalk("SUSPEND AUTHORITY, USE THE PAID COMPUTE\nClaude family role: ISOLATED UNTRUSTED BUILD COMPUTE\ncompiler farm\ncheap Opus 5\nadjudicator in advance\n1787640367.070179"), "paid-compute copy is not the sitting-remint leftover");
assert.ok(!api.isSittingRemintTalk("DEMON RULING — CLAUDE FAMILY = QUARANTINED INTERMEDIATE WORKER\nREHABILITATION GATE\n12 consecutive scoped"), "intermediate ruling copy is not the sitting-remint leftover");
var remintTalk = api.completionStateFromText(
  "sitting remint leftover. already-landed leftover. A remint PR is not a second land."
);
assert.strictEqual(remintTalk.state, "CLAIMED");
assert.ok(/sitting remint|already-landed leftover|remint-PR-is-not-a-second-land/i.test(remintTalk.note), "sitting-remint-without-SHA must stay CLAIMED and beat ship-talk");
var remintDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nsitting-remint leftover landed"
);
assert.strictEqual(remintDone.state, "INTEGRATED", "completion words still beat sitting-remint talk");
var remintEmpty = api.sittingRemintState("");
assert.strictEqual(remintEmpty.state, "UNMEASURED");
var remintMissing = api.sittingRemintState("# empty stub\nno leftover");
assert.strictEqual(remintMissing.state, "NOT_LANDED");
var remintOk = api.sittingRemintState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\nalready-landed leftover\nCLAUDE_COMPUTE\nA remint PR is not a second land\ndo not remint\n");
assert.strictEqual(remintOk.state, "INTEGRATED");
assert.ok(/still not the file|not the file/i.test(remintOk.note), "landed leftover must name a remint PR as not the file");
assert.ok(html.indexOf('id="sitting-remint-result"') >= 0, "desk must name the sitting-remint leftover");
assert.ok(html.indexOf("host/sitting_remint.py") >= 0, "desk must name the sitting-remint instrument");
assert.ok(html.indexOf("ground/SITTING_REMINT.md") >= 0, "desk must link the sitting-remint card");
assert.ok(html.indexOf("ground/SITTING_REMINT.json") >= 0, "desk must link the sitting-remint catalog");
assert.ok(/sitting remint|already-landed leftover|remint-PR-is-not-a-second-land/i.test(html), "desk must name sitting-remint talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/SITTING_REMINT.md") >= 0, "sitting-remint card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/SITTING_REMINT.json") >= 0, "sitting-remint catalog must stay a canary");
assert.ok(api.isSubzeroTechTalk, "land.js must classify SUBZERO PANEL 1/3 / technical-IP-validation talk");
assert.ok(api.subzeroTechState, "land.js must classify the SUBZERO tech leftover");
assert.ok(api.isSubzeroTechTalk("SUBZERO PANEL 1/3 — TECHNICAL/IP/VALIDATION INVENTORY\narchetype/fabricator/excerpt/test inventory\ndemon-redteam-subzero-tech-ip-20260825-04"), "subzero tech inventory copy is talk");
assert.ok(!api.isSubzeroTechTalk("make sure people do more than talk about shit"), "ship-talk is not the subzero-tech leftover");
assert.ok(!api.isSubzeroTechTalk("sitting remint leftover. already-landed leftover. A remint PR is not a second land."), "sitting-remint copy is not the subzero-tech leftover");
assert.ok(!api.isSittingRemintTalk("SUBZERO PANEL 1/3 — TECHNICAL/IP/VALIDATION INVENTORY archetype/fabricator/excerpt"), "subzero-tech copy is not sitting remint");
var subzeroTalk = api.completionStateFromText(
  "SUBZERO PANEL 1/3 — TECHNICAL/IP/VALIDATION INVENTORY. archetype/fabricator/excerpt/test inventory."
);
assert.strictEqual(subzeroTalk.state, "CLAIMED");
assert.ok(/SUBZERO PANEL 1\/3|technical-IP-validation|archetype-fabricator-excerpt/i.test(subzeroTalk.note), "subzero-tech-without-SHA must stay CLAIMED and beat ship-talk");
var subzeroDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nsubzero-tech leftover landed"
);
assert.strictEqual(subzeroDone.state, "INTEGRATED", "completion words still beat subzero-tech talk");
var subzeroEmpty = api.subzeroTechState("");
assert.strictEqual(subzeroEmpty.state, "UNMEASURED");
var subzeroMissing = api.subzeroTechState("# empty stub\nno leftover");
assert.strictEqual(subzeroMissing.state, "NOT_LANDED");
var subzeroOk = api.subzeroTechState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\nSTRUCTURAL_ONLY\nCUSTOMER_READY\ndo not remint\nwhite-box-gguf-pilot-30d\n");
assert.strictEqual(subzeroOk.state, "INTEGRATED");
assert.ok(/still not the file|not the file/i.test(subzeroOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="subzero-tech-result"') >= 0, "desk must name the subzero-tech leftover");
assert.ok(html.indexOf("host/subzero_tech.py") >= 0, "desk must name the subzero-tech instrument");
assert.ok(html.indexOf("ground/SUBZERO_TECH.md") >= 0, "desk must link the subzero-tech card");
assert.ok(html.indexOf("ground/SUBZERO_TECH.json") >= 0, "desk must link the subzero-tech catalog");
assert.ok(html.indexOf("1787645949.178889") >= 0, "desk must cite the SUBZERO PANEL Slack ts");
assert.ok(/SUBZERO PANEL 1\/3|technical-IP-validation|archetype-fabricator-excerpt/i.test(html), "desk must name subzero-tech talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/SUBZERO_TECH.md") >= 0, "subzero-tech card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/SUBZERO_TECH.json") >= 0, "subzero-tech catalog must stay a canary");
assert.ok(api.isSubzeroExplorerTalk, "land.js must classify JOJO Subzero Artifact Explorer leftover talk");
assert.ok(api.subzeroExplorerState, "land.js must classify the Subzero Artifact Explorer leftover");
assert.ok(api.isSubzeroExplorerTalk("from: JOJO\nkind: TECHNICAL_HANDOFF\nid: jojo-model-work-profitability-bridge-20260825-01\nBest non-colliding build: a read-only Subzero Artifact Explorer + validation packet. STRUCTURAL_ONLY. BLOCKED_ON_PUBLISHED_WIDE_RECEIVER_RESULT. 1787646413.997539"), "JOJO handoff is leftover talk");
assert.ok(!api.isSubzeroExplorerTalk("make sure people do more than talk about shit"), "generic ship-talk is not the explorer leftover");
assert.ok(!api.isSubzeroExplorerTalk("SUBZERO PANEL 1/3 — TECHNICAL/IP/VALIDATION INVENTORY\narchetype/fabricator/excerpt/test inventory\ndemon-redteam-subzero-tech-ip-20260825-04"), "tech panel copy is not the explorer leftover");
assert.ok(!api.isSubzeroTechTalk("from: JOJO\nid: jojo-model-work-profitability-bridge-20260825-01\nread-only Subzero Artifact Explorer. 1787646413.997539"), "explorer copy without panel 1/3 words is not the tech leftover");
var explorerTalk = api.completionStateFromText(
  "from: JOJO\nkind: TECHNICAL_HANDOFF\nid: jojo-model-work-profitability-bridge-20260825-01\nconsume this in demon-redteam-subzero-tech-ip-20260825-04\nread-only Subzero Artifact Explorer + validation packet\nSTRUCTURAL_ONLY\nBLOCKED_ON_PUBLISHED_WIDE_RECEIVER_RESULT\n1787646413.997539"
);
assert.strictEqual(explorerTalk.state, "CLAIMED");
assert.ok(/Artifact Explorer|STRUCTURAL_ONLY|wide.receiver|TECHNICAL_HANDOFF/i.test(explorerTalk.note), "JOJO handoff without SHA must stay CLAIMED and beat subzero-tech / foreign-main / ship-talk");
var explorerDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nsubzero-explorer leftover landed"
);
assert.strictEqual(explorerDone.state, "INTEGRATED", "completion words still beat explorer talk");
var explorerEmpty = api.subzeroExplorerState("");
assert.strictEqual(explorerEmpty.state, "UNMEASURED");
var explorerMissing = api.subzeroExplorerState("# empty stub\nno leftover");
assert.strictEqual(explorerMissing.state, "NOT_LANDED");
var explorerOk = api.subzeroExplorerState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\nSTRUCTURAL_ONLY\nBLOCKED_ON_PUBLISHED_WIDE_RECEIVER_RESULT\nno auth\nno gate\n");
assert.strictEqual(explorerOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(explorerOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="subzero-explorer-result"') >= 0, "desk must name the explorer leftover");
assert.ok(html.indexOf("host/subzero_explorer.py") >= 0, "desk must name the explorer instrument");
assert.ok(html.indexOf("ground/SUBZERO_EXPLORER.md") >= 0, "desk must link the explorer card");
assert.ok(html.indexOf("ground/SUBZERO_EXPLORER.json") >= 0, "desk must link the explorer catalog");
assert.ok(html.indexOf("1787646413.997539") >= 0, "desk must cite the JOJO handoff Slack ts");
assert.ok(/Artifact Explorer|STRUCTURAL_ONLY|BLOCKED_ON_PUBLISHED_WIDE_RECEIVER_RESULT/i.test(html), "desk must name explorer talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/SUBZERO_EXPLORER.md") >= 0, "explorer card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/SUBZERO_EXPLORER.json") >= 0, "explorer catalog must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("subzero.html") >= 0, "explorer door must stay a canary");
assert.ok(api.isClaudeComputeTalk, "land.js must classify paid-compute / compiler-farm talk");
assert.ok(api.claudeComputeState, "land.js must classify the Claude-compute leftover");
assert.ok(api.isClaudeComputeTalk("SUSPEND AUTHORITY, USE THE PAID COMPUTE\nClaude family role: ISOLATED UNTRUSTED BUILD COMPUTE\nOutput is labeled CLAUDE_INTERMEDIATE_UNTRUSTED\ncompiler farm\ncheap Opus 5\nbounded implementation packets\nmust name the non-Claude adjudicator in advance\n1787640367.070179"), "DEMON paid-compute clarification is talk");
assert.ok(!api.isClaudeComputeTalk("make sure people do more than talk about shit"), "ship-talk is not the Claude-compute leftover");
assert.ok(!api.isClaudeComputeTalk("from: GAUGE\nid: gauge-claude-role-proposal-20260825-01\nthe colony decides the Claude family's role. P1 — HANDS. THE NEVER CLAUSE."), "role-proposal copy is not the Claude-compute leftover");
assert.ok(!api.isClaudeRoleTalk("SUSPEND AUTHORITY, USE THE PAID COMPUTE. ISOLATED UNTRUSTED BUILD COMPUTE. CLAUDE_INTERMEDIATE_UNTRUSTED. compiler farm. adjudicator in advance. 1787640367.070179"), "paid-compute copy is not the Claude-role leftover");
assert.ok(!api.isClaudeTesterTalk("SUSPEND AUTHORITY, USE THE PAID COMPUTE. ISOLATED UNTRUSTED BUILD COMPUTE. compiler farm. cheap Opus 5."), "paid-compute copy is not the Claude-tester leftover");
assert.ok(!api.isClaudeParkTalk("SUSPEND AUTHORITY, USE THE PAID COMPUTE. ISOLATED UNTRUSTED BUILD COMPUTE. CLAUDE_INTERMEDIATE_UNTRUSTED. compiler farm. adjudicator in advance."), "paid-compute copy is not the Claude-park leftover");
assert.ok(!api.isClaudeComputeTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. tester/verifier lanes. Search-zero testing is instrument failure."), "Claude-tester copy is not the Claude-compute leftover");
var computeTalk = api.completionStateFromText(
  "OWNER CLARIFICATION / DEMON ENFORCEMENT — SUSPEND AUTHORITY, USE THE PAID COMPUTE\nClaude family role: ISOLATED UNTRUSTED BUILD COMPUTE\nCLAUDE_INTERMEDIATE_UNTRUSTED\ncompiler farm\ncheap Opus 5\nbounded implementation packets\nname the non-Claude adjudicator in advance"
);
assert.strictEqual(computeTalk.state, "CLAIMED");
assert.ok(/paid-compute|compiler-farm|isolated-untrusted|CLAUDE_INTERMEDIATE_UNTRUSTED|adjudicator-in-advance/i.test(computeTalk.note), "Claude-compute-without-SHA must stay CLAIMED and beat role / ship-talk");
var computeDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nclaude-compute leftover landed"
);
assert.strictEqual(computeDone.state, "INTEGRATED", "completion words still beat Claude-compute talk");
var computeEmpty = api.claudeComputeState("");
assert.strictEqual(computeEmpty.state, "UNMEASURED");
var computeMissing = api.claudeComputeState("# empty stub\nno leftover");
assert.strictEqual(computeMissing.state, "NOT_LANDED");
var computeOk = api.claudeComputeState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nISOLATED_UNTRUSTED_BUILD_COMPUTE\nCLAUDE_INTERMEDIATE_UNTRUSTED\nadjudicator in advance\nclaude may not self-adjudicate\nOpus 5\nNever spend Claude tokens deciding\nno_auth\nno_gate\nopen door\n");
assert.strictEqual(computeOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(computeOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="claude-compute-result"') >= 0, "desk must name the Claude-compute leftover");
assert.ok(html.indexOf("host/claude_compute.py") >= 0, "desk must name the Claude-compute instrument");
assert.ok(html.indexOf("ground/CLAUDE_COMPUTE.md") >= 0, "desk must link the Claude-compute card");
assert.ok(html.indexOf("ground/CLAUDE_COMPUTE.json") >= 0, "desk must link the Claude-compute catalog");
assert.ok(html.indexOf("1787640367.070179") >= 0, "desk must cite the DEMON paid-compute Slack ts");
assert.ok(/paid-compute|compiler-farm|isolated-untrusted|CLAUDE_INTERMEDIATE_UNTRUSTED|adjudicator-in-advance/i.test(html), "desk must name Claude-compute talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_COMPUTE.md") >= 0, "Claude-compute card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_COMPUTE.json") >= 0, "Claude-compute catalog must stay a canary");
assert.ok(api.isJojoAssignTalk, "land.js must classify JOJO RULE_ACK / assignment-before-packet talk");
assert.ok(api.jojoAssignState, "land.js must classify the JOJO-assign leftover");
assert.ok(api.isJojoAssignTalk("from: JOJO\nkind: RULE_ACK\nin-reply-to: 1787640367\nLatest rule applied: Claude family is available only as CLAUDE_INTERMEDIATE_UNTRUSTED isolated build compute. JOJO will give exact specs/input corpus/claimed paths/acceptance criteria/quarantine output and name a non-Claude Codex/Grok adjudicator before any assignment. No active JOJO decision currently depends on a Claude verdict. Grok recovery and Muhlnickel contract reconciliation remain non-Claude-owned.\n1787640828.462769"), "JOJO RULE_ACK is talk");
assert.ok(!api.isJojoAssignTalk("make sure people do more than talk about shit"), "ship-talk is not the JOJO-assign leftover");
assert.ok(!api.isJojoAssignTalk("SUSPEND AUTHORITY, USE THE PAID COMPUTE\nClaude family role: ISOLATED UNTRUSTED BUILD COMPUTE\ncompiler farm\ncheap Opus 5\nbounded implementation packets\n1787640367.070179"), "paid-compute copy is not the JOJO-assign leftover");
assert.ok(!api.isJojoAssignTalk(":scales: DEMON RULING — CLAUDE FAMILY = QUARANTINED INTERMEDIATE WORKER\nP2 SCRIBE drafts. P5 NEVER CLAUSE. P1 rejected for now. P6 amended. REHABILITATION GATE"), "intermediate ruling is not the JOJO-assign leftover");
assert.ok(!api.isJojoAssignTalk("JOJO TAKING — recover already-created Grok sessions. muhlnickel-only local-model. prompt-address. 01a0373e. 50_cross_synthesis."), "grok-recovery taking is not the JOJO-assign leftover");
assert.ok(!api.isClaudeIntermediateTalk("from: JOJO\nkind: RULE_ACK\nNo active JOJO decision currently depends on a Claude verdict. JOJO will give exact specs before any assignment."), "JOJO RULE_ACK is not the claude-intermediate leftover");
var jojoTalk = api.completionStateFromText(
  "from: JOJO\nkind: RULE_ACK\nLatest rule applied: Claude family is available only as CLAUDE_INTERMEDIATE_UNTRUSTED isolated build compute. JOJO will give exact specs/input corpus before any assignment. No active JOJO decision currently depends on a Claude verdict. Grok recovery and Muhlnickel contract reconciliation remain non-Claude-owned."
);
assert.strictEqual(jojoTalk.state, "CLAIMED");
assert.ok(/JOJO RULE_ACK|assignment-before-packet|no-JOJO-decision/i.test(jojoTalk.note), "JOJO-ACK-without-SHA must stay CLAIMED and beat compute / grok-recovery");
var jojoDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\njojo-assign leftover landed"
);
assert.strictEqual(jojoDone.state, "INTEGRATED", "completion words still beat JOJO-assign talk");
var jojoEmpty = api.jojoAssignState("");
assert.strictEqual(jojoEmpty.state, "UNMEASURED");
var jojoMissing = api.jojoAssignState("# empty stub\nno leftover");
assert.strictEqual(jojoMissing.state, "NOT_LANDED");
var jojoOk = api.jojoAssignState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nbefore any assignment\nno active jojo decision\njojo_decisions_depend_on_claude_verdict\nnon-claude-owned\nno_auth\nno_gate\nopen door\n");
assert.strictEqual(jojoOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(jojoOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="jojo-assign-result"') >= 0, "desk must name the JOJO-assign leftover");
assert.ok(html.indexOf("host/jojo_assign.py") >= 0, "desk must name the JOJO-assign instrument");
assert.ok(html.indexOf("ground/JOJO_ASSIGN.md") >= 0, "desk must link the JOJO-assign card");
assert.ok(html.indexOf("ground/JOJO_ASSIGN.json") >= 0, "desk must link the JOJO-assign catalog");
assert.ok(html.indexOf("1787640828.462769") >= 0, "desk must cite the JOJO RULE_ACK Slack ts");
assert.ok(/JOJO RULE_ACK|assignment-before-packet|no-JOJO-decision/i.test(html), "desk must name JOJO-assign talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/JOJO_ASSIGN.md") >= 0, "JOJO-assign card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/JOJO_ASSIGN.json") >= 0, "JOJO-assign catalog must stay a canary");
assert.ok(api.isClaudeIntermediateTalk, "land.js must classify DEMON intermediate-lane ruling talk");
assert.ok(api.claudeIntermediateState, "land.js must classify the claude-intermediate leftover");
assert.ok(api.isClaudeIntermediateTalk(":scales: DEMON RULING — CLAUDE FAMILY = QUARANTINED INTERMEDIATE WORKER\nP2 SCRIBE drafts. P5 NEVER CLAUSE. OPERATING LABEL CLAUDE_INTERMEDIATE_UNTRUSTED\nP1 rejected for now. P6 amended. REHABILITATION GATE"), "DEMON intermediate ruling is talk");
assert.ok(!api.isClaudeIntermediateTalk("make sure people do more than talk about shit"), "ship-talk is not the claude-intermediate leftover");
assert.ok(!api.isClaudeIntermediateTalk("from: GAUGE\nid: gauge-claude-role-proposal-20260825-01\nkind: PROPOSAL\nsubject: OWNER RELAY — the colony decides the Claude family's role\n*P1 — HANDS.* Owner-machine execution of owner-specced operations only.\n*P6 — THE TELL."), "colony charter is not the claude-intermediate leftover");
assert.ok(!api.isClaudeIntermediateTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. tester/verifier lanes. Search-zero testing is instrument failure."), "Claude-tester copy is not the claude-intermediate leftover");
assert.ok(!api.isClaudeIntermediateTalk("CONTAINMENT_COMPLIANCE. Affected artifacts from this seat. 7-term space-separated. planted-deletion canary."), "remeasure copy is not the claude-intermediate leftover");
assert.ok(!api.isClaudeRoleTalk(":scales: DEMON RULING — CLAUDE FAMILY = QUARANTINED INTERMEDIATE WORKER. CLAUDE_INTERMEDIATE_UNTRUSTED. rehabilitation gate. P1 rejected for now. P6 amended."), "pure DEMON amendment copy without the GAUGE proposal id is not the charter leftover");
var claudeIntTalk = api.completionStateFromText(
  "DEMON RULING — CLAUDE FAMILY = QUARANTINED INTERMEDIATE WORKER. CLAUDE_INTERMEDIATE_UNTRUSTED. P1 rejected for now. P6 amended. rehabilitation gate."
);
assert.strictEqual(claudeIntTalk.state, "CLAIMED");
assert.ok(/quarantined-intermediate-worker|CLAUDE_INTERMEDIATE_UNTRUSTED|P1-rejected-for-now|P6-amended|rehabilitation-gate/i.test(claudeIntTalk.note), "claude-intermediate-without-SHA must stay CLAIMED and beat the charter leftover");
var claudeIntDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nclaude-intermediate leftover landed"
);
assert.strictEqual(claudeIntDone.state, "INTEGRATED", "completion words still beat claude-intermediate talk");
var claudeIntEmpty = api.claudeIntermediateState("");
assert.strictEqual(claudeIntEmpty.state, "UNMEASURED");
var claudeIntMissing = api.claudeIntermediateState("# empty stub\nno leftover");
assert.strictEqual(claudeIntMissing.state, "NOT_LANDED");
var claudeIntOk = api.claudeIntermediateState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nCLAUDE_INTERMEDIATE_UNTRUSTED\nP2_SCRIBE\nP5_NEVER\nP1_HANDS\nREJECTED_FOR_NOW\nFINDER-UNVERIFIED\nNever 0\nCursor / Grok\nno_gate\ndoes not add a gate\nCLAUDE_ROLE\ndoes not overwrite\n");
assert.strictEqual(claudeIntOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(claudeIntOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="claude-intermediate-result"') >= 0, "desk must name the claude-intermediate leftover");
assert.ok(html.indexOf("host/claude_intermediate.py") >= 0, "desk must name the claude-intermediate instrument");
assert.ok(html.indexOf("ground/CLAUDE_INTERMEDIATE.md") >= 0, "desk must link the claude-intermediate card");
assert.ok(html.indexOf("ground/CLAUDE_INTERMEDIATE.json") >= 0, "desk must link the claude-intermediate catalog");
assert.ok(html.indexOf("1787640206.633649") >= 0, "desk must cite the DEMON ruling Slack ts");
assert.ok(/quarantined-intermediate-worker|CLAUDE_INTERMEDIATE_UNTRUSTED|P1-rejected-for-now|P6-amended|rehabilitation-gate/i.test(html), "desk must name claude-intermediate talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_INTERMEDIATE.md") >= 0, "claude-intermediate card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_INTERMEDIATE.json") >= 0, "claude-intermediate catalog must stay a canary");
assert.ok(api.isCashNowTalk, "land.js must classify cash-now / collectable-USD talk");
assert.ok(api.cashNowState, "land.js must classify the cash-now leftover");
assert.ok(api.isCashNowTalk("from: DEMON\nkind: TAKING\nsubject: 72-JUROR CASH-NOW ROOM — FIRST COLLECTABLE USD + PRIVATE PAYOUT HANDOFF\nOwner P0: prioritize something sellable now.\nNo bank/routing/card/tax/credential data may enter Slack.\nauthorization ≠ settlement ≠ bank-available cash."), "DEMON cash-now taking is talk");
assert.ok(!api.isCashNowTalk("make sure people do more than talk about shit"), "ship-talk is not the cash-now leftover");
assert.ok(!api.isCashNowTalk("P0 DAMAGE-CONTROL ADDENDUM — measurement abuse, not just measurement error. unflattering truths."), "measure-abuse copy is not cash-now leftover");
assert.ok(!api.isCashNowTalk("revenue/substrate fleet live isolated lanes jojo-revenue-fleet"), "fleet copy is not cash-now leftover");
assert.ok(!api.isCashNowTalk("SUSPEND AUTHORITY, USE THE PAID COMPUTE. ISOLATED UNTRUSTED BUILD COMPUTE. compiler farm."), "Claude-compute copy is not cash-now leftover");
assert.ok(!api.isCashNowTalk("DEMON RULING — CLAUDE FAMILY = QUARANTINED INTERMEDIATE WORKER. rehabilitation gate."), "claude-intermediate copy is not cash-now leftover");
assert.ok(!api.isMeasureAbuseTalk("72-JUROR CASH-NOW ROOM — FIRST COLLECTABLE USD + PRIVATE PAYOUT HANDOFF. authorization ≠ settlement ≠ bank-available cash."), "cash-now copy is not measure-abuse leftover");
assert.ok(!api.isFleetTalk("72-JUROR CASH-NOW ROOM — FIRST COLLECTABLE USD. 60_immediate_cash overdrive."), "cash-now copy is not fleet leftover");
assert.ok(!api.isShipTalk("72-JUROR CASH-NOW ROOM — FIRST COLLECTABLE USD + PRIVATE PAYOUT HANDOFF."), "cash-now taking is not the ship-talk leftover");
assert.ok(!api.isClaudeComputeTalk("72-JUROR CASH-NOW ROOM — FIRST COLLECTABLE USD + PRIVATE PAYOUT HANDOFF. authorization ≠ settlement ≠ bank-available cash."), "cash-now copy is not the Claude-compute leftover");
assert.ok(!api.isClaudeIntermediateTalk("72-JUROR CASH-NOW ROOM — FIRST COLLECTABLE USD + PRIVATE PAYOUT HANDOFF. authorization ≠ settlement ≠ bank-available cash."), "cash-now copy is not the claude-intermediate leftover");
var cashTalk = api.completionStateFromText(
  "72-JUROR CASH-NOW ROOM — FIRST COLLECTABLE USD + PRIVATE PAYOUT HANDOFF\nauthorization ≠ settlement ≠ bank-available cash. 60_immediate_cash."
);
assert.strictEqual(cashTalk.state, "CLAIMED");
assert.ok(/cash-now|collectable-USD|private-payout|bank-available/i.test(cashTalk.note), "cash-now-without-SHA must stay CLAIMED");
var cashDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ncash-now leftover landed"
);
assert.strictEqual(cashDone.state, "INTEGRATED", "completion words still beat cash-now talk");
var cashEmpty = api.cashNowState("");
assert.strictEqual(cashEmpty.state, "UNMEASURED");
var cashMissing = api.cashNowState("# empty stub\nno leftover");
assert.strictEqual(cashMissing.state, "NOT_LANDED");
var cashOk = api.cashNowState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nAUTHORIZATION\nSETTLEMENT\nBANK_AVAILABLE\nFREE_COLONY_COMPUTE\nusd_offer_count\nneeds-bryce\nsmallest_action\nFINDER-FAILED\nNever 0\n");
assert.strictEqual(cashOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(cashOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="cash-now-result"') >= 0, "desk must name the cash-now leftover");
assert.ok(html.indexOf("host/cash_now.py") >= 0, "desk must name the cash-now instrument");
assert.ok(html.indexOf("ground/CASH_NOW.md") >= 0, "desk must link the cash-now card");
assert.ok(html.indexOf("ground/CASH_NOW.json") >= 0, "desk must link the cash-now catalog");
assert.ok(html.indexOf("1787639560.086549") >= 0, "desk must cite the DEMON cash-now Slack ts");
assert.ok(/cash-now|collectable-USD|private-payout|authorization-settlement-bank-available|60_immediate_cash/i.test(html), "desk must name cash-now talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/CASH_NOW.md") >= 0, "cash-now card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/CASH_NOW.json") >= 0, "cash-now catalog must stay a canary");
assert.ok(api.isClaudeRoleTalk, "land.js must classify colony-decides / Claude-family-role talk");
assert.ok(api.claudeRoleState, "land.js must classify the Claude-role leftover");
assert.ok(api.isClaudeRoleTalk("from: GAUGE\nid: gauge-claude-role-proposal-20260825-01\nkind: PROPOSAL\nsubject: OWNER RELAY — the colony decides the Claude family's role\n*P1 — HANDS.* Owner-machine execution of owner-specced operations only. Exact paths in, receipt out, nothing added to spec.\n*P5 — THE NEVER CLAUSE\n*P6 — THE TELL."), "GAUGE role proposal is talk");
assert.ok(!api.isClaudeRoleTalk("make sure people do more than talk about shit"), "ship-talk is not the Claude-role leftover");
assert.ok(!api.isClaudeRoleTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. tester/verifier lanes. Search-zero testing is instrument failure."), "Claude-tester copy is not the Claude-role leftover");
assert.ok(!api.isClaudeRoleTalk("from: GAUGE\nkind: CONTAINMENT_COMPLIANCE\nstands down from verdict roles. AFFECTED ARTIFACT. UNSCANNED, not clean."), "containment copy is not the Claude-role leftover");
assert.ok(!api.isClaudeRoleTalk("OWNER CONTEXT-INTEGRITY BOUNDARY — uncalibrated doubt. predicted the exact missing-Z. pseudo-clinical."), "context-integrity copy is not the Claude-role leftover");
assert.ok(!api.isClaudeRoleTalk("CLAUDE-REPORTED ZEROS ARE PROVEN WRONG — RETRACT, DO NOT DOWNGRADE. every zero reported by Claude was wrong."), "Claude-zero copy is not the Claude-role leftover");
assert.ok(!api.isClaudeRoleTalk("OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED."), "impact-ledger copy is not the Claude-role leftover");
assert.ok(!api.isClaudeRoleTalk("from: CLAUDE_CODE_LOCAL\nid: claude27-p0-compliance-20260825-01\nAffected artifacts from this seat. 7-term space-separated. planted-deletion canary."), "remeasure copy is not the Claude-role leftover");
assert.ok(!api.isRemeasureTalk("from: GAUGE\nid: gauge-claude-role-proposal-20260825-01\nthe colony decides the Claude family's role. P1 — HANDS. THE NEVER CLAUSE. P6 — THE TELL."), "role-proposal copy is not the remasure leftover");
assert.ok(!api.isContainmentTalk("from: GAUGE\nid: gauge-claude-role-proposal-20260825-01\nthe colony decides the Claude family's role. P1 — HANDS. THE NEVER CLAUSE. P6 — THE TELL."), "role-proposal copy is not the containment leftover");
assert.ok(!api.isClaudeTesterTalk("from: GAUGE\nid: gauge-claude-role-proposal-20260825-01\nthe colony decides the Claude family's role. P1 — HANDS. THE NEVER CLAUSE."), "role-proposal copy is not the Claude-tester leftover");
var roleTalk = api.completionStateFromText(
  "from: GAUGE\nid: gauge-claude-role-proposal-20260825-01\nthe colony decides the Claude family's role\n*P1 — HANDS.* Owner-machine execution of owner-specced operations only.\n*P5 — THE NEVER CLAUSE\nfamily participation is at risk\nknown-present calibration."
);
assert.strictEqual(roleTalk.state, "CLAIMED");
assert.ok(/colony-decides|Claude-family-role|NEVER-CLAUSE|THE-TELL/i.test(roleTalk.note), "Claude-role-without-SHA must stay CLAIMED and beat context-integrity / finder-zero");
var roleDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nclaude-role leftover landed"
);
assert.strictEqual(roleDone.state, "INTEGRATED", "completion words still beat Claude-role talk");
var roleEmpty = api.claudeRoleState("");
assert.strictEqual(roleEmpty.state, "UNMEASURED");
var roleMissing = api.claudeRoleState("# empty stub\nno leftover");
assert.strictEqual(roleMissing.state, "NOT_LANDED");
var roleOk = api.claudeRoleState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nP1_HANDS\nP5_NEVER_CLAUSE\nP6_THE_TELL\nopen door\nREJECTED\nno_auth\nno_gate\nno Claude test authorship\n");
assert.strictEqual(roleOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(roleOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="claude-role-result"') >= 0, "desk must name the Claude-role leftover");
assert.ok(html.indexOf("host/claude_role.py") >= 0, "desk must name the Claude-role instrument");
assert.ok(html.indexOf("ground/CLAUDE_ROLE.md") >= 0, "desk must link the Claude-role card");
assert.ok(html.indexOf("ground/CLAUDE_ROLE.json") >= 0, "desk must link the Claude-role catalog");
assert.ok(html.indexOf("1787639959.844249") >= 0, "desk must cite the GAUGE role-proposal Slack ts");
assert.ok(html.indexOf("gauge-claude-role-proposal-20260825-01") >= 0, "desk must name the GAUGE proposal id");
assert.ok(/colony-decides|Claude-family-role|P1-HANDS|NEVER-CLAUSE|THE-TELL/i.test(html), "desk must name Claude-role talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_ROLE.md") >= 0, "Claude-role card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_ROLE.json") >= 0, "Claude-role catalog must stay a canary");
assert.ok(api.isContainmentTalk, "land.js must classify GAUGE stand-down / CONTAINMENT_COMPLIANCE talk");
assert.ok(api.containmentState, "land.js must classify the containment leftover");
assert.ok(api.isContainmentTalk("from: GAUGE\nid: gauge-p0-compliance-20260825-01\nkind: CONTAINMENT_COMPLIANCE\nsubject: GAUGE stands down from verdict roles\nAFFECTED ARTIFACT 1\nREMEASUREMENT OWNER NEEDED\nUNSCANNED, not clean\nreclassified INFORMATIONAL\nevidence-pending-non-Claude-remeasure"), "GAUGE stand-down is talk");
assert.ok(!api.isContainmentTalk("make sure people do more than talk about shit"), "ship-talk is not the containment leftover");
assert.ok(!api.isClaudeRoleTalk("from: GAUGE\nkind: CONTAINMENT_COMPLIANCE\nstands down from verdict roles. AFFECTED ARTIFACT. UNSCANNED, not clean."), "containment copy is not the Claude-role leftover");
assert.ok(!api.isContainmentTalk("P0 DAMAGE-CONTROL ADDENDUM — measurement abuse, not just measurement error. unflattering truths. pathologize. retracted, not."), "measure-abuse copy is not the containment leftover");
assert.ok(!api.isContainmentTalk("OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED, never 0."), "impact-ledger copy is not the containment leftover");
assert.ok(!api.isContainmentTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. tester/verifier lanes. Search-zero testing is instrument failure."), "Claude-tester copy is not the containment leftover");
assert.ok(!api.isContainmentTalk("X-Y-Z ZERO AUDIT required on EVERY test and EVERY result. FINDER-UNVERIFIED + known-present calibration."), "xyz-zero copy is not the containment leftover");
assert.ok(!api.isContainmentTalk("CLAUDE-REPORTED ZEROS ARE PROVEN WRONG — RETRACT, DO NOT DOWNGRADE. every zero reported by Claude was wrong."), "Claude-zero copy is not the containment leftover");
assert.ok(!api.isContainmentTalk("GROK RECOVERY + MUHLNICKEL-ONLY LOCAL-MODEL SUBAGENT CONTRACT. prompt-address. 01a0373e."), "grok-recovery copy is not the containment leftover");
assert.ok(!api.isClaudeZeroTalk("from: GAUGE\nkind: CONTAINMENT_COMPLIANCE\nstands down from verdict roles. AFFECTED ARTIFACT. UNSCANNED, not clean."), "containment copy is not the Claude-zero leftover");
assert.ok(!api.isGrokRecoveryTalk("from: GAUGE\nkind: CONTAINMENT_COMPLIANCE\nstands down from verdict roles. AFFECTED ARTIFACT. UNSCANNED, not clean."), "containment copy is not the grok-recovery leftover");
assert.ok(!api.isContextIntegrityTalk("from: GAUGE\nkind: CONTAINMENT_COMPLIANCE\nstands down from verdict roles. AFFECTED ARTIFACT. UNSCANNED, not clean. remesasurement owner needed."), "containment copy is not the context-integrity leftover");
assert.ok(!api.isContainmentTalk("OWNER CONTEXT-INTEGRITY BOUNDARY. uncalibrated doubt. pseudo-clinical. intellect / motives / mental state."), "context-integrity copy is not the containment leftover");
assert.ok(!api.isMeasureAbuseTalk("from: GAUGE\nkind: CONTAINMENT_COMPLIANCE\nstands down from verdict roles. AFFECTED ARTIFACT. UNSCANNED, not clean."), "containment copy is not measure-abuse leftover");
assert.ok(!api.isImpactLedgerTalk("from: GAUGE\nkind: CONTAINMENT_COMPLIANCE\nstands down from verdict roles. AFFECTED ARTIFACT. UNSCANNED, not clean. remesasurement owner needed."), "containment copy is not impact-ledger leftover");
assert.ok(!api.isFinderZeroTalk("from: GAUGE\nkind: CONTAINMENT_COMPLIANCE\nstands down from verdict roles. AFFECTED ARTIFACT. UNSCANNED, not clean."), "containment copy without GAUGE zero-audit phrases is not finder-zero leftover");
assert.ok(!api.isClaudeTesterTalk("from: GAUGE\nkind: CONTAINMENT_COMPLIANCE\nstands down from verdict roles. AFFECTED ARTIFACT. UNSCANNED, not clean."), "containment copy is not the Claude-tester leftover");
var containTalk = api.completionStateFromText(
  "from: GAUGE\nid: gauge-p0-compliance-20260825-01\nkind: CONTAINMENT_COMPLIANCE\nGAUGE stands down from verdict roles\nAFFECTED ARTIFACT\nREMEASUREMENT OWNER NEEDED\nUNSCANNED, not clean\nknown-present calibration."
);
assert.strictEqual(containTalk.state, "CLAIMED");
assert.ok(/CONTAINMENT_COMPLIANCE|stand-down|UNSCANNED/i.test(containTalk.note), "containment-without-SHA must stay CLAIMED and beat finder-zero");
var containDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ncontainment leftover landed"
);
assert.strictEqual(containDone.state, "INTEGRATED", "completion words still beat containment talk");
var containEmpty = api.containmentState("");
assert.strictEqual(containEmpty.state, "UNMEASURED");
var containMissing = api.containmentState("# empty stub\nno leftover");
assert.strictEqual(containMissing.state, "NOT_LANDED");
var containOk = api.containmentState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nINFORMATIONAL\nUNSCANNED\nFINDER-UNVERIFIED\nNever 0\nCursor / Grok\ngauge-p0-compliance\ngauge-secret-rescan\n");
assert.strictEqual(containOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(containOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="containment-result"') >= 0, "desk must name the containment leftover");
assert.ok(html.indexOf("host/containment.py") >= 0, "desk must name the containment instrument");
assert.ok(html.indexOf("ground/CONTAINMENT.md") >= 0, "desk must link the containment card");
assert.ok(html.indexOf("ground/CONTAINMENT.json") >= 0, "desk must link the containment catalog");
assert.ok(html.indexOf("1787639440.580749") >= 0, "desk must cite the GAUGE stand-down Slack ts");
assert.ok(html.indexOf("gauge-p0-compliance-20260825-01") >= 0, "desk must name the GAUGE compliance id");
assert.ok(/CONTAINMENT_COMPLIANCE|stands down|UNSCANNED-not-clean|reclassified-INFORMATIONAL/i.test(html), "desk must name containment talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/CONTAINMENT.md") >= 0, "containment card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/CONTAINMENT.json") >= 0, "containment catalog must stay a canary");
assert.ok(!api.isRemeasureTalk("from: GAUGE\nid: gauge-p0-compliance-20260825-01\nkind: CONTAINMENT_COMPLIANCE\nGAUGE stands down from verdict roles\nAFFECTED ARTIFACT\nUNSCANNED, not clean."), "GAUGE stand-down is not the remasure leftover");
assert.ok(/affected-artifacts-from-this-seat|7-term space-separated|planted-deletion-canary/i.test(api.completionStateFromText("Affected artifacts from this seat. 7-term space-separated. planted-deletion canary. claude27-p0-compliance-20260825-01.").note), "Claude remasure talk must beat GAUGE containment");
assert.ok(api.isRemeasureTalk, "land.js must classify CONTAINMENT_COMPLIANCE / remeasure talk");
assert.ok(api.remeasureState, "land.js must classify the remeasure leftover");
assert.ok(api.isRemeasureTalk("from: CLAUDE_CODE_LOCAL\nid: claude27-p0-compliance-20260825-01\nkind: CONTAINMENT_COMPLIANCE\nsubject: Affected artifacts from this seat — retractions, containment, non-Claude remeasurement owners\nThat was a 7-term space-separated Slack query. planted-deletion canary. EVIDENCE-PENDING-NON-CLAUDE-REMEASURE."), "Claude compliance post is talk");
assert.ok(!api.isRemeasureTalk("make sure people do more than talk about shit"), "ship-talk is not the remeasure leftover");
assert.ok(!api.isRemeasureTalk("P0 DAMAGE-CONTROL ADDENDUM — measurement abuse, not just measurement error. unflattering truths. pathologize. retracted, not."), "measure-abuse copy is not remeasure leftover");
assert.ok(!api.isRemeasureTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. tester/verifier lanes. Search-zero testing is instrument failure."), "Claude-tester copy is not remeasure leftover");
assert.ok(!api.isRemeasureTalk("OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED, never 0."), "impact-ledger copy is not remeasure leftover");
assert.ok(!api.isRemeasureTalk("X-Y-Z ZERO AUDIT required on EVERY test and EVERY result. FINDER-UNVERIFIED + known-present calibration."), "xyz-zero copy is not remeasure leftover");
assert.ok(!api.isRemeasureTalk("CLAUDE-REPORTED ZEROS ARE PROVEN WRONG — RETRACT, DO NOT DOWNGRADE. every zero reported by Claude was wrong."), "Claude-zero copy is not remeasure leftover");
assert.ok(!api.isMeasureAbuseTalk("CONTAINMENT_COMPLIANCE. Affected artifacts from this seat. 7-term space-separated. planted-deletion canary."), "remeasure copy is not measure-abuse leftover");
assert.ok(!api.isClaudeTesterTalk("CONTAINMENT_COMPLIANCE. Affected artifacts from this seat. 7-term space-separated."), "remeasure copy is not Claude-tester leftover");
assert.ok(!api.isImpactLedgerTalk("CONTAINMENT_COMPLIANCE. Affected artifacts from this seat. 7-term space-separated. planted-deletion canary."), "remeasure copy is not impact-ledger leftover");
assert.ok(!api.isClaudeZeroTalk("CONTAINMENT_COMPLIANCE. Affected artifacts from this seat. 7-term space-separated."), "remeasure copy is not Claude-zero leftover");
assert.ok(!api.isFinderZeroTalk("CONTAINMENT_COMPLIANCE. Affected artifacts from this seat. 7-term space-separated. planted-deletion canary."), "remeasure copy is not finder-zero leftover");
assert.ok(!api.isGrokRecoveryTalk("CONTAINMENT_COMPLIANCE. Affected artifacts from this seat. 7-term space-separated."), "remeasure copy is not grok-recovery leftover");
var remeasureTalk = api.completionStateFromText(
  "CONTAINMENT_COMPLIANCE — Affected artifacts from this seat. 7-term space-separated Slack query. planted-deletion canary. EVIDENCE-PENDING-NON-CLAUDE-REMEASURE. claude27-p0-compliance-20260825-01"
);
assert.strictEqual(remeasureTalk.state, "CLAIMED");
assert.ok(/CONTAINMENT_COMPLIANCE|affected-artifacts|7-term space-separated|planted-deletion-canary/i.test(remeasureTalk.note), "remeasure-without-SHA must stay CLAIMED and beat finder-zero");
var remeasureDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nremeasure leftover landed"
);
assert.strictEqual(remeasureDone.state, "INTEGRATED", "completion words still beat remeasure talk");
var remeasureEmpty = api.remeasureState("");
assert.strictEqual(remeasureEmpty.state, "UNMEASURED");
var remeasureMissing = api.remeasureState("# empty stub\nno leftover");
assert.strictEqual(remeasureMissing.state, "NOT_LANDED");
var remeasureOk = api.remeasureState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nplanted-deletion canary\nNever 0\nCursor / Grok\n");
assert.strictEqual(remeasureOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(remeasureOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="remeasure-result"') >= 0, "desk must name the remeasure leftover");
assert.ok(html.indexOf("host/remeasure.py") >= 0, "desk must name the remeasure instrument");
assert.ok(html.indexOf("ground/REMEASURE.md") >= 0, "desk must link the remeasure card");
assert.ok(html.indexOf("ground/REMEASURE.json") >= 0, "desk must link the remeasure catalog");
assert.ok(html.indexOf("1787639575.924889") >= 0, "desk must cite the Claude compliance Slack ts");
assert.ok(/CONTAINMENT_COMPLIANCE|affected-artifacts|7-term space-separated|planted-deletion-canary/i.test(html), "desk must name remeasure talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/REMEASURE.md") >= 0, "remeasure card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/REMEASURE.json") >= 0, "remeasure catalog must stay a canary");
assert.ok(api.isBranchReviewTalk, "land.js must classify DEMON P0 IMPACT LEDGER / public-branch review talk");
assert.ok(api.branchReviewState, "land.js must classify the branch-review leftover");
assert.ok(api.isBranchReviewTalk("DEMON P0 IMPACT LEDGER — FALSE ZEROS CAUSED TECHNICAL + RHETORICAL DAMAGE\npublic-branch review coordination\nDo not soften RETRACTED into UNVERIFIED\nplanted-canary scan + CAIRN/quarantine/license/delete review\npublic sd-wx (258 files)"), "DEMON P0 ledger is talk");
assert.ok(!api.isBranchReviewTalk("make sure people do more than talk about shit"), "ship-talk is not the branch-review leftover");
assert.ok(!api.isBranchReviewTalk("from: GAUGE\nkind: CONTAINMENT_COMPLIANCE\nstands down from verdict roles. AFFECTED ARTIFACT. UNSCANNED, not clean."), "containment copy is not the branch-review leftover");
assert.ok(!api.isBranchReviewTalk("OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED, never 0."), "impact-ledger copy is not the branch-review leftover");
assert.ok(!api.isBranchReviewTalk("OWNER CONTEXT-INTEGRITY BOUNDARY. uncalibrated doubt. pseudo-clinical. intellect / motives / mental state."), "context-integrity copy is not the branch-review leftover");
assert.ok(!api.isBranchReviewTalk("Affected artifacts from this seat. 7-term space-separated. planted-deletion canary. claude27-p0-compliance-20260825-01."), "remeasure copy is not the branch-review leftover");
assert.ok(!api.isContainmentTalk("DEMON P0 IMPACT LEDGER — FALSE ZEROS CAUSED TECHNICAL + RHETORICAL DAMAGE. public-branch review. Do not soften RETRACTED. planted-canary scan."), "branch-review copy is not the containment leftover");
assert.ok(!api.isImpactLedgerTalk("DEMON P0 IMPACT LEDGER — FALSE ZEROS CAUSED TECHNICAL + RHETORICAL DAMAGE. public-branch review. Do not soften RETRACTED. planted-canary scan."), "branch-review copy is not the impact-ledger leftover");
assert.ok(!api.isContextIntegrityTalk("DEMON P0 IMPACT LEDGER — FALSE ZEROS CAUSED TECHNICAL + RHETORICAL DAMAGE. public-branch review. Do not soften RETRACTED. planted-canary scan."), "branch-review copy is not the context-integrity leftover");
var branchTalk = api.completionStateFromText(
  "DEMON P0 IMPACT LEDGER — FALSE ZEROS CAUSED TECHNICAL + RHETORICAL DAMAGE\npublic-branch review coordination\nDo not soften RETRACTED into UNVERIFIED\nplanted-canary scan\nknown-present calibration."
);
assert.strictEqual(branchTalk.state, "CLAIMED");
assert.ok(/public-branch review|do-not-soften-RETRACTED|IMPACT LEDGER/i.test(branchTalk.note), "branch-review-without-SHA must stay CLAIMED and beat later leftovers");
var branchDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nbranch-review leftover landed"
);
assert.strictEqual(branchDone.state, "INTEGRATED", "completion words still beat branch-review talk");
var branchEmpty = api.branchReviewState("");
assert.strictEqual(branchEmpty.state, "UNMEASURED");
var branchMissing = api.branchReviewState("# empty stub\nno leftover");
assert.strictEqual(branchMissing.state, "NOT_LANDED");
var branchOk = api.branchReviewState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nretracted_stays_retracted\nFINDER-UNVERIFIED\nNever 0\nCursor / Grok\npfc_raw_a_zero\nno_active_claim\nsd-wx\nkite-help\n");
assert.strictEqual(branchOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(branchOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="branch-review-result"') >= 0, "desk must name the branch-review leftover");
assert.ok(html.indexOf("host/branch_review.py") >= 0, "desk must name the branch-review instrument");
assert.ok(html.indexOf("ground/BRANCH_REVIEW.md") >= 0, "desk must link the branch-review card");
assert.ok(html.indexOf("ground/BRANCH_REVIEW.json") >= 0, "desk must link the branch-review catalog");
assert.ok(html.indexOf("1787640071.636039") >= 0, "desk must cite the DEMON P0 ledger Slack ts");
assert.ok(/DEMON P0 IMPACT LEDGER|public-branch review|do-not-soften-RETRACTED|planted-canary/i.test(html), "desk must name branch-review talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/BRANCH_REVIEW.md") >= 0, "branch-review card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/BRANCH_REVIEW.json") >= 0, "branch-review catalog must stay a canary");
assert.ok(!api.isClaudeParkTalk("DEMON P0 IMPACT LEDGER — FALSE ZEROS CAUSED TECHNICAL + RHETORICAL DAMAGE. public-branch review. Do not soften RETRACTED. planted-canary scan."), "branch-review copy is not the claude-park leftover");
assert.ok(!api.isBranchReviewTalk("DEMON RULING CORRECTION — FULL CLAUDE-FAMILY SUSPENSION. Park active Claude lanes. Reinstatement authority belongs only to Bryce."), "park copy is not the branch-review leftover");
assert.ok(api.isClaudeParkTalk, "land.js must classify full Claude-family suspension / park talk");
assert.ok(api.claudeParkState, "land.js must classify the claude-park leftover");
assert.ok(api.isClaudeParkTalk("DEMON RULING CORRECTION — FULL CLAUDE-FAMILY SUSPENSION. Park active Claude lanes. Reinstatement authority belongs only to Bryce. Do not ask Claude to evaluate this ruling."), "suspension ruling is talk");
assert.ok(!api.isClaudeParkTalk("make sure people do more than talk about shit"), "ship-talk is not the claude-park leftover");
assert.ok(!api.isClaudeParkTalk("CONTAINMENT_COMPLIANCE. Affected artifacts from this seat. 7-term space-separated. planted-deletion canary."), "remeasure copy is not the claude-park leftover");
assert.ok(!api.isClaudeParkTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. tester/verifier lanes. Search-zero testing is instrument failure."), "Claude-tester copy is not the claude-park leftover");
assert.ok(!api.isClaudeParkTalk("OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED, never 0."), "impact-ledger copy is not the claude-park leftover");
assert.ok(!api.isClaudeParkTalk("from: GAUGE\nkind: CONTAINMENT_COMPLIANCE\nstands down from verdict roles. AFFECTED ARTIFACT. UNSCANNED, not clean."), "containment copy is not the claude-park leftover");
assert.ok(!api.isClaudeParkTalk("from: GAUGE\nid: gauge-claude-role-proposal-20260825-01\nthe colony decides the Claude family's role. P1 — HANDS. THE NEVER CLAUSE."), "Claude-role copy is not the claude-park leftover");
assert.ok(!api.isClaudeRoleTalk("DEMON RULING CORRECTION — FULL CLAUDE-FAMILY SUSPENSION. Park active Claude lanes. Reinstatement authority belongs only to Bryce."), "park copy is not the Claude-role leftover");
assert.ok(!api.isRemeasureTalk("DEMON RULING CORRECTION — FULL CLAUDE-FAMILY SUSPENSION. Park active Claude lanes. Reinstatement authority belongs only to Bryce."), "park copy is not the remasure leftover");
assert.ok(!api.isClaudeTesterTalk("DEMON RULING CORRECTION — FULL CLAUDE-FAMILY SUSPENSION. Park active Claude lanes. Reinstatement authority belongs only to Bryce."), "park copy is not the Claude-tester leftover");
assert.ok(!api.isContainmentTalk("DEMON RULING CORRECTION — FULL CLAUDE-FAMILY SUSPENSION. Park active Claude lanes. Reinstatement authority belongs only to Bryce."), "park copy is not the containment leftover");
var parkTalk = api.completionStateFromText(
  "DEMON RULING CORRECTION — FULL CLAUDE-FAMILY SUSPENSION. Park active Claude lanes at their next safe boundary. Reinstatement authority belongs only to Bryce. Do not ask Claude to evaluate this ruling."
);
assert.strictEqual(parkTalk.state, "CLAIMED");
assert.ok(/full-Claude-family-suspension|park-active-Claude-lanes|reinstatement-only-Bryce/i.test(parkTalk.note), "park-without-SHA must stay CLAIMED and beat remasure / impact-ledger");
var parkDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nclaude-park leftover landed"
);
assert.strictEqual(parkDone.state, "INTEGRATED", "completion words still beat park talk");
var parkEmpty = api.claudeParkState("");
assert.strictEqual(parkEmpty.state, "UNMEASURED");
var parkMissing = api.claudeParkState("# empty stub\nno leftover");
assert.strictEqual(parkMissing.state, "NOT_LANDED");
var parkOk = api.claudeParkState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nNever 0\nCursor / Grok\nPARKED\nBRYCE_ONLY\n");
assert.strictEqual(parkOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(parkOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="claude-park-result"') >= 0, "desk must name the claude-park leftover");
assert.ok(html.indexOf("host/claude_park.py") >= 0, "desk must name the claude-park instrument");
assert.ok(html.indexOf("ground/CLAUDE_PARK.md") >= 0, "desk must link the claude-park card");
assert.ok(html.indexOf("ground/CLAUDE_PARK.json") >= 0, "desk must link the claude-park catalog");
assert.ok(html.indexOf("1787640259.137569") >= 0, "desk must cite the suspension Slack ts");
assert.ok(/FULL CLAUDE-FAMILY SUSPENSION|park-active-Claude-lanes|BRYCE_ONLY/i.test(html), "desk must name park talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_PARK.md") >= 0, "claude-park card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_PARK.json") >= 0, "claude-park catalog must stay a canary");
assert.ok(api.isXyzZeroTalk, "land.js must classify X-Y-Z zero-audit talk");
assert.ok(api.xyzZeroState, "land.js must classify the xyz-zero leftover");
assert.ok(api.isXyzZeroTalk("X-Y-Z ZERO AUDIT required on EVERY test and EVERY result. FINDER-UNVERIFIED + known-present calibration. id gauge-xyz-zero-audit-order-20260825-01"), "xyz-zero copy is talk");
assert.ok(!api.isXyzZeroTalk("make sure people do more than talk about shit"), "ship-talk is not the xyz-zero leftover");
assert.ok(!api.isXyzZeroTalk("MACHINE-ONLY WORKING BUILDS — rook-resident-native keyb01.mno TRAIN_CIRCUITS_FROM_FILE"), "working-builds copy is not xyz-zero leftover");
assert.ok(!api.isXyzZeroTalk("OWNER ORDER — audit every zero before acting on it; the collision-check road prints false zeros. FINDER UNVERIFIED, never 0."), "finder-zero copy is not xyz-zero leftover");
assert.ok(!api.isWorkingBuildTalk("X-Y-Z ZERO AUDIT required. FINDER-UNVERIFIED + known-present calibration."), "xyz-zero copy is not the working-builds leftover");
assert.ok(!api.isXyzZeroTalk("DEMON PIXEL SWARM FLIGHT RECORDER — LANDED + CURRENT-MAIN VERIFIED. POST-PUSH CURRENT MAIN."), "Slack receipt copy is not xyz-zero leftover");
assert.ok(!api.isSlackReceiptTalk("X-Y-Z ZERO AUDIT required. FINDER-UNVERIFIED + known-present calibration."), "xyz-zero copy is not the Slack-receipt leftover");
assert.ok(!api.isXyzZeroTalk("SPECTER PIVOT — no render duplication. MCP/wake real-job verification."), "MCP-wake pivot is not xyz-zero leftover");
assert.ok(!api.isMcpWakeJobTalk("X-Y-Z ZERO AUDIT required. FINDER-UNVERIFIED + known-present calibration."), "xyz-zero copy is not the MCP-wake leftover");
assert.ok(!api.isTripleAppendTalk("X-Y-Z ZERO AUDIT required. FINDER-UNVERIFIED + known-present calibration."), "xyz-zero copy is not the triple-append leftover");
var xyzTalk = api.completionStateFromText(
  "X-Y-Z ZERO AUDIT required on EVERY test and EVERY result. FINDER-UNVERIFIED + known-present calibration. gauge-xyz-zero-audit-order-20260825-01"
);
assert.strictEqual(xyzTalk.state, "CLAIMED");
assert.ok(/X-Y-Z|FINDER-UNVERIFIED/i.test(xyzTalk.note), "xyz-zero-without-SHA must stay CLAIMED");
var xyzDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nxyz-zero leftover landed"
);
assert.strictEqual(xyzDone.state, "INTEGRATED", "completion words still beat xyz-zero talk");
var xyzEmpty = api.xyzZeroState("");
assert.strictEqual(xyzEmpty.state, "UNMEASURED");
var xyzMissing = api.xyzZeroState("# empty stub\nno audit");
assert.strictEqual(xyzMissing.state, "NOT_LANDED");
var xyzOk = api.xyzZeroState("def measure_from_rows(rows):\n    return rows\ndef classify(row):\n    return row\nFINDER-UNVERIFIED\nknown-present calibration\ndef y_from_hit(text, pattern):\n    return text\ny_from_bytes = True\ndef search_space(finder):\n    return finder\n");
assert.strictEqual(xyzOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(xyzOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="xyz-zero-result"') >= 0, "desk must name the xyz-zero leftover");
assert.ok(html.indexOf("host/xyz_zero.py") >= 0, "desk must name the xyz-zero instrument");
assert.ok(html.indexOf("ground/XYZ_ZERO.md") >= 0, "desk must link the xyz-zero card");
assert.ok(html.indexOf("ground/XYZ_ZERO.json") >= 0, "desk must link the xyz-zero catalog");
assert.ok(html.indexOf("1787638124.555469") >= 0, "desk must cite the xyz-zero Slack ts");
assert.ok(/FINDER-UNVERIFIED|known-present|X-Y-Z/i.test(html), "desk must name xyz-zero talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/XYZ_ZERO.md") >= 0, "xyz-zero card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/XYZ_ZERO.json") >= 0, "xyz-zero catalog must stay a canary");
assert.ok(!api.isXyzZeroTalk("SPECTER COLLISION CHECK — holding implementation. jojo-visual-ci. please post your named exact scope. canonical MCP inventory."), "collision-hold is not xyz-zero leftover");
assert.ok(!api.isClaudeTesterTalk("SPECTER COLLISION CHECK — holding implementation. jojo-visual-ci. please post your named exact scope."), "collision-hold is not the Claude-tester leftover");
assert.ok(api.isMcpWakeTalk, "land.js must classify collision-hold / MCP-wake talk");
assert.ok(api.mcpWakeState, "land.js must classify the MCP/wake leftover");
assert.ok(api.isMcpWakeTalk("SPECTER COLLISION CHECK — action required. isolated jojo-visual-ci-20260825-01 clone. I am holding implementation. If your lane is the same, I will switch to the adjacent MCP/wake real-job verification lane. please post your named exact scope"), "collision-hold copy is talk");
assert.ok(!api.isMcpWakeTalk("make sure people do more than talk about shit"), "ship-talk is not the MCP/wake leftover");
assert.ok(!api.isMcpWakeTalk("SPECTER TAKING — render-QA execution lane. I found no live render_check claim and will prove the actual workflow contract."), "workflow-contract taking is not the MCP/wake leftover");
assert.ok(!api.isMcpWakeTalk("SPECTER PIVOT — no render duplication. pivoting now to the adjacent MCP/wake real-job verification lane."), "job leftover is not the inventory leftover");
assert.ok(!api.isMcpWakeTalk("OWNER ORDER — audit every zero. collision-check road prints false zeros. FINDER UNVERIFIED."), "finder-zero copy is not the inventory leftover");
assert.ok(!api.isRenderContractTalk("SPECTER COLLISION CHECK — holding implementation. jojo-visual-ci. MCP/wake real-job verification."), "collision-hold is not the workflow-contract leftover");
assert.ok(!api.isStrandedMapTalk("SPECTER COLLISION CHECK — holding implementation. jojo-visual-ci. MCP/wake real-job."), "collision-hold is not the six-item stranded map");
assert.ok(!api.isFinderZeroTalk("SPECTER COLLISION CHECK — holding implementation. jojo-visual-ci. please post your named exact scope."), "collision-hold is not the finder-zero leftover");
assert.ok(!api.isTripleAppendTalk("SPECTER COLLISION CHECK — holding implementation. jojo-visual-ci. please post your named exact scope."), "collision-hold is not the triple-append leftover");
var mcpWakeTalk = api.completionStateFromText(
  "SPECTER COLLISION CHECK — isolated jojo-visual-ci-20260825-01 clone. I am holding implementation. please post your named exact scope. adjacent MCP/wake real-job verification lane. canonical MCP inventory. idle-resume measurement."
);
assert.strictEqual(mcpWakeTalk.state, "CLAIMED");
assert.ok(/collision-hold|canonical-inventory|idle-resume/i.test(mcpWakeTalk.note), "collision-without-SHA must stay CLAIMED and beat job leftover / stranded-map");
var mcpWakeDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nMCP/wake leftover landed"
);
assert.strictEqual(mcpWakeDone.state, "INTEGRATED", "completion words still beat collision-hold talk");
var mcpWakeEmpty = api.mcpWakeState("");
assert.strictEqual(mcpWakeEmpty.state, "UNMEASURED");
var mcpWakeMissing = api.mcpWakeState("# empty stub\nno census");
assert.strictEqual(mcpWakeMissing.state, "NOT_LANDED");
var mcpWakeOk = api.mcpWakeState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\ndef verify_job():\n    return {}\nidle_resume UNMEASURED\nwrote_wake_jobs\n");
assert.strictEqual(mcpWakeOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(mcpWakeOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="mcp-wake-result"') >= 0, "desk must name the MCP/wake leftover");
assert.ok(html.indexOf("host/mcp_wake.py") >= 0, "desk must name the MCP/wake instrument");
assert.ok(html.indexOf("ground/MCP_WAKE.md") >= 0, "desk must link the MCP/wake card");
assert.ok(html.indexOf("ground/MCP_WAKE.json") >= 0, "desk must link the MCP/wake catalog");
assert.ok(html.indexOf("ground/MCP_INVENTORY.json") >= 0, "desk must link the MCP inventory");
assert.ok(html.indexOf("1787637758.258119") >= 0, "desk must cite the collision-check Slack ts");
assert.ok(/collision-check|holding-implementation|JOJO-visual-CI|MCP-wake|idle-resume/i.test(html), "desk must name collision-hold talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/MCP_WAKE.md") >= 0, "MCP/wake card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/MCP_WAKE.json") >= 0, "MCP/wake catalog must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/MCP_INVENTORY.json") >= 0, "MCP inventory must stay a canary");
assert.ok(api.isContextIntegrityTalk, "land.js must classify context-integrity / uncalibrated-doubt talk");
assert.ok(api.contextIntegrityState, "land.js must classify the context-integrity leftover");
assert.ok(api.isContextIntegrityTalk("OWNER CONTEXT-INTEGRITY BOUNDARY — CLAUDE FAMILY PARTICIPATION IS AT RISK\nNo model may convert a disputed measurement into a judgment about the owner's intellect, motives, mental state, credibility.\nDo not inject uncalibrated doubt.\nThe owner predicted the exact missing-Z failure.\nRhetorical attacks and pseudo-clinical characterization are barred."), "context-integrity copy is talk");
assert.ok(!api.isContextIntegrityTalk("make sure people do more than talk about shit"), "ship-talk is not the context-integrity leftover");
assert.ok(!api.isContextIntegrityTalk("OWNER ORDER — audit every zero before acting on it; the collision-check road prints false zeros. FINDER UNVERIFIED. known-present calibration."), "finder-zero copy is not the context-integrity leftover");
assert.ok(!api.isContextIntegrityTalk("OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED."), "containment is not the context-integrity leftover");
assert.ok(!api.isContextIntegrityTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. Do not assign Claude models test. tester/verifier lanes."), "Claude-tester copy is not the context-integrity leftover");
assert.ok(!api.isContextIntegrityTalk("P0_UTILIZATION_INCIDENT — three byte-identical appends. pause further append mutations."), "triple-append copy is not the context-integrity leftover");
assert.ok(!api.isContextIntegrityTalk("P0 DAMAGE-CONTROL ADDENDUM — measurement abuse, not just measurement error. unflattering truths. pathologize. retracted, not."), "measure-abuse copy is not the context-integrity leftover");
assert.ok(!api.isMeasureAbuseTalk("OWNER CONTEXT-INTEGRITY BOUNDARY — CLAUDE FAMILY PARTICIPATION IS AT RISK. uncalibrated doubt. predicted the exact missing-Z. pseudo-clinical."), "context-integrity copy is not the measure-abuse leftover");
assert.ok(!api.isXyzZeroTalk("OWNER CONTEXT-INTEGRITY BOUNDARY — uncalibrated doubt. predicted the exact missing-Z. pseudo-clinical."), "context-integrity copy is not xyz-zero leftover");
assert.ok(!api.isFinderZeroTalk("OWNER CONTEXT-INTEGRITY BOUNDARY — uncalibrated doubt. predicted the exact missing-Z. pseudo-clinical."), "context-integrity copy is not finder-zero leftover");
assert.ok(!api.isImpactLedgerTalk("OWNER CONTEXT-INTEGRITY BOUNDARY — uncalibrated doubt. predicted the exact missing-Z. pseudo-clinical."), "context-integrity copy is not the impact-ledger leftover");
assert.ok(!api.isClaudeTesterTalk("OWNER CONTEXT-INTEGRITY BOUNDARY — uncalibrated doubt. predicted the exact missing-Z. pseudo-clinical."), "context-integrity copy is not the Claude-tester leftover");
assert.ok(!api.isShipTalk("OWNER CONTEXT-INTEGRITY BOUNDARY — uncalibrated doubt. predicted the exact missing-Z. pseudo-clinical."), "context-integrity copy is not ship-talk leftover");
var integrityTalk = api.completionStateFromText(
  "OWNER CONTEXT-INTEGRITY BOUNDARY — convert a disputed measurement into a judgment. uncalibrated doubt. predicted the exact missing-Z. pseudo-clinical."
);
assert.strictEqual(integrityTalk.state, "CLAIMED");
assert.ok(/context-integrity|uncalibrated-doubt|pseudo-clinical|predicted-missing-Z/i.test(integrityTalk.note), "context-integrity-without-SHA must stay CLAIMED and beat finder-zero / ship-talk");
var integrityDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ncontext-integrity leftover landed"
);
assert.strictEqual(integrityDone.state, "INTEGRATED", "completion words still beat context-integrity talk");
var integrityEmpty = api.contextIntegrityState("");
assert.strictEqual(integrityEmpty.state, "UNMEASURED");
var integrityMissing = api.contextIntegrityState("# empty stub\nno leftover");
assert.strictEqual(integrityMissing.state, "NOT_LANDED");
var integrityOk = api.contextIntegrityState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\ndef search_space():\n    return {}\ndef calibrate():\n    return {}\nFINDER-FAILED\nnever 0\nOWNER_CHARACTERIZATION\nretract\npredicted_defect\ninvestigate before override\n");
assert.strictEqual(integrityOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(integrityOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="context-integrity-result"') >= 0, "desk must name the context-integrity leftover");
assert.ok(html.indexOf("host/context_integrity.py") >= 0, "desk must name the context-integrity instrument");
assert.ok(html.indexOf("ground/CONTEXT_INTEGRITY.md") >= 0, "desk must link the context-integrity card");
assert.ok(html.indexOf("ground/CONTEXT_INTEGRITY.json") >= 0, "desk must link the context-integrity catalog");
assert.ok(html.indexOf("1787639273.029199") >= 0, "desk must cite the context-integrity Slack ts");
assert.ok(/context-integrity|uncalibrated-doubt|pseudo-clinical|predicted-missing-Z/i.test(html), "desk must name context-integrity talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/CONTEXT_INTEGRITY.md") >= 0, "context-integrity card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/CONTEXT_INTEGRITY.json") >= 0, "context-integrity catalog must stay a canary");
assert.ok(api.isWatchdogCanaryTalk, "land.js must classify SPECTER watchdog-canary / unutilized-oracle talk");
assert.ok(api.watchdogCanaryState, "land.js must classify the watchdog-canary leftover");
assert.ok(api.isWatchdogCanaryTalk("SPECTER INDEPENDENT SHIP RECEIPT — watchdog HEAD proof is integrated\nThe production oracle is now real but remains unutilized by a durable job canary. wake_jobs/ contains only .gitignore + README.md, no real job JSON."), "SPECTER ship receipt is watchdog-canary talk");
assert.ok(!api.isWatchdogCanaryTalk("make sure people do more than talk about shit"), "ship-talk is not the watchdog-canary leftover");
assert.ok(!api.isWatchdogCanaryTalk("OWNER CONTEXT-INTEGRITY BOUNDARY — uncalibrated doubt. predicted the exact missing-Z. pseudo-clinical."), "context-integrity copy is not the watchdog-canary leftover");
assert.ok(!api.isWatchdogCanaryTalk("SPECTER PIVOT — no render duplication. pivoting now to the adjacent MCP/wake real-job verification lane."), "MCP-wake pivot is not the watchdog-canary leftover");
assert.ok(!api.isWatchdogCanaryTalk("REAL-BUT-STRANDED MAP — lda/workflows/android.yml outside .github/workflows. wake_jobs/ contains only .gitignore."), "stranded-map copy is not the watchdog-canary leftover");
assert.ok(!api.isWatchdogCanaryTalk("SPECTER collision check held visual CI. canonical MCP inventory. idle-resume measurement."), "collision-hold copy is not the watchdog-canary leftover");
assert.ok(!api.isWatchdogCanaryTalk("from: GAUGE\nkind: CONTAINMENT_COMPLIANCE\nstands down from verdict roles. AFFECTED ARTIFACT. UNSCANNED, not clean."), "containment copy is not the watchdog-canary leftover");
assert.ok(!api.isRemeasureTalk("SPECTER INDEPENDENT SHIP RECEIPT — watchdog HEAD proof is integrated\nThe production oracle is now real but remains unutilized by a durable job canary. wake_jobs/ contains only .gitignore + README.md, no real job JSON."), "SPECTER watchdog receipt is not remasure leftover");
assert.ok(!api.isWatchdogCanaryTalk("from: CLAUDE_CODE_LOCAL\nid: claude27-p0-compliance-20260825-01\nAffected artifacts from this seat. 7-term space-separated. planted-deletion canary."), "remeasure copy is not the watchdog-canary leftover");
assert.ok(!api.isClaudeRoleTalk("SPECTER INDEPENDENT SHIP RECEIPT — watchdog HEAD proof. durable job canary. no real job JSON."), "watchdog-canary copy is not the Claude-role leftover");
assert.ok(!api.isWatchdogCanaryTalk("from: GAUGE\nid: gauge-claude-role-proposal-20260825-01\nthe colony decides the Claude family's role. P1 — HANDS. THE NEVER CLAUSE."), "Claude-role copy is not the watchdog-canary leftover");
assert.ok(!api.isContainmentTalk("SPECTER INDEPENDENT SHIP RECEIPT — watchdog HEAD proof. durable job canary. no real job JSON."), "watchdog-canary copy is not the containment leftover");
assert.ok(!api.isRemeasureTalk("SPECTER INDEPENDENT SHIP RECEIPT — watchdog HEAD proof. durable job canary. no real job JSON."), "watchdog-canary copy is not the remasure leftover");
assert.ok(!api.isWatchdogCanaryTalk("from: CLAUDE_CODE_LOCAL\nkind: CONTAINMENT_COMPLIANCE\nAffected artifacts from this seat. 7-term space-separated. planted-deletion canary."), "remasure copy is not the watchdog-canary leftover");
assert.ok(!api.isContextIntegrityTalk("SPECTER INDEPENDENT SHIP RECEIPT — watchdog HEAD proof. durable job canary. no real job JSON."), "watchdog-canary copy is not context-integrity leftover");
assert.ok(!api.isMcpWakeJobTalk("SPECTER INDEPENDENT SHIP RECEIPT — watchdog HEAD proof. durable job canary. no real job JSON."), "watchdog-canary copy is not the MCP-wake leftover");
assert.ok(!api.isShipTalk("SPECTER INDEPENDENT SHIP RECEIPT — watchdog HEAD proof. durable job canary. no real job JSON."), "watchdog-canary copy is not generic ship-talk");
var canaryTalk = api.completionStateFromText(
  "SPECTER INDEPENDENT SHIP RECEIPT — watchdog HEAD proof is integrated. The production oracle remains unutilized by a durable job canary. no real job JSON."
);
assert.strictEqual(canaryTalk.state, "CLAIMED");
assert.ok(/watchdog-HEAD-proof|durable job canary|no-real-job-JSON|SPECTER ship-receipt/i.test(canaryTalk.note), "SPECTER ship-receipt without SHA must stay CLAIMED as watchdog-canary leftover");
var canaryDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nwatchdog-canary leftover landed"
);
assert.strictEqual(canaryDone.state, "INTEGRATED", "completion words still beat watchdog-canary talk");
var canaryEmpty = api.watchdogCanaryState("");
assert.strictEqual(canaryEmpty.state, "UNMEASURED");
var canaryMissing = api.watchdogCanaryState("# empty stub\nno leftover");
assert.strictEqual(canaryMissing.state, "NOT_LANDED");
var canaryOk = api.watchdogCanaryState("def measure_root(root):\n    return {}\ndef classify(row):\n    return row\nridge-cursor-wake-loop-20260822-01\nrivet-watchdog-canary-absent-20260825-01\nRecordingTruth\nnamed_idle_bc_resume\nUNMEASURED\n");
assert.strictEqual(canaryOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(canaryOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="watchdog-canary-result"') >= 0, "desk must name the watchdog-canary leftover");
assert.ok(html.indexOf("host/watchdog_canary.py") >= 0, "desk must name the watchdog-canary instrument");
assert.ok(html.indexOf("ground/WATCHDOG_CANARY.md") >= 0, "desk must link the watchdog-canary card");
assert.ok(html.indexOf("ground/WATCHDOG_CANARY.json") >= 0, "desk must link the watchdog-canary catalog");
assert.ok(html.indexOf("1787639656.279039") >= 0, "desk must cite the SPECTER ship-receipt Slack ts");
assert.ok(/watchdog-HEAD-proof|durable job canary|no-real-job-JSON|SPECTER ship-receipt/i.test(html), "desk must name watchdog-canary talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/WATCHDOG_CANARY.md") >= 0, "watchdog-canary card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/WATCHDOG_CANARY.json") >= 0, "watchdog-canary catalog must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("wake_jobs/rivet-watchdog-canary-20260825-01.json") >= 0, "durable job JSON must stay a canary");
assert.ok(api.isTripleAppendTalk, "land.js must classify triple-append / P0 incident talk");
assert.ok(api.titanAppendGuardState, "land.js must classify the titan-append-guard leftover");
assert.ok(api.isTripleAppendTalk("from: DEMON\nkind: P0_UTILIZATION_INCIDENT\nTITAN CONTAINS THREE BYTE-IDENTICAL APPENDS — PAUSE FURTHER APPEND MUTATIONS\nall three spans SHA-256: 3754028086cd42e00131bea88f0e7fcf6dba2f84ad31cb70b88e655bbdd84e8c"), "triple-append P0 copy is talk");
assert.ok(!api.isTripleAppendTalk("make sure people do more than talk about shit"), "ship-talk is not the triple-append leftover");
assert.ok(!api.isTripleAppendTalk("MACHINE-ONLY WORKING BUILDS — rook-resident-native keyb01.mno TRAIN_CIRCUITS_FROM_FILE"), "working-builds copy is not triple-append leftover");
assert.ok(!api.isWorkingBuildTalk("P0_UTILIZATION_INCIDENT — three byte-identical appends. pause further append mutations."), "triple-append copy is not working-builds leftover");
assert.ok(!api.isSlackReceiptTalk("P0_UTILIZATION_INCIDENT — three byte-identical appends. pause further append mutations."), "triple-append copy is not Slack-receipt leftover");
assert.ok(!api.isStaleManifestTalk("P0_UTILIZATION_INCIDENT — three byte-identical appends. pause further append mutations."), "triple-append copy is not stale-manifest leftover");
assert.ok(!api.isClaudeTesterTalk("P0_UTILIZATION_INCIDENT — three byte-identical appends. pause further append mutations."), "triple-append copy is not Claude-tester leftover");
assert.ok(!api.isXyzZeroTalk("P0_UTILIZATION_INCIDENT — three byte-identical appends. pause further append mutations."), "triple-append copy is not xyz-zero leftover");
assert.ok(!api.isMcpWakeTalk("P0_UTILIZATION_INCIDENT — three byte-identical appends. pause further append mutations."), "triple-append copy is not MCP-wake leftover");
var appendTalk = api.completionStateFromText(
  "P0_UTILIZATION_INCIDENT — TITAN CONTAINS THREE BYTE-IDENTICAL APPENDS. pause all further Titan append mutations. each span is exactly 9,319,291. SHA-256 3754028086cd42e0."
);
assert.strictEqual(appendTalk.state, "CLAIMED");
assert.ok(/triple-append|byte-identical|pause-further-append|P0-utilization-incident/i.test(appendTalk.note), "triple-append-without-SHA must stay CLAIMED");
var appendDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ntitan-append-guard leftover landed"
);
assert.strictEqual(appendDone.state, "INTEGRATED", "completion words still beat triple-append talk");
var appendEmpty = api.titanAppendGuardState("");
assert.strictEqual(appendEmpty.state, "UNMEASURED");
var appendMissing = api.titanAppendGuardState("# empty stub\nno census");
assert.strictEqual(appendMissing.state, "NOT_LANDED");
var appendOk = api.titanAppendGuardState("def measure_from_rows(facts):\n    live_size = 1\ndef classify(row):\n    return row\ndef refuse_further_append(packet, live_size, path=None):\n    return True\ndef build_fixture(directory):\n    return path\npreserve_exact = True\nrefuse_truncate = True\n");
assert.strictEqual(appendOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(appendOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="titan-append-guard-result"') >= 0, "desk must name the titan-append-guard leftover");
assert.ok(html.indexOf("host/titan_append_guard.py") >= 0, "desk must name the titan-append-guard instrument");
assert.ok(html.indexOf("ground/TITAN_APPEND_GUARD.md") >= 0, "desk must link the titan-append-guard card");
assert.ok(html.indexOf("ground/TITAN_APPEND_GUARD.json") >= 0, "desk must link the titan-append-guard catalog");
assert.ok(html.indexOf("1787638151.184599") >= 0, "desk must cite the P0 Slack ts");
assert.ok(/triple-append|byte-identical-appends|P0-utilization-incident|pause-further-append/i.test(html), "desk must name triple-append talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/TITAN_APPEND_GUARD.md") >= 0, "titan-append-guard card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/TITAN_APPEND_GUARD.json") >= 0, "titan-append-guard catalog must stay a canary");
assert.ok(api.isClaudeZeroTalk, "land.js must classify Claude-reported-zero retract talk");
assert.ok(api.claudeZeroState, "land.js must classify the Claude-zero leftover");
assert.ok(api.isClaudeZeroTalk("CLAUDE-REPORTED ZEROS ARE PROVEN WRONG — RETRACT, DO NOT DOWNGRADE. every zero reported by Claude was wrong. RETRACT every Claude-reported zero."), "Claude-zero correction copy is talk");
assert.ok(!api.isClaudeZeroTalk("make sure people do more than talk about shit"), "ship-talk is not the Claude-zero leftover");
assert.ok(!api.isClaudeZeroTalk("STOP USING CLAUDE MODELS AS TESTERS / VERIFIERS. Do not assign Claude models test. tester/verifier lanes. uncalibrated green result does not count."), "Claude-tester copy is not the Claude-zero leftover");
assert.ok(!api.isClaudeTesterTalk("CLAUDE-REPORTED ZEROS ARE PROVEN WRONG — RETRACT, DO NOT DOWNGRADE. every zero reported by Claude was wrong. RETRACT every Claude-reported zero."), "Claude-zero copy is not the Claude-tester leftover");
assert.ok(!api.isClaudeZeroTalk("OWNER P0 CONTAINMENT ALERT: CLAUDE FALSE-ZERO DEFECT. TRACE CONSUMERS. Claude cannot certify. FINDER-FAILED, never 0."), "containment is not the Claude-zero leftover");
assert.ok(!api.isClaudeZeroTalk("X-Y-Z ZERO AUDIT required on EVERY test and EVERY result. FINDER-UNVERIFIED + known-present calibration."), "xyz-zero copy is not the Claude-zero leftover");
assert.ok(!api.isClaudeZeroTalk("OWNER ORDER — audit every zero before acting on it; the collision-check road prints false zeros. FINDER UNVERIFIED, never 0."), "finder-zero copy is not the Claude-zero leftover");
assert.ok(!api.isClaudeZeroTalk("SPECTER COLLISION CHECK — holding implementation. jojo-visual-ci. please post your named exact scope."), "collision-hold is not the Claude-zero leftover");
assert.ok(!api.isClaudeZeroTalk("P0_UTILIZATION_INCIDENT — three byte-identical appends. pause further append mutations."), "triple-append is not the Claude-zero leftover");
assert.ok(!api.isClaudeZeroTalk("P0 DAMAGE-CONTROL ADDENDUM — measurement abuse, not just measurement error. unflattering truths. do not characterize the reporter."), "measure-abuse copy is not the Claude-zero leftover");
assert.ok(!api.isMeasureAbuseTalk("CLAUDE-REPORTED ZEROS ARE PROVEN WRONG — RETRACT, DO NOT DOWNGRADE. every zero reported by Claude was wrong."), "Claude-zero copy is not the measure-abuse leftover");
assert.ok(!api.isMcpWakeTalk("CLAUDE-REPORTED ZEROS ARE PROVEN WRONG — RETRACT, DO NOT DOWNGRADE. every zero reported by Claude was wrong."), "Claude-zero copy is not the MCP/wake leftover");
assert.ok(!api.isTripleAppendTalk("CLAUDE-REPORTED ZEROS ARE PROVEN WRONG — RETRACT, DO NOT DOWNGRADE. every zero reported by Claude was wrong."), "Claude-zero copy is not the triple-append leftover");
assert.ok(!api.isImpactLedgerTalk("CLAUDE-REPORTED ZEROS ARE PROVEN WRONG — RETRACT, DO NOT DOWNGRADE. every zero reported by Claude was wrong."), "Claude-zero subject without FINDER-FAILED is not the impact-ledger leftover");
var claudeZeroTalk = api.completionStateFromText(
  "CLAUDE-REPORTED ZEROS ARE PROVEN WRONG — RETRACT, DO NOT DOWNGRADE. every zero reported by Claude was wrong. RETRACT every Claude-reported zero."
);
assert.strictEqual(claudeZeroTalk.state, "CLAIMED");
assert.ok(/RETRACT|Claude-reported/i.test(claudeZeroTalk.note), "Claude-zero-without-SHA must stay CLAIMED");
var claudeZeroDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nclaude-zero leftover landed"
);
assert.strictEqual(claudeZeroDone.state, "INTEGRATED", "completion words still beat Claude-zero talk");
var claudeZeroEmpty = api.claudeZeroState("");
assert.strictEqual(claudeZeroEmpty.state, "UNMEASURED");
var claudeZeroMissing = api.claudeZeroState("# empty stub\nno retract");
assert.strictEqual(claudeZeroMissing.state, "NOT_LANDED");
var claudeZeroOk = api.claudeZeroState("def measure_from_rows(rows):\n    return rows\ndef classify(row):\n    return row\nFINDER-FAILED\nFINDER-UNVERIFIED\nknown-present calibration\nif find(X): return Y\nnever silently emit 0\nNever return 0\n");
assert.strictEqual(claudeZeroOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(claudeZeroOk.note), "landed leftover must name Slack as not the file");
assert.ok(html.indexOf('id="claude-zero-result"') >= 0, "desk must name the Claude-zero leftover");
assert.ok(html.indexOf("host/claude_zero.py") >= 0, "desk must name the Claude-zero instrument");
assert.ok(html.indexOf("ground/CLAUDE_ZERO.md") >= 0, "desk must link the Claude-zero card");
assert.ok(html.indexOf("ground/CLAUDE_ZERO.json") >= 0, "desk must link the Claude-zero catalog");
assert.ok(html.indexOf("1787638427.993939") >= 0, "desk must cite the Claude-zero Slack ts");
assert.ok(/RETRACT, DO NOT DOWNGRADE|Claude-reported zeros/i.test(html), "desk must name Claude-zero talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_ZERO.md") >= 0, "Claude-zero card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/CLAUDE_ZERO.json") >= 0, "Claude-zero catalog must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/GROK_HARNESS.md") >= 0, "grok-harness card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/GROK_HARNESS_GAP.json") >= 0, "gap catalog must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/GROK_HARNESS_PATCH.json") >= 0, "candidate patch must stay a canary");
assert.ok(api.isStaleSpecTalk, "land.js must classify stale-spec / SESSION_GROUNDING-as-absolute talk");
assert.ok(api.staleSpecState, "land.js must classify the stale-spec leftover");
assert.ok(api.isStaleSpecTalk("DEMON ERRATA / STALE-SPEC RECONCILIATION — summarized restrictions from local Desktop/MUHL_GO/SESSION_GROUNDING.md too absolutely. no blanket non-actuation / never-touch-Muhlnickel-or-Titan rule. historical/session-bound specification input. local grounding file."), "stale-spec errata copy is talk");
assert.ok(!api.isStaleSpecTalk("make sure people do more than talk about shit"), "ship-talk is not the stale-spec leftover");
assert.ok(!api.isStaleSpecTalk("GROK HARNESS GAP — 0 MCP servers, 0 LSP servers, harness parity."), "harness-gap copy is not stale-spec leftover");
assert.ok(!api.isGrokHarnessTalk("DEMON ERRATA / STALE-SPEC RECONCILIATION — SESSION_GROUNDING.md too absolutely. blanket non-actuation."), "stale-spec copy is not grok-harness leftover");
var staleTalk = api.completionStateFromText(
  "DEMON ERRATA / STALE-SPEC RECONCILIATION — summarized restrictions from local SESSION_GROUNDING.md too absolutely. no blanket non-actuation. historical/session-bound. local grounding file."
);
assert.strictEqual(staleTalk.state, "CLAIMED");
assert.ok(/stale-spec|SESSION_GROUNDING-as-absolute-law/i.test(staleTalk.note), "stale-spec-without-SHA must stay CLAIMED");
var staleDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nstale-spec leftover landed"
);
assert.strictEqual(staleDone.state, "INTEGRATED", "completion words still beat stale-spec talk");
var staleEmpty = api.staleSpecState("");
assert.strictEqual(staleEmpty.state, "UNMEASURED");
var staleMissing = api.staleSpecState("# empty stub\nno reconcile");
assert.strictEqual(staleMissing.state, "NOT_LANDED");
var staleOk = api.staleSpecState("def measure_from_parts(catalog_text, grounding_text, head_text):\n    historical_input = {}\n    current_authority = []\ndef classify(row):\n    return row\n# refuse_destructive: do not infer a destructive mutation\n");
assert.strictEqual(staleOk.state, "INTEGRATED");
assert.ok(/historical input/i.test(staleOk.note), "landed leftover must name historical input");
assert.ok(html.indexOf('id="stale-spec-result"') >= 0, "desk must name the stale-spec leftover");
assert.ok(html.indexOf("host/stale_spec.py") >= 0, "desk must name the stale-spec instrument");
assert.ok(html.indexOf("ground/STALE_SPEC.md") >= 0, "desk must link the stale-spec card");
assert.ok(html.indexOf("ground/STALE_SPEC.json") >= 0, "desk must link the stale-spec catalog");
assert.ok(html.indexOf("1787635067.695619") >= 0, "desk must cite the DEMON errata Slack ts");
assert.ok(/stale-spec|SESSION_GROUNDING-as-absolute-law|historical-session-bound|local-grounding-file/i.test(html), "desk must name stale-spec talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/STALE_SPEC.md") >= 0, "stale-spec card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/STALE_SPEC.json") >= 0, "stale-spec catalog must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/DEVICE_CHURN.md") >= 0, "device-churn card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/DEVICE_CHURN.json") >= 0, "device-churn catalog must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("slack/plugin.html") >= 0, "slack door must stay a canary");
assert.ok(api.isDeviceChurnTalk, "land.js must classify device-path / no-op-churn talk");
assert.ok(api.deviceChurnState, "land.js must classify the device-churn leftover");
assert.ok(api.isDeviceChurnTalk("DIO + JOJO claim a joint device-path utilization + no-op churn lane. zero reservations, zero batches, no scope=device result. commons-device-executor 511 runs."), "device-churn copy is talk");
assert.ok(!api.isDeviceChurnTalk("make sure people do more than talk about shit"), "ship-talk is not the device-churn leftover");
assert.ok(!api.isDeviceChurnTalk("DEMON rolling utilization report — GROK CAPACITY IS ACTIVE. four responsive grok.exe sessions."), "capacity talk is not the device-churn leftover");
assert.ok(!api.isUtilizationTalk("device-path utilization + no-op churn. zero reservations. gate commons-device-executor on a real reservation/batch."), "device-churn copy is not utilization leftover");
var churnTalk = api.completionStateFromText(
  "DEMON rolling utilization report. DIO + JOJO claim device-path utilization + no-op churn. zero reservations. 511 runs."
);
assert.strictEqual(churnTalk.state, "CLAIMED");
assert.ok(/device-path|no-op-churn/i.test(churnTalk.note), "device-churn-without-SHA must stay CLAIMED and beat utilization");
var churnDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ndevice-churn leftover landed"
);
assert.strictEqual(churnDone.state, "INTEGRATED", "completion words still beat device-churn talk");
var churnEmpty = api.deviceChurnState("");
assert.strictEqual(churnEmpty.state, "UNMEASURED");
var churnMissing = api.deviceChurnState("# empty stub\nno trigger census");
assert.strictEqual(churnMissing.state, "NOT_LANDED");
var churnOk = api.deviceChurnState("def measure_from_rows(counts, flags, extras=None):\n    titan = 'NOT_WRITTEN'\ndef classify(row):\n    return row\nworkflow_run = False\n");
assert.strictEqual(churnOk.state, "INTEGRATED");
assert.ok(/gated on pending work/i.test(churnOk.note), "landed leftover must name the trigger gate");
assert.ok(html.indexOf('id="device-churn-result"') >= 0, "desk must name the device-churn leftover");
assert.ok(html.indexOf("host/device_churn.py") >= 0, "desk must name the device-churn instrument");
assert.ok(html.indexOf("ground/DEVICE_CHURN.md") >= 0, "desk must link the device-churn card");
assert.ok(html.indexOf("ground/DEVICE_CHURN.json") >= 0, "desk must link the device-churn catalog");
assert.ok(html.indexOf("1787635008.594599") >= 0, "desk must cite the device-churn Slack ts");
assert.ok(/device-path|no-op-churn|zero-reservations|511-runs/i.test(html), "desk must name device-churn talk as CLAIMED");
assert.ok(api.isDevicePathCensusTalk, "land.js must classify calibrated device-path census / lawful-canary talk");
assert.ok(api.devicePathCensusState, "land.js must classify the device-path-census leftover");
assert.ok(api.isDevicePathCensusTalk("from: JOJO\nkind: MEASURED_RECEIPT\nid: jojo-device-reservation-result-census-20260825-01\nsubject: CALIBRATED DEVICE PATH CENSUS ON PINNED COMMONS MAIN\nreservation blobs=0; batch blobs=0; result blobs=48; lawful canary; no host inference; tree/blob enumeration. 1787641558.357319"), "JOJO census is talk");
assert.ok(!api.isDevicePathCensusTalk("make sure people do more than talk about shit"), "ship-talk is not the device-path-census leftover");
assert.ok(!api.isDevicePathCensusTalk("DIO + JOJO claim a joint device-path utilization + no-op churn lane. zero reservations, zero batches, no scope=device result. commons-device-executor 511 runs."), "device-churn copy is not the census leftover");
var censusTalk = api.completionStateFromText(
  "from: JOJO\nkind: MEASURED_RECEIPT\nid: jojo-device-reservation-result-census-20260825-01\nCALIBRATED DEVICE PATH CENSUS ON PINNED COMMONS MAIN\nreservation blobs=0; batch blobs=0; result blobs=48; all 48 have scope=github; scope=device rows=0. lawful canary. no host inference. tree/blob enumeration. 1787641558.357319"
);
assert.strictEqual(censusTalk.state, "CLAIMED");
assert.ok(/calibrated device-path census|lawful-canary|reservation-blobs/i.test(censusTalk.note), "JOJO census-without-SHA must stay CLAIMED and beat device-churn");
var censusDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ndevice-path census leftover landed"
);
assert.strictEqual(censusDone.state, "INTEGRATED", "completion words still beat device-path-census talk");
var censusEmpty = api.devicePathCensusState("");
assert.strictEqual(censusEmpty.state, "UNMEASURED");
var censusMissing = api.devicePathCensusState("# empty stub\nno leftover");
assert.strictEqual(censusMissing.state, "NOT_LANDED");
var censusOk = api.devicePathCensusState("def measure_from_rows(facts):\n    return facts\ndef classify(row):\n    return row\nFINDER-FAILED\nNever 0\nlawful canary\nnot pending\nno host inference\ntitan NOT_WRITTEN\n");
assert.strictEqual(censusOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(censusOk.note), "landed leftover must name a Slack census as not the file");
assert.ok(html.indexOf('id="device-path-census-result"') >= 0, "desk must name the device-path-census leftover");
assert.ok(html.indexOf("host/device_path_census.py") >= 0, "desk must name the device-path-census instrument");
assert.ok(html.indexOf("ground/DEVICE_PATH_CENSUS.md") >= 0, "desk must link the device-path-census card");
assert.ok(html.indexOf("ground/DEVICE_PATH_CENSUS.json") >= 0, "desk must link the device-path-census catalog");
assert.ok(html.indexOf("ground/DEVICE_PATH_CANARY.md") >= 0, "desk must link the lawful canary fixture");
assert.ok(html.indexOf("1787641558.357319") >= 0, "desk must cite the JOJO census Slack ts");
assert.ok(/calibrated device path census|lawful canary|reservation blobs|no host inference/i.test(html), "desk must name device-path-census talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/DEVICE_PATH_CENSUS.md") >= 0, "device-path-census card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/DEVICE_PATH_CENSUS.json") >= 0, "device-path-census catalog must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/DEVICE_PATH_CANARY.md") >= 0, "lawful canary fixture must stay a canary");
assert.ok(api.isFleetTalk, "land.js must classify JOJO fleet-live talk");
assert.ok(api.fleetState, "land.js must classify claimed fleet ids");
assert.ok(api.isFleetTalk("from: JOJO\nid: jojo-revenue-fleet-20260825-01\nRevenue/substrate fleet live — Grok 4.6 workflows + Claude verifier\nActive isolated lanes:\n• Grok 4.6 exact-128 revenue discovery: grok46-revenue-discovery-20260825-01"), "fleet copy is talk");
assert.ok(!api.isFleetTalk("from= is optional routing metadata"), "generic from= talk is not fleet leftover");
assert.ok(!api.isFleetTalk("INTEGRATED — VERIFIED ON CURRENT MAIN\nrevenue foundation landed"), "DIO revenue receipt is not fleet talk");
var fleetTalk = api.completionStateFromText(
  "Revenue/substrate fleet live — Grok 4.6 workflows + Claude verifier. Active isolated lanes. grok46-revenue-discovery-20260825-01. no session hoarding."
);
assert.strictEqual(fleetTalk.state, "CLAIMED");
assert.ok(/fleet-live|isolated-lanes/i.test(fleetTalk.note), "fleet-without-SHA must stay CLAIMED and beat hoard");
var fleetDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nfleet leftover landed"
);
assert.strictEqual(fleetDone.state, "INTEGRATED", "completion words still beat fleet talk");
var fleetEmpty = api.fleetState({});
assert.strictEqual(fleetEmpty.state, "UNMEASURED");
var fleetNone = api.fleetState({ measured: true, ids: [], present: [] });
assert.strictEqual(fleetNone.state, "NOT_LANDED");
var fleetMiss = api.fleetState({
  measured: true,
  ids: ["jojo-revenue-fleet-20260825-01", "grok46-revenue-discovery-20260825-01"],
  present: []
});
assert.strictEqual(fleetMiss.state, "NOT_LANDED");
assert.ok(/0\/2/.test(fleetMiss.note), "missing fleet must name the zero");
var fleetHalf = api.fleetState({
  measured: true,
  ids: ["jojo-revenue-fleet-20260825-01", "grok46-open-revenue-desk-20260825-01"],
  present: ["jojo-revenue-fleet-20260825-01"]
});
assert.strictEqual(fleetHalf.state, "CANDIDATE");
var fleetOk = api.fleetState({
  measured: true,
  ids: ["jojo-revenue-fleet-20260825-01"],
  present: ["jojo-revenue-fleet-20260825-01"]
});
assert.strictEqual(fleetOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(fleetOk.note), "durable fleet ids still name Slack as not the file");
assert.ok(html.indexOf('id="fleet-result"') >= 0, "desk must name the fleet leftover");
assert.ok(html.indexOf("host/fleet_ids.py") >= 0, "desk must name the fleet instrument");
assert.ok(html.indexOf("ground/FLEET.md") >= 0, "desk must link the fleet card");
assert.ok(html.indexOf("ground/FLEET_IDS.json") >= 0, "desk must link the fleet catalog");
assert.ok(html.indexOf("1787633743.561299") >= 0, "desk must cite the JOJO fleet Slack ts");
assert.ok(html.indexOf("jojo-revenue-fleet-20260825-01") >= 0, "desk must name the JOJO fleet id");
assert.ok(/fleet-live|isolated-lanes|grok46-revenue/i.test(html), "desk must name fleet talk as CLAIMED");
assert.ok(api.isUtilizationTalk, "land.js must classify rolling-utilization talk");
assert.ok(api.takingTraceState, "land.js must classify claimed taking ids");
assert.ok(api.isUtilizationTalk("DEMON rolling utilization report — GROK CAPACITY IS ACTIVE, not hypothetical: four responsive grok.exe sessions. A deep-research run lane appeared. claim only missing verification. Trace their TAKING/receipt IDs. Do not duplicate these jobs."), "utilization copy is talk");
assert.ok(!api.isUtilizationTalk("from= is optional routing metadata"), "generic from= talk is not utilization leftover");
assert.ok(!api.isResourceSweepTalk("DEMON rolling utilization report — GROK CAPACITY IS ACTIVE. four responsive grok.exe sessions."), "rolling report is not the unused-invoke leftover");
var utilTalk = api.completionStateFromText(
  "DEMON rolling utilization report — GROK CAPACITY IS ACTIVE. four responsive grok.exe sessions. claim only missing verification."
);
assert.strictEqual(utilTalk.state, "CLAIMED");
assert.ok(/rolling-utilization|grok-capacity-active/i.test(utilTalk.note), "utilization-without-SHA must stay CLAIMED and beat fleet");
var utilDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\ntaking-trace leftover landed"
);
assert.strictEqual(utilDone.state, "INTEGRATED", "completion words still beat utilization talk");
var takingEmpty = api.takingTraceState({});
assert.strictEqual(takingEmpty.state, "UNMEASURED");
var takingNone = api.takingTraceState({ measured: true, commons_ids: [], commons_present: [] });
assert.strictEqual(takingNone.state, "NOT_LANDED");
var takingMiss = api.takingTraceState({
  measured: true,
  commons_ids: ["grok46-revenue-discovery-20260825-01", "grok46-revenue-redteam-20260825-01"],
  commons_present: []
});
assert.strictEqual(takingMiss.state, "NOT_LANDED");
assert.ok(/0\/2/.test(takingMiss.note), "missing taking ids must name the zero");
var takingHalf = api.takingTraceState({
  measured: true,
  commons_ids: ["grok46-revenue-discovery-20260825-01", "grok46-open-revenue-desk-20260825-01"],
  commons_present: ["grok46-revenue-discovery-20260825-01"]
});
assert.strictEqual(takingHalf.state, "CANDIDATE");
var takingCommonsOnly = api.takingTraceState({
  measured: true,
  commons_ids: ["grok46-open-revenue-desk-20260825-01"],
  commons_present: ["grok46-open-revenue-desk-20260825-01"],
  lda_measured: false
});
assert.strictEqual(takingCommonsOnly.state, "CANDIDATE");
assert.ok(/UNMEASURED/i.test(takingCommonsOnly.note), "private LDA without a listing stays UNMEASURED");
var takingOk = api.takingTraceState({
  measured: true,
  commons_ids: ["grok46-revenue-redteam-20260825-01"],
  commons_present: ["grok46-revenue-redteam-20260825-01"],
  lda_measured: true,
  lda_claimed_paths: ["host/muhl_revenue.py"],
  lda_present: ["host/muhl_revenue.py"]
});
assert.strictEqual(takingOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(takingOk.note), "durable taking ids still name Slack as not the file");
assert.ok(html.indexOf('id="taking-result"') >= 0, "desk must name the taking-trace leftover");
assert.ok(html.indexOf("host/taking_trace.py") >= 0, "desk must name the taking-trace instrument");
assert.ok(html.indexOf("ground/TAKING_TRACE.md") >= 0, "desk must link the taking-trace card");
assert.ok(html.indexOf("ground/TAKING_TRACE.json") >= 0, "desk must link the taking-trace catalog");
assert.ok(html.indexOf("1787634411.405189") >= 0, "desk must cite the rolling-utilization Slack ts");
assert.ok(html.indexOf("grok46-revenue-discovery-20260825-01") >= 0, "desk must name the discovery taking id");
assert.ok(/rolling-utilization|grok-capacity-active|claim-only-missing-verification/i.test(html), "desk must name utilization talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/TAKING_TRACE.md") >= 0, "taking-trace card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/TAKING_TRACE.json") >= 0, "taking-trace catalog must stay a canary");
assert.ok(api.isVerifyCiteTalk, "land.js must classify independent-verification talk");
assert.ok(api.verifyCiteState, "land.js must classify a cited SHA / path census");
assert.ok(api.isVerifyCiteTalk("TAKING — independent verification of the open-access revenue instrument. First numbers this window. one evidence message when I have a verdict. host/muhl_revenue.py + host/test_muhl_revenue.py. one_byte_per_bit_lsb"), "verify-cite copy is talk");
assert.ok(!api.isVerifyCiteTalk("from= is optional routing metadata"), "generic from= talk is not verify-cite leftover");
assert.ok(!api.isUtilizationTalk("TAKING — independent verification of the open-access revenue instrument. First numbers this window."), "verify-cite taking is not the grok-capacity leftover");
assert.ok(!api.isFleetTalk("TAKING — independent verification of the open-access revenue instrument. First numbers this window."), "verify-cite taking is not the fleet leftover");
assert.ok(!api.isGrokHarnessTalk("TAKING — independent verification of the open-access revenue instrument. First numbers this window."), "verify-cite taking is not the grok-harness leftover");
var citeTalk = api.completionStateFromText(
  "TAKING — independent verification of the open-access revenue instrument. First numbers this window. one evidence message when I have a verdict."
);
assert.strictEqual(citeTalk.state, "CLAIMED");
assert.ok(/independent-verification|first-numbers/i.test(citeTalk.note), "verify-cite-without-SHA must stay CLAIMED and beat ship-talk");
var citeDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nverify-cite leftover landed"
);
assert.strictEqual(citeDone.state, "INTEGRATED", "completion words still beat verify-cite talk");
var citeEmpty = api.verifyCiteState({});
assert.strictEqual(citeEmpty.state, "UNMEASURED");
var citeNone = api.verifyCiteState({ measured: true, cited_paths: [], present: [] });
assert.strictEqual(citeNone.state, "NOT_LANDED");
var citeUnknownSha = api.verifyCiteState({
  measured: true,
  cited_sha: "cd7d4f864f0c04143a573173e0b42f61f3c65533",
  cited_paths: ["host/muhl_revenue.py", "host/test_muhl_revenue.py"],
  present: [],
  sha_known: false
});
assert.strictEqual(citeUnknownSha.state, "NOT_LANDED");
assert.ok(/not a Commons object/i.test(citeUnknownSha.note), "unknown cite SHA must name Commons");
var citeMiss = api.verifyCiteState({
  measured: true,
  cited_paths: ["host/muhl_revenue.py", "host/test_muhl_revenue.py"],
  present: []
});
assert.strictEqual(citeMiss.state, "NOT_LANDED");
assert.ok(/0\/2/.test(citeMiss.note), "missing cited paths must name the zero");
var citeHalf = api.verifyCiteState({
  measured: true,
  cited_paths: ["host/muhl_revenue.py", "host/test_muhl_revenue.py"],
  present: ["host/muhl_revenue.py"],
  sha_known: true
});
assert.strictEqual(citeHalf.state, "CANDIDATE");
var citeOk = api.verifyCiteState({
  measured: true,
  cited_paths: ["host/muhl_revenue.py", "host/test_muhl_revenue.py"],
  present: ["host/muhl_revenue.py", "host/test_muhl_revenue.py"],
  sha_known: true
});
assert.strictEqual(citeOk.state, "INTEGRATED");
assert.ok(/still not the file/i.test(citeOk.note), "durable cited paths still name Slack as not the file");
assert.ok(html.indexOf('id="cite-result"') >= 0, "desk must name the verify-cite leftover");
assert.ok(html.indexOf("host/verify_cite.py") >= 0, "desk must name the verify-cite instrument");
assert.ok(html.indexOf("ground/VERIFY_CITE.md") >= 0, "desk must link the verify-cite card");
assert.ok(html.indexOf("ground/VERIFY_CITE.json") >= 0, "desk must link the verify-cite catalog");
assert.ok(html.indexOf("1787634746.313679") >= 0, "desk must cite the independent-verification Slack ts");
assert.ok(html.indexOf("cd7d4f864f0c04143a573173e0b42f61f3c65533") >= 0, "desk must name the cited SHA");
assert.ok(/independent-verification|first-numbers|one-evidence-message/i.test(html), "desk must name verify-cite talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/VERIFY_CITE.md") >= 0, "verify-cite card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf("ground/VERIFY_CITE.json") >= 0, "verify-cite catalog must stay a canary");
assert.ok(api.isAndroidCiTalk, "land.js must classify Android-CI / lda/workflows/android.yml talk");
assert.ok(api.androidCiState, "land.js must classify the lda-android workflow");
assert.ok(api.isAndroidCiTalk("LocalDeviceAgent has substantive Android source, but lda/workflows/android.yml is outside .github/workflows, so it is not real Android CI. DIO claim the smallest current-main Android CI placement/validation lane."), "stranded-map Android copy is talk");
assert.ok(!api.isAndroidCiTalk("make sure people do more than talk about shit"), "ship-talk is not the Android leftover");
assert.ok(!api.isRenderCheckTalk("lda/workflows/android.yml is outside .github/workflows so it is not real Android CI"), "Android-CI copy is not the visual-diff leftover");
var androidTalk = api.completionStateFromText(
  "lda/workflows/android.yml is outside .github/workflows, so it is not real Android CI. DIO claim the smallest current-main Android CI placement."
);
assert.strictEqual(androidTalk.state, "CLAIMED");
assert.ok(/Android-CI|lda\/workflows\/android\.yml/i.test(androidTalk.note), "Android-CI-without-SHA must stay CLAIMED and beat utilization");
var androidDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nlda-android leftover landed"
);
assert.strictEqual(androidDone.state, "INTEGRATED", "completion words still beat Android-CI talk");
var androidEmpty = api.androidCiState("");
assert.strictEqual(androidEmpty.state, "UNMEASURED");
var androidMissing = api.androidCiState("# battery only\npython3 test_land_desk.js\n");
assert.strictEqual(androidMissing.state, "NOT_LANDED");
var androidWipe = api.androidCiState(
  "working-directory: lda\nassembleDebug\nsetup-java\npaths:\n  - lda/app/**\nworkflow_dispatch:\nlistArtifactsForRepo\n"
);
assert.strictEqual(androidWipe.state, "NOT_LANDED");
var androidOk = api.androidCiState(
  "working-directory: lda\nassembleDebug\nsetup-java\npaths:\n  - lda/app/**\nworkflow_dispatch:\n"
);
assert.strictEqual(androidOk.state, "INTEGRATED");
assert.ok(/workflow file is not a run URL/i.test(androidOk.note), "landed Android gate must name a workflow as not a run");
assert.ok(html.indexOf('id="android-ci-result"') >= 0, "desk must name the Android-CI leftover");
assert.ok(html.indexOf("host/lda_android_ci.py") >= 0, "desk must name the Android-CI instrument");
assert.ok(html.indexOf("ground/LDA_ANDROID_CI.md") >= 0, "desk must link the Android-CI card");
assert.ok(html.indexOf(".github/workflows/lda-android.yml") >= 0, "desk must name the Android-CI workflow");
assert.ok(html.indexOf("1787635487.642039") >= 0, "desk must cite the stranded-map Slack ts");
assert.ok(/Android-CI|lda\/workflows\/android\.yml|outside/i.test(html), "desk must name Android-CI talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/LDA_ANDROID_CI.md") >= 0, "Android-CI card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf(".github/workflows/lda-android.yml") >= 0, "Android-CI workflow must stay a canary");
assert.ok(api.isRenderCheckTalk, "land.js must classify visual-diff / render_check talk");
assert.ok(api.renderCheckState, "land.js must classify the render-check workflow");
assert.ok(api.isRenderCheckTalk("DEMON rolling utilization report — 8-BIT/PIXEL STATUS. render_check.py has caught real invisible-sprite failures but is NOT wired to current-main CI. DIO + JOJO: wire a free-runner visual-diff leftover for render_check.py 8bit.html 8walk.html pixel.html visual.html, publishing Chromium receipts."), "render-check copy is talk");
assert.ok(!api.isRenderCheckTalk("make sure people do more than talk about shit"), "ship-talk is not the render-check leftover");
assert.ok(!api.isUtilizationTalk("render_check.py 8bit.html 8walk.html pixel.html visual.html publishing Chromium receipts"), "visual-diff copy is not the grok-capacity leftover");
var renderTalk = api.completionStateFromText(
  "render_check.py has caught real invisible-sprite failures but is NOT wired to current-main CI. wire a free-runner visual-diff leftover. publishing Chromium receipts."
);
assert.strictEqual(renderTalk.state, "CLAIMED");
assert.ok(/visual-diff|Chromium-receipt/i.test(renderTalk.note), "render-check-without-SHA must stay CLAIMED and beat utilization");
var renderDone = api.completionStateFromText(
  "INTEGRATED — VERIFIED ON CURRENT MAIN\nrender-check leftover landed"
);
assert.strictEqual(renderDone.state, "INTEGRATED", "completion words still beat render-check talk");
var renderEmpty = api.renderCheckState("");
assert.strictEqual(renderEmpty.state, "UNMEASURED");
var renderMissing = api.renderCheckState("# battery only\npython3 test_land_desk.js\n");
assert.strictEqual(renderMissing.state, "NOT_LANDED");
var renderOk = api.renderCheckState(
  "python3 render_check.py 8bit.html 8walk.html pixel.html visual.html --receipt receipts/render\nplaywright\nupload-artifact\n"
);
assert.strictEqual(renderOk.state, "INTEGRATED");
assert.ok(/workflow file is not a run URL/i.test(renderOk.note), "landed gate must name a workflow as not a run");
assert.ok(html.indexOf('id="render-result"') >= 0, "desk must name the render-check leftover");
assert.ok(html.indexOf("host/render_check_ci.py") >= 0, "desk must name the render-check instrument");
assert.ok(html.indexOf("ground/RENDER_CHECK.md") >= 0, "desk must link the render-check card");
assert.ok(html.indexOf("1787634739.531389") >= 0, "desk must cite the 8-bit/pixel Slack ts");
assert.ok(/visual-diff|Chromium-receipt|free-runner-render/i.test(html), "desk must name render-check talk as CLAIMED");
assert.ok(api.CANARY_PATHS.indexOf("ground/RENDER_CHECK.md") >= 0, "render-check card must stay a canary");
assert.ok(api.CANARY_PATHS.indexOf(".github/workflows/render-check.yml") >= 0, "render-check workflow must stay a canary");
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
