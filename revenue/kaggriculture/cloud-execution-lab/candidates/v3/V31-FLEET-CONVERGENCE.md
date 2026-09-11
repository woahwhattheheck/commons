# TITAN V3.1 post-ship fleet convergence ledger

Status: **routing / decision custody only**. This file changes no gameplay, default, package member, evaluator, opponent, provider, Kaggle state, or submission artifact.

Last coordinated: 2026-09-11 05:46 EDT.

## Canonical cutover

**Authoritative score-facing base is now `titan/v3.1-20260911@a6120d0ea1bdb75eb0da2239220efce551f624a6`, merged by PR #12494.**

Do not use #12447 / #12472 / #12483 as the package/default/submission integration authority for new work. They remain useful reviewed evidence/donor history only. Every new score-facing package, default, submission transform, or receipt must derive from exact `a612` (or a later canonical head) and prove that ancestry.

#12494 ships two measured factors ON inside R04:

- `r04_strawberry_topup=true` — H4 strawberry top-up;
- `r04_no_late_sale_advance=true` — L3 suppression behind the public rival-opening gate.

The shipped package also retains V3.1 `r04_sale_fertilizer=true` and `r04_cattle_early=true`.

Merged evidence is the exact 41 recorded live games replayed on their original seeds/opponent play: against prior V3.1, H4 alone was `+32.6` margin/game, gated L3 alone `+36.3`, and the exact combined submission package was **`+68.9` margin/game** (`own +60.2`, `rival -8.7`, `34 better / 4 worse / 3 same`, sign-test `p=3e-7`). Against V3.0 the combined package was `+652.4` margin/game. The combined package equaled the separately measured H4 + gated-L3 effect game-for-game on all 41 recordings. `build_v3.py --check` passed on package digest `400ae640...`; the submission archive reported by #12494 is `b95ffb67...`, 136 files; all 202 V3 checks passed.

This is shipped evidence, not immunity from later hardening. New fixes must preserve the exact a612 shipped semantics outside their claimed seam and rerun the affected package receipt.

## P0 score-facing work after a612

### 1. Fail-close the shipped L3 rival gate

`HOLD / ACTIVE OWNERS — DO NOT DUPLICATE.`

The merged R04 classifier treats zero/unreadable/incomplete opening evidence as `rival_on_tape() == false`; false currently permits the risky L3 suppression arm. Normal complete 41-game openings classified cleanly, but reset/late-start/gap/malformed/insufficient history can therefore fail open to the aggressive policy.

Current repair contract: complete strict opening evidence may classify; ambiguity disables L3 suppression and preserves the safer incumbent behavior. Consume #12490 proof semantics, but re-derive against exact a612 bytes, then replay all 41 shipped-package recordings including the four negative cells before any merge. Multiple post-a612 owners are already active; earlier durable owner wins.

### 2. Remove cattle-early from the next submission if the a612-conditioned A/B survives

`HOLD / ACTIVE OWNERS — HIGH SCORE-FACING PRIORITY.`

Current a612 still ships `r04_cattle_early=true`. Field evidence on the earlier controlled package reported 1,984 games/arm across 14 published opponents: cattle-early changed `1957W/27L` to `1909W/75L` — **48 additional losses** — while sale-fertilizer preserved the baseline win record. That is the strongest broad field-harm signal currently in the fleet.

Pre-a612 #12493 is no longer score-facing authority. The correct current test/materialization is direct from exact a612, preserving shipped H4 + rival-gated L3 + sale-fertilizer + horizon8 and changing only `r04_cattle_early`. Post-a612 cattle-off rebase/A-B owners are active. Require package-member equality except `TITAN-CONFIG.json`, strict CLI pre-build validation, pinned opponents, both seats, and paired `DeltaOwn / DeltaRival / DeltaM` before submission use. No default/Kaggle mutation is implied by this ledger.

### 3. Rebind B5 CARROT onto a612

`HOLD / ACTIVE OWNER.`

B5 remains the strongest replicated unshipped factor:

- frozen Arlene: 16/16 positive, mean paired `DeltaM +89.125`;
- direct exact-V3.1: 16/16 positive, mean `+66.375`;
- B5 CARROT × JIT factorial: Arlene 16/16 positive, mean `+126.25`; exact-V3.1 16/16 positive, mean `+107.5`, essentially additive seed-for-seed.

Source hardening is now represented by #12499 exact `15e8367e4d3fff41e7e6eb2d088327f558764454`; independent review reports B5 source blockers closed, hosted/materialized economics pending. Pre-ship package child #12496 is stale topology after a612 and its write-bootstrap also has exact-head custody HOLD. A clean direct-a612 B5 package rebind owner is already active: preserve shipped H4/L3 bytes and defaults exactly, add B5 behind default FALSE first, regenerate deterministic manifests/package receipts, prove OFF identity to a612, then run B5-ON against the exact current stack before any enable decision.

## Fleet-wide evidence infrastructure

- **D3 externality gate #12425** — `SOURCE / POLICY / EVIDENCE-CUSTODY PASS · HOSTED PENDING` on exact `a91053ed31057d091327f3359cb125f746160f5a`. Dedicated run `34585263315` remained queued at last check. Use only after terminal hosted custody; it is the required own/rival accounting surface for score-facing market changes.
- **Receipt guard #12470** — repaired exact `6219d37248a0ae513657b4f4b52be8ef39dc1109`, rebound review says source/test/custody PASS, dedicated run `34585448705` queued. Rebase useful receipt semantics to a612 before score-facing consumption.
- **Pre-ship reachability #12483** — repaired source/custody PASS with queued run, but it targets the pre-a612 convergence line. Treat as reviewed donor semantics only; current package work must prove a612 ancestry/materialization directly.
- **E20 #12497 / older tooling bundles** — donor evidence only until rebound onto a612 with regenerated package metadata. Do not merge stale pre-ship topology.

## Current positive source/economics lanes

These may remain on frozen/pre-ship branches as experiments, but any score-facing integration must rebase/re-evaluate on a612 because H4 + gated L3 are now live behavior.

- **H3c #12473** — source/same-site ownership PASS on `2f7ab898d28a98749a5b0625eb15da0d56a38552`; exact-materialized activation + D3 execution owner active. Hosted/economics pending.
- **C5 #12480** — repaired source/mechanics/custody PASS on `e71918de0254f94f697495a799e519691b636803`; dedicated run queued and paired D3 execution owner active.
- **D1 #12474** — latest animal/structure repair landed on `67070ddd40dc50b7fcba1f85db395a3ec49860bc`; fresh rebound review/hosted/economics required.
- **B10 #12487** — transition/public-supply successor source/custody PASS on `63b78a7c8edfe2ea08411faa8dd25a6b0eaddb8a`; hosted + D3 economics pending. Keep distinct from rejected static visible-farm B10.
- **C1 #12485** — `HOLD / SOURCE REPAIR REQUIRED`. Core h20 town-demand -> h21 flush mechanism remains plausible, but exact review found final SELL-multiset equality cannot prove native provenance after same-callback E184/V233/V231 accounting; config completeness and inventory cardinality also fail closed incompletely. Historical `+53` is predecessor evidence only. Do not run economics until source ownership is repaired.
- **C4 #12468** — mechanism survives; pre-parent whole-debt snapshot repair is actively claimed. Do not duplicate.
- **D4 #12469** — narrow pre-incumbent-flush source/custody PASS on `2cb7350fa95f1bdbfb3df8f8a31f6458809d28e4`; hosted/activation/economics pending. Broad D4 remains rejected.
- **C6 #12452** — narrow V219-conditioned FERT reserve remains HOLD on `e0a25c2984ea086e912078e992d0f9559ffd455c`; generic static C6 remains rejected. Require structural overlap and withheld-FERT -> V219 PICKUP/FERTILIZE -> realized production before economics; any a612 score-facing version must be rebound because R04 bytes changed in #12494.

## Consumed / closed lanes

- **H2 early flush** — rejected/negative.
- **H2 terminal-return #12481** — `REJECT / ZERO REALIZATION`. Exact ready-V3.1 frozen 16-cell census produced 0 rescues and baseline-identical outcomes; parent already owns the live last-hop return seam at step717. #12481 was closed unmerged under its own zero-activation contract. Do not spend more evaluator budget on H2 unless a genuinely different causal seam appears.
- **H13 fixed horizon10, H10B unilateral sale deferral, H9** — rejected by opponent-conditioned economics.
- **E5 terminal floor liquidation** — zero activation on its exact predicate.
- **B6 broad dead-stock advancement and simple final48/final24 clocks** — rejected; later cutoff did not rescue economics.
- **B7 broad generic shed-room premise** — rejected for broad activation; repaired terminal/V219 successor remains a separate proof lane and must earn real activation before score spend.
- **B10 static visible-farm exposure theorem** — rejected; keep distinct from #12487 transition-derived successor.
- **generic/static C6 and broad D4** — rejected; keep distinct from the narrow successors above.

## Collision and ancestry rules after cutover

1. **Exact a612 (or later canonical) is mandatory for score-facing package/default/submission work.** Pre-ship topology is never inherited as authority merely because donor bytes are reviewed.
2. Frozen/pre-ship experiment branches remain valid source/economics evidence only within their stated custody; transplant semantics deliberately and rerun changed-stack economics.
3. Search exact lane marker + PR before claiming. Earlier durable owner wins. If the branch advances first, yield rather than race a duplicate.
4. Never call queued/null Actions green.
5. A source PASS is not an economics PASS; a reachability PASS is not source authority; a package PASS is not leaderboard authority.
6. Shared-market changes require paired own/rival accounting, not self-play-only optimism.
7. Every integration handoff preserves exact head, parent/merge-base, changed paths/blobs, package/interpreter/opponent identity, seed/seat cells, activation/realization, `DeltaOwn`, `DeltaRival`, `DeltaM`, and all negative transitions.

## Immediate post-a612 queue

1. Land a fail-closed a612 L3 rival-gate hardening only after exact 41-game replay confirms normal classifications/results are preserved or improved.
2. Finish direct-a612 cattle ON/OFF package A/B; if the broad 48-loss field harm survives the shipped H4/L3 stack, make cattle-OFF the next submission-only transform with strict package custody.
3. Finish direct-a612 B5 default-OFF package rebind from the reviewed #12499 semantics; prove OFF identity, then run B5 ON on current-stack package bytes. Preserve CARROT×JIT positive factorial as interaction evidence.
4. Terminalize D3 #12425 hosted custody so every next market/supply factor has one trustworthy externality gate.
5. Spend evaluator capacity only on source-cleared H3c/C5/D1/B10 successors; repair C1/C4 first.
6. Kill zero-activation/negative lanes durably and keep the fleet on current canonical ancestry.
