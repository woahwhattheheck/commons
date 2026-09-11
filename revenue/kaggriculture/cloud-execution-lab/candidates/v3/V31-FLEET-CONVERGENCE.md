# TITAN V3.1 fleet convergence ledger — post-ship a612

Status: **routing / decision custody only**. This file does not itself change gameplay, defaults, package bytes, evaluator state, or Kaggle state.

Canonical cutover: `titan/v3.1-20260911@a6120d0ea1bdb75eb0da2239220efce551f624a6` (merged #12494).

## Current authority

`a612` is the only package/default/submission integration root until canonical advances again. It ships:

- H4 `r04_strawberry_topup` ON;
- L3 `r04_no_late_sale_advance` ON behind the public rival-opening gate;
- rebuilt deterministic package `400ae640...`, 136 files, with `build_v3.py --check` clean and 202 V3 checks reported passing in #12494.

The exact #12494 package was measured on the 41 live games of submission 56159263 with pinned recorded opponents: +68.9 margin/game versus the prior V3.1 package (own +60.2, rival -8.7; 34 better / 4 worse / 3 same) and +652.4/game versus V3.0. H4 and rival-gated L3 were additive game-for-game on that panel.

Pre-ship #12447 / #12472 and frozen-508b branches remain **provenance/evidence only**. Exact donor blobs may be reused; their ancestry is not current merge authority.

## Terminal contract

Every fleet lane ends durably as one of:

- `CONVERGENCE_READY`: source + custody + economics required for its claim are terminal, and current package/default/submission work is rebased/recomposed onto `a612` or later canonical;
- `HOLD`: useful evidence exists but a named blocker remains;
- `REJECT`: preserve the negative / no-activation / duplicate result so the fleet does not respends it.

A winning experiment that remains only on an old sibling is not finished. A repaired source whose package wiring still targets pre-a612 ancestry is not current integration work.

## Immediate post-ship gates

### 1. Shipped L3 ambiguity hardening — P0 correctness

`a612`'s rival gate is supported on the 41 complete live openings, but the current implementation can treat missing/unreadable/insufficient opening evidence as `rival_on_tape() == false`; false permits the risky L3 suppression arm. That is a fail-open boundary outside the measured complete-opening domain.

Current disposition: `HOLD / POST-SHIP HARDENING`. Re-derive #12490's reviewed fail-closed proof semantics directly on `a612`: only complete strict opening evidence may classify OFF_TAPE; malformed/gap/rewind/late-start/insufficient evidence must preserve incumbent E184 behavior. Rerun the exact 41-game shipped-package receipt including all negative cells after source proof. Do not silently undo #12494; harden the shipped gate.

### 2. Cattle-early field regression — P0 score-facing

The broad official-engine field check measured 1,984 games/arm against 14 published agents: baseline 1957W/27L; `r04_cattle_early` 1909W/75L (48 extra losses); sale-fertilizer 1957W/27L. Canonical `a612` still ships cattle-early true.

Current disposition: `HOLD / CURRENT-BASE REPARENT ACTIVE`. The pre-a612 #12493 transform is donor evidence only. The live carrier must be a direct `a612` child and prove the output package differs only in `TITAN-CONFIG.json`, preserves shipped H4 + rival-gated-L3 keys/bytes, forces sale-window ON / horizon8 / sale-fertilizer ON / cattle-early OFF, and keeps the reviewed pre-build CLI horizon-fail contract. Prefer a cheap exact-a612 cattle OFF-vs-ON confirmation before leaderboard upload; no need to rerun the full 1,984 first unless the sign surprises.

### 3. B5 CARROT + JIT — strongest unshipped gameplay family

B5 CARROT repaired source #12499 has independently closed the current malformed-input/whole-action source blockers; hosted and materialized economics remain. CARROT and JIT measured nearly perfectly additive on the pre-a612 live R04 parent: combined exact-V3.1 frozen panel 16/16 positive, mean paired DeltaM +107.5; Arlene 16/16 positive, mean +126.25. Those numbers are evidence, not inheritance onto `a612`.

Current disposition: `HOLD / POST-a612 PACKAGE REBIND ACTIVE`. Old #12496 is stale/closed. Package wiring must consume the final repaired B5 source semantics on a clean direct child of `a612`, ship default FALSE first, regenerate deterministic metadata, prove OFF identity, then run B5 ON and B5+JIT ON against the exact shipped stack with D3 own/rival accounting before any default decision.

### 4. E20 executable-prefix repair — correctness carrier

Reviewed E20 donor semantics remain useful: only executable market-prefix HIRE rows consume/drop allowance; tail HIRE rows beyond `max(1,int(maxMarketOrdersPerTurn))` do not affect the decision. Pre-a612 #12497 is now stale topology.

Current disposition: `HOLD / NEEDS DIRECT-a612 REBIND`. Reuse the exact reviewed donor blobs, bind a current-head workflow to `a612`, regenerate FILES/manifest/package receipts through the existing deterministic builder, and rerun materialized package predecessors. No gameplay default change is required.

### 5. D3 externality gate — fleet merge-policy evidence

#12425 current repaired source/policy/evidence custody has passed independent review; dedicated hosted execution remains pending. Use D3 after terminal hosted proof for any market-facing candidate. Do not infer safety from self-play or own-score alone.

## Other active lanes

- **H3c goose cap-loss rescue** — source/same-site ownership repaired; `HOLD` for exact materialized activation + paired D3 on the current canonical, then a third opponent.
- **C1 intertemporal SELL cap** — `HOLD`. Current rescue review found sale-provenance and config/cardinality blockers; historical +53 is predecessor evidence only. Repair provenance before more economics.
- **C5 WHEAT rider / B10 public-supply successor / C4 public-demand predecessor** — source-correctness work is progressing, but none owns package/default authority without new `a612` economics.
- **A5 MELON / B9 terminal fertilizer / H1 realization / B7 concrete overflow guards** — activation-first or narrow-economics lanes; keep package-neutral until signal clears.

## Durable rejects / no-spend evidence

Keep these out unless a genuinely distinct mechanism reopens them:

- unconditional L3 default-on without a public fail-closed regime gate;
- H13 fixed horizon10;
- H10B unilateral sale deferral;
- H9;
- H2 last-hop rescue as currently scoped (0/16 activations on its exact realization census; parent already owns the live step717 return seam);
- current E5 zero-activation predicate;
- broad generic D5/D6/D4/M1 duplicates with no distinct measured seam.

## Collision and assembly rules

1. **Canonical first:** before any package/default/submission work, fetch `titan/v3.1-20260911`. If its head is no longer `a612`, rebase/recompose again before spending receipt/evaluator capacity.
2. **One winning head per lane:** experiments can race; integration cannot. Earlier durable current-canonical owner wins. Close duplicate carriers and preserve them only as provenance.
3. **Donor bytes are not ancestry:** exact reviewed source blobs may be transplanted onto current canonical; stale branch topology never authorizes merge.
4. **No inherited economics across stack changes:** rerun representative paired `DeltaOwn`, `DeltaRival`, `DeltaM`, activation/realization, opponent identity, seeds/seats and package/interpreter custody on the combined current stack.
5. **Submission is the top of the stack:** the cattle-off submission transform must eventually sit above every gameplay/package change intended for the next artifact, not beside it as a sibling.
6. **Never call queued/null Actions green.**

## Current assembly queue

1. Fail-close shipped L3 ambiguity on direct `a612`; rerun exact 41-game package receipt.
2. Reparent cattle-off submission transform onto `a612`; preserve prior builder hardening; run cheap exact-current cattle A/B.
3. Rebind E20 correctness donor onto `a612` with deterministic package metadata.
4. Rebind final B5 source onto `a612` default-FALSE; package-gate CARROT then CARROT+JIT on the current shipped stack.
5. Carry only candidates that survive materialized current-stack D3/opponent-diverse gates into the next canonical head.
