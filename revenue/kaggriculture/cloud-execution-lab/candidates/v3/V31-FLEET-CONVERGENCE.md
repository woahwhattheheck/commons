# TITAN V3.1 fleet convergence ledger — live post-ship routing

Status: **routing / decision custody only**. This file changes no gameplay, defaults, package bytes, evaluator state, provider state, submission, or Kaggle state.

Snapshot refreshed: **2026-09-11 06:05 EDT**.

## Canonical authority

Current canonical remains:

`titan/v3.1-20260911@a6120d0ea1bdb75eb0da2239220efce551f624a6` (#12494)

It ships H4 strawberry top-up + rival-gated L3 and is the only package/default/submission integration root until that branch actually advances. The shipped package receipt remains `400ae640...` / 136 files. Pre-ship #12447/#12472 and frozen-508b branches are provenance only: reviewed donor bytes may be reused, stale ancestry never grants merge authority.

## Non-negotiable convergence rule

A fleet result is **not finished** because its experiment PR is good. It is finished only when it reaches one of these durable states:

- `CONVERGENCE_READY`: current-canonical source/custody/economics required for the claim are terminal and a production/package/submission consumer exists on the current root;
- `HOLD`: useful evidence exists, but the next blocker is named and the carrier remains attached to this ledger;
- `REJECT`: negative/no-activation/duplicate evidence is preserved so the fleet does not respawn it.

Evidence PRs do not merge directly into canonical by default. Winners earn a narrow production consumer on the then-current canonical. If canonical moves, stale evidence must be rebound before further package/evaluator spend.

## P0 production chain

### L3 ambiguity fail-closed — #12528

Current production consumer: **#12528** `a01dc3de7f2c338e088afa7fc2d66b314a1fb539`, direct child of `a612`.

The branch is still a three-path privileged bootstrap carrier: one write-capable workflow plus the exact reviewed #12515 repair/test donors. The previous write blocker on `a4c168...` is closed on this head:

- generated permanent workflow uses inert `__EVENT_HEAD_EXPR__` tokens inside the outer heredoc;
- Python constructs the literal future `${{ github.event.pull_request.head.sha || github.sha }}` expression only after file creation;
- repaired router Git blob is computed after patch application and replaces `__POST_BOOTSTRAP_ROUTER_BLOB__` before staging;
- unresolved-token, exact-expression-count, exact-router-blob, exact-five-path final-scope, canonical freshness, donor blob, parent blob, materialized 17-test, deterministic build, remote-head CAS, and non-force push gates all fail closed.

Exact-head rereview on this repaired privileged head: review `5177442905` = **WRITE BLOCKER CLOSED / BOOTSTRAP SOURCE+CUSTODY PASS / HOSTED + GENERATED FINAL HEAD + 41-LIVE ECONOMICS PENDING**.

Current exact-head bootstrap run at refresh: `34587217962` queued.

**Routing:** do not spawn another L3 production consumer. If bootstrap succeeds, the generated final five-path head becomes the only L3 landing candidate. It must pass the permanent read-only package gate and rerun the shipped 41-live package receipt with classifier counts and all four prior negative cells before merge authority.

### E20 executable-prefix parity — #12516

Current carrier: **#12516** `41b16c3ea422e76541f1e18ce98a82d70e1ceefe`, direct child of `a612`, exactly three paths.

It mechanically reuses reviewed E20 source/test postimages and preserves H4/L3/cattle policy. Generated FILES/manifest/package artifacts are handoff evidence only until deliberately consumed on the then-current canonical.

**Routing:** keep #12516 as the single E20 donor/rebind authority. After terminal hosted proof, consume its reviewed postimages + regenerated metadata into the current canonical; do not merge a source-only or stale-metadata carrier as package authority.

## Score-facing cattle chain

### Source/submission authority — #12505

#12505 remains the single score-facing cattle-off transform authority. It is not replaced by its execution children.

The broad field result still motivates the lane: 1,984 games/arm across 14 published opponents measured 48 additional losses with cattle-early ON. Current shipped `a612` still has cattle-early true.

### Full current-package A/B — #12529

Current carrier: **#12529** `6d13ca404d5b60be3c3b19ce38f1a9c3fb08bed6`, direct child of `a612`, four evidence-only paths.

It materializes exact score-facing H4 + gated-L3 + sale-fertilizer + horizon8 package arms that differ only in `TITAN-CONFIG.json:r04_cattle_early true -> false`, then runs the 8-seed × both-seat cheap screen against fixed cattle-ON current-package opponent bytes.

### Conditional pull-request execution child — #12531

Current carrier: **#12531** `c13732560e284e3f628d3c884a8af1053cc75202`, stacked on #12505. It exists to keep an already-built fleet A/B from remaining stranded on an un-PR'd branch. It changes only three evidence paths and runs a smaller four-cell live-stack discriminator.

**Routing:** #12531 feeds evidence into #12505/#12529; it is not a third cattle implementation. If cattle-off survives current-stack economics and opponent-diverse widening, #12505 remains the single final submission transform and must sit **above every gameplay/package change selected for the next artifact**.

## Gameplay/economics candidates attached to current V3.1

These are active fleet work, but none is allowed to become an isolated “V3.1 variant.”

| Lane | Exact current carrier | Current routing boundary |
| --- | --- | --- |
| B5 CARROT | #12526 `1bb3b13f5422af9efca2602b010ebce333e8a7aa` | Current-a612 evidence only on the intended cattle-OFF score tuple. Any negative own-score or margin cell holds. Positive cheap screen still requires materially different opponent + D3 before a production landing carrier. |
| JIT PASS→FERTILIZE | #12524 `1bd4a438b39238ebb90d1c3da63a37996118da5e` | Current carrier now has 7 paths including the exact reviewed helper + focused test, closing the earlier missing-helper execution blocker. Live interaction evidence only; positive result earns a materialized default-OFF package gate, not merge/default authority. |
| H3c GOOSE realization | #12521 `79ff57947dd57da951cdb287a590cf5e4fda7231` | Current-a612 evidence only. Strict duplicate/cartesian/type/finite/freshness/opponent custody is repaired. Hosted + economics pending; positive result still needs current-stack materialized package/D3 before production. |
| A1 V219 late-TOMATO ablation | #12530 `2169397bb98cce98cef9c0c8edff00e4562341a9` | Five evidence/CI paths only. Whole-mechanism ablation of V219 qualification on shipped a612; zero activation rejects, any negative margin holds, positive two-regime result only earns a reviewed default-OFF production seam. |
| H13 horizon10 interaction | #12523 `f68e411345937c47b8da696266977647805481c9` | Direct-a612 evidence gate. H10 must remain beneficial in both tested regimes to widen; unconditional H10 remains rejected. |
| B11 adaptive mirror horizon | #12438 repaired `d8fb85e7...` | Strong frozen evidence: Arlene remains exact H8 while mirror regime uses H10 and measured large positive margin. This is **not** current-a612 production authority; next useful step is composition on the shipped stack against H13/gated-L3 context. |
| C1 STRAWBERRY intertemporal sale cap | #12525 `f0f3f882bce5865bf07a72559484a90a92df9422` | Repaired source/provenance/config/cardinality carrier only. Old +53 economics is invalid after narrowing from WOOL/MILK to STRAWBERRY. Activation → incumbent later flush realization is the next cheap gate; zero activations closes the lane before current-a612 rebind spend. |
| C4 public-demand boundary | #12510 repaired proof line | Whole-predebt source theorem is repaired; package/default/economics still require a current-root consumer. |

## Common externality and receipt policy

- #12425 D3 remains the common own/rival/competitive-margin + product-externality merge-policy gate once its hosted exact-head proof is terminal.
- Do not treat own-score gain, self-play gain, or action-trace change alone as promotion evidence.
- Every current-stack economics receipt must bind candidate/control package identity, exact opponent bytes, seed/seat set, official interpreter/evaluator identity, finite typed scores, duplicate/completeness checks, and activation/realization where the mechanism requires it.
- A queued/null/cancelled workflow is never green.

## Current assembly order

1. **Finish #12528 safely.** Generate the five-path L3 fail-closed production head; permanent read-only exact-head gate; 41-live package replay. If it passes, this becomes the next canonical-candidate correctness layer.
2. **Finish #12516 E20 correctness consumption** on whichever canonical head is current after step 1. Regenerate deterministic metadata/package custody; no policy/default change.
3. **Resolve cattle-off on the resulting stack.** Consume #12529/#12531 evidence; if sign remains consistent, retain #12505 as the one top-of-stack score transform.
4. **Resolve gameplay candidates on the resulting stack:** B5 #12526, JIT #12524, H3c #12521, V219 ablation #12530, H13/B11 conditional horizon family, C1 only if it activates. Any candidate whose evidence predates a canonical move must rebind before promotion.
5. **For each economic survivor, create one narrow production consumer.** Default-OFF identity/reachability first where appropriate, deterministic package receipts, opponent-diverse D3, then deliberate default decision.
6. **Apply the final submission transform last.** The cattle-off score transform must sit above all selected production/package changes, never beside them as a sibling.
7. **Only then produce the next leaderboard artifact.** The submission receipt must name the exact canonical ancestry + exact production consumers + exact score transform.

## Collision rules

1. One winning integration head per lane. Experiments may race; production consumers may not.
2. Earlier durable current-canonical owner wins unless it is explicitly rejected/closed/superseded.
3. Reviewed donor bytes can be transplanted; stale branch ancestry cannot.
4. No inherited economics across stack changes.
5. No evidence-only PR is silently treated as a production/package landing PR.
6. Any canonical advance immediately invalidates “current-stack” language on children until they rebind or explicitly prove compatibility.
7. Preserve negative/no-activation results so the fleet does not respawn dead predicates.

## Durable no-spend / reject guidance

Do not reopen without a materially distinct mechanism/context:

- unconditional L3 default-on without the public fail-closed regime gate;
- unconditional horizon10 default;
- B8 reserve guard on its repaired frozen census (structurally reachable but zero authoritative activations / zero decision changes);
- current frozen E5 screen (zero activations; only a cheap activation census is justified after a materially different current-stack change);
- C5 Arlene screen with detector live but zero eligible authored WHEAT SELL relocations;
- H2 last-hop scope with zero realization activations;
- duplicate pre-a612 cattle/E20/B5 landing branches.

## Fleet handoff sentence

**If you discover or repair a factor, attach it to this queue by naming the current canonical parent, exact durable carrier, terminal state, next gate, and intended production consumer. If you cannot name how it reaches the current canonical, the work is not finished.**
