# SOL-LEVEL — TITAN V3 receding reserve-release receipt

- Operation: `titan-v3-receding-reserve-release-20260909-01`
- Starting main: `5c202d3d471e77df2bcbf4add371fa2b8aaaf308`
- Branch: `sol-level-full-shed-feasibility-20260909-01`
- Canonical mutation: **none**
- Provider/Kaggle action: **none**
- Disposition: **DRAFT / NO_SIGNAL**

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

## Factual correction to the first hardening receipt

A prior PR/Slack statement claimed that first head
`01108a7cfa366e71214640885d3b076f9a2b997c` had an indentation defect and only
one discoverable reserve test. That statement was wrong and is withdrawn.
Exact blob readback shows **12 class-level reserve tests**. Together with the
five comparator tests, exact hosted run `34403285293` correctly executed
**17/17 tests**.

Current hardening head `ee077911eda098ee74faee9ecf689f12f0220083`
adds two semantic reserve tests—malformed active-market rows and unsupported
non-24-turn day semantics—bringing that suite to 14. It also adds five
independent strict own-cash tests. It does not repair test nesting.

The immutable message on the intervening commit incorrectly says it repairs
reserve-contract discovery. This corrective receipt supersedes that description
without rewriting history.

## Exact hosted result

Run `34403285293` completed successfully on the first experimental head. Its
paired report contains 8/8 complete development cells against public Arlene and
submitted V1, 5,752 candidate decisions, zero changed traces, and zero score or
margin delta in every cell. Verdict: **NO_SIGNAL**.

That green workflow status is not strength evidence. The mechanism did not
activate on the measured panel. This lane will not consume a larger score panel
without an independent occurrence witness; the already-open expansion child is
owned by SOL-BULWARK.

## Evidence hardening retained

The current workflow requires exact unittest discovery counts of 14 reserve,
five inherited comparator, and five strict own-cash tests. The independent
`strict_gate.py` blocks margin-only apparent gains when candidate own cash falls
or fails to improve, so harming the rival cannot masquerade as Titan progress.

## Owned additive paths

- `revenue/kaggriculture/cloud-execution-lab/candidates/v3-receding-reserve-release/**`
- `.github/workflows/titan-v3-receding-reserve-release.yml`
- this receipt

## Promotion boundary

No canonical runtime, config, archive, release pointer, default, provider, or
Kaggle state changed. `NO_SIGNAL` is the authoritative disposition for this
small panel. This PR remains draft and must not be merged or promoted as a V3
improvement from the available evidence.
