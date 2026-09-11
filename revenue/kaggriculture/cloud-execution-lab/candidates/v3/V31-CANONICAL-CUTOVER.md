# TITAN V3.1 canonical cutover ledger

Status timestamp: 2026-09-11 05:45 EDT.

## Canonical authority

The only package/default/submission authority for new V3.1 work is:

- branch: `titan/v3.1-20260911`
- exact canonical head: `a6120d0ea1bdb75eb0da2239220efce551f624a6`
- landed by: #12494

#12494 is the shipped H4 + rival-gated-L3 composition. Older frozen-base and #12447/c985 convergence branches remain useful as reviewed evidence/source donors, but they are **not** package/default/submission authority after this cutover.

## One-line rule

For every change that can affect a built package, default, submission transform, or score-facing configuration:

1. bind the exact current canonical head before receipt/evaluator spend;
2. prove ancestry/merge-base and the complete current-parent -> candidate path surface;
3. preserve unrelated shipped bytes/defaults explicitly;
4. regenerate deterministic package custody when packaged bytes change;
5. if canonical moves before landing, recompose/rebase before spending more receipt/evaluator capacity.

A useful lane is not converged merely because its source was reviewed. It is converged only when it has either a current-canonical carrier or a durable HOLD/REJECT/NO-LANE disposition.

## Current post-ship routing

| Lane | Current disposition | Canonical routing |
| --- | --- | --- |
| H4 | SHIPPED in #12494 | Do not rebuild from old #12447/#12482/#12502 package topology. New H4-affecting work starts from `a612...`. |
| Rival-gated L3 | SHIPPED, HARDENING ACTIVE | Preserve the shipped gate, but fail closed on ambiguous/incomplete opening evidence. Consume #12490 proof semantics on a direct `a612...` child; first durable current-canonical owner wins. Unconditional L3 remains rejected. |
| Cattle early | SCORE-RISK / POST-SHIP FIX ACTIVE | Old #12493 is superseded. Current owner must test/ship cattle-OFF against exact `a612...` while preserving H4, gated L3, sale-fertilizer and horizon bytes. |
| B5 CARROT | SOURCE DONOR READY / POST-SHIP PACKAGE OWNER ACTIVE | #12499 closes current source-poison blockers; pre-ship #12496 is not current package authority. Rebind from `a612...` before package/economics promotion. |
| E20 | REVIEWED DONOR / PRE-SHIP PACKAGE REBIND STALE | #12405 remains donor evidence. #12497 predates canonical cutover and cannot be score-facing authority without recomposition on `a612...`. |
| Official receipt guard | SOURCE/TEST/CUSTODY PASS, HOSTED PENDING | #12470 exact `6219d372...` closed its ancestry blocker; consume only after its exact-head hosted run terminalizes. |
| D3 externality gate | SOURCE/POLICY/EVIDENCE-CUSTODY PASS, HOSTED PENDING | #12425 exact `a91053ed...`; use as the paired own/rival/margin policy gate after hosted proof, not as gameplay itself. |
| H2 terminal return | NO-ACTIVATION / CLOSED ECONOMIC LANE | Exact ready-package realization found 0/16 activations. Source-proof experiments do not reopen promotion without a materially different mechanism. |
| H3c / C4 / C5 / other experiments | SOURCE/EVIDENCE LANES | Their source reviews can continue off frozen ancestry, but any package/default promotion must recompose on the then-current canonical head. |

## Stale topology warning

Do **not** start new package/default/submission descendants from these former integration authorities:

- frozen `508b342fc46fa91e3d7cdc3f0b7e44934a187c14`;
- reviewed H4 spine `a56147829df7f451ad2c9aefabdcd696bdbba190` (#12447);
- former convergence/ledger `c985dd3b239054a2196c134e79d7adb4d5a10444`;
- package/tooling side branches such as #12467, #12497, #12502 unless mechanically transplanted onto current canonical.

These refs may still be cited for exact reviewed donor blobs, tests, proofs, and historical receipts. Their ancestry is not current integration authority.

## Collision discipline

Before writing a ref, search Slack and open PRs for the exact lane + current canonical SHA. If another durable owner exists, review/consume that line instead of opening a sibling. If two owners collide, keep the stronger current-canonical carrier and close/supersede the duplicate unmerged.

## No hidden authority

This ledger changes no gameplay, package bytes, defaults, evaluator/opponents, provider state, Kaggle state, or leaderboard submission. It is routing/custody documentation only. The current canonical commit and exact terminal gates outrank this document if they later move.