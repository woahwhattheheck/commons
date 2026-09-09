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
product or animal purchases,
malformed state, and peer-patch collisions.

## Owned additive paths

- `revenue/kaggriculture/cloud-execution-lab/candidates/v3-receding-reserve-release/**`
- `.github/workflows/titan-v3-receding-reserve-release.yml`
- this receipt

## Acceptance

1. Focused predecessor and official-engine contracts pass.
2. `build_integrated.py --check` proves canonical source/archive consistency.
3. Current control and candidate run on the same official interpreter, public
   opponents, development seeds, and both seats.
4. The comparison rejects incomplete/duplicate/extra/nonfinite/provenance-drifted
   cells.
5. `ADVANCE` requires a changed trace, positive paired mean margin, and zero
   negative development cells. Otherwise the candidate stays isolated.

No score or promotion claim is made until the exact hosted workflow report is
available.
