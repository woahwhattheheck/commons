# Canonical a612 L3 opening-gate fail-closed proof

This is a **package-neutral source-repair proof** bound directly to the current V3.1 canonical root `a6120d0ea1bdb75eb0da2239220efce551f624a6` (merged #12494).

## Why this is score-facing

#a612 shipped H4 plus the rival-gated L3 arm. Its current `r04_full_router.py` still treats an unreadable or incomplete public opening as `rival_on_tape() == False`; the L3 call site interprets that value as permission to suppress the incumbent E184 reservation. Thus missing, malformed, late-started, or discontinuous evidence can fail open into the risky L3 arm.

The exact shipped 41-game package receipt was strongly positive overall (+68.9 margin/game, 34 better / 4 worse / 3 unchanged), so this proof does **not** undo or replace the shipped gate. It hardens only the ambiguity boundary.

## Donor semantics

`repair.patch` is byte-identical to the reviewed proof delta from #12490. The target gate block on canonical a612 is still the exact unsafe preimage, so the same delta is intentionally reused rather than re-derived.

The repaired contract is:

- only the complete public opening steps 1..143 may certify `OFF_TAPE`;
- all 143 samples must be contiguous and strictly typed;
- `step`, `player`, two-farm cardinality, farmer coordinate shape, and coordinate scalars are exact-type checked (bool/float/string aliases fail closed);
- the existing `RIVAL_GATE_SHARE = 0.8` threshold is evaluated only after the complete valid window;
- the completed decision freezes until rewind/new-game reset;
- gaps, late starts, malformed samples, partial windows, missing evidence, or malformed outer step/player preserve incumbent E184 rather than enabling L3.

`test_failclosed.py` is also byte-identical to #12490's 17-test predecessor suite. It covers complete on/off-tape openings, threshold edge, partial/single-sample ambiguity, strict scalar poisoning, farm cardinality, gaps, rewind, frozen decisions, both seats, call-site reservation behavior, and exact parent identity for malformed outer step/player.

## Important current-test boundary

Canonical a612's existing `overlay/checks/test_v3_r04_l3_rival_gate.py` is itself the pre-repair contract: it explicitly expects unreadable evidence and fresh-game zero evidence to return `False`. A production source consumer must therefore replace/update that packaged test together with the router source. This proof deliberately leaves both production files untouched and applies the router repair only ephemerally inside CI.

## Custody

The dedicated workflow binds exact parent a612, the current router blob `d797ecd6068dc714d2ba45d44c2d672842116c7b`, and current stale packaged gate-test blob `543101ea0499a529e024675d8299a896b3e5f9dd`; requires exactly the four additive proof-carrier paths; applies the repair with `git apply --check`; compiles the patched source; runs all 17 fail-closed predecessors; then restores the router and proves a clean checkout.

## Consumption boundary

Passing this PR is **not** package/default/merge/Kaggle authorization. After source review + exact-head CI:

1. consume the proven router delta directly onto the then-current canonical root;
2. update the packaged L3 gate test to the fail-closed contract;
3. regenerate deterministic FILES/manifest/archive receipts as required;
4. rerun the exact 41-live-game package receipt, explicitly reporting all four prior negative cells plus classification counts.

No H4, cattle, sale-window, horizon, evaluator/opponent, provider, or submission state changes are authorized here.
