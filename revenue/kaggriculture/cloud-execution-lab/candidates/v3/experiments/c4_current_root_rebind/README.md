# C4 public-demand boundary — current-8e3 donor

Fleet lane: `TITAN-V31-8E3-C4-PUBLIC-DEMAND-BOUNDARY-REBIND-20260911-01`.

## Purpose

This is a **current-root evidence donor**, not production/default/package authority. It binds the reviewed C4 public-town-demand boundary from #12468 and the independently reviewed whole-predebt fail-closed repair from #12510 to shipped V3.1 root `8e3d92a286806f9f9525973ee7d359b629a11487` (#12537), where B5 CARROT + JIT are already production bytes on top of H4 + rival-gated L3 + sale-fertilizer.

C4 does not infer rival intent or claim that a generic quiet market slot is observable. The only timing signal is deterministic public town consumption: market rows execute before town demand, unlocked shops consume known products on the public shop cadence, and town center consumes known products on its public cadence. If incumbent E184 newly advances an authored future SELL across one of those known demand ticks, C4 may roll back only that newly-created reservation and leave the future authored sale in place.

## Exact reviewed donors

The carrier copies these already-reviewed objects byte-for-byte rather than reimplementing them:

- #12468 candidate blob `1f2f3d05bceb62fbbb9c3d6474364cfd32b256e2`;
- #12468 focused-test blob `ea30a397d3ec6baddea60d667efdd011e3779228`;
- #12510 whole-predebt repair patch blob `9933b22d187daee8ae7ee394690b0d3f19c73cb6`;
- #12510 four-killer regression blob `49f35001a52dbb313a0b62160eb32426efa8053d`.

The repair validates the entire pre-parent sale-debt snapshot before any newly-created debt can authorize rollback: stale/malformed pre-debt fails closed; debt due exactly on the current callback may legitimately disappear as incumbent settlement; future pre-debt must survive with each prior amount intact or increased.

## Current-root custody

The dedicated workflow requires live `titan/v3.1-20260911` to remain exact 8e3, exact merge-base 8e3, and exactly these six additive donor/CI paths. It pins the four donor blobs above plus current shipped R04/apply/B5/JIT postimages. It applies the reviewed repair ephemerally, runs all 14 inherited C4 predecessors plus all four whole-predebt killers, then restores a clean tree.

Because `candidate.py` delegates to the **current checkout's** full `r04_full_router.v3_agent()`, this current-root source proof inherits the shipped B5 CARROT + JIT + H4 + gated-L3 + sale-fertilizer behavior rather than copying an a612 runtime stack. No production overlay or deterministic default changes in this PR.

## Evidence boundary / convergence

C4 still needs current-package activation and opponent-diverse paired `DeltaOwn / DeltaRival / DeltaM` before any promotion. Delaying supply across a public demand tick can improve our later quote but can also improve a rival quote; D3 externality accounting remains mandatory.

Assembly rule: after #12535 immutable build custody and #12541 L3 fail-closed correctness settle on the then-current canonical, consume this exact repaired theorem into **one** current-canonical production/package lane only if economics justify it. Regenerate package receipts through the canonical builder, prove B5/JIT/H4/L3/sale-fertilizer preservation, and keep cattle/row-shed/default decisions orthogonal. If canonical advances first, this workflow deliberately stale-fails and the exact donor objects must be rebound again rather than merging stale ancestry.
