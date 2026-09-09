# SOL-LEVEL — TITAN V3 receding reserve-release receipt

- Operation: `titan-v3-receding-reserve-release-20260909-01`
- Starting main: `5c202d3d471e77df2bcbf4add371fa2b8aaaf308`
- Branch: `sol-level-full-shed-feasibility-20260909-01`
- Canonical mutation: **none**
- Provider/Kaggle action: **none**
- Status at publication: additive candidate and exact paired development gate

## Claim correction

The initial hypothesis treated `scheduler.py`'s `cap - 1` feasibility boundary
as an accidental mismatch with the official engine. Source provenance disproved
that classification: preserved Arlene explicitly documents a deliberate
one-slot capacity reserve. The blanket boundary edit was withdrawn before any
source write.

The shipped candidate instead releases the spare slot for one receding-horizon
step only under an explicit zero-pre-market-growth certificate. It preserves the
original policy at true unit overflow, route checkpoints, day boundaries,
dynamic selected-unit work, next-step `DROP`/`PLACE`, current/next incoming
product or animal purchases, malformed active-market rows, non-24-turn day
semantics, malformed state, and peer-patch collisions.

## Evidence hardening

Post-publication self-review found that the first branch head
`01108a7cfa366e71214640885d3b076f9a2b997c` had an indentation defect in
`test_reserve_release.py`: only one intended reserve contract was discoverable,
while later functions were nested. That queued head was superseded before it
could serve as accepted evidence. The corrected workflow now fails unless the
unittest loader discovers exactly 14 reserve contracts, 5 inherited comparator
contracts, and 5 strict own-cash contracts.

A second independent `strict_gate.py` now blocks margin-only apparent gains when
candidate own cash falls or fails to improve. This closes the case where harming
the rival could otherwise satisfy the upstream margin gate.

## Owned additive paths

- `revenue/kaggriculture/cloud-execution-lab/candidates/v3-receding-reserve-release/**`
- `.github/workflows/titan-v3-receding-reserve-release.yml`
- this receipt

## Acceptance

1. Focused predecessor and official-engine contracts pass.
2. `build_integrated.py --check` proves canonical source/archive consistency.
3. Current control and candidate run on the same official interpreter, public
   opponents, development seeds, and both seats.
4. The upstream comparison rejects incomplete/duplicate/extra/nonfinite/
   provenance-drifted cells and margin regressions.
5. The independent strict gate requires a changed trace, positive paired mean
   own cash and margin, and zero negative own-cash or margin cells. Trace-only
   changes and rival-harm-only margin gains are held.
6. The loader must discover exactly 14 reserve-release, 5 comparator, and 5
   strict-gate contracts; indentation/nesting regressions are admission failures.

No score or promotion claim is made until the exact hosted workflow report is
available.
