# V5 V3.1→V4 E14 shed-projection causal ablation

This package answers one narrow causal question: **did E14's mechanically-correct pre-market shed-overflow projection contribute to submitted V4 scoring worse than submitted V3.1?** It is evidence plumbing for the single V5 line, not a competing runtime or a rollback recommendation.

## Exact identities

Control is the submitted V4 archive, SHA-256:

`4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b`

Submitted V4 source is `4af1113154e78c662780e6658cd920daac7902e3`. Its `scheduler.py` is Git blob `a483b24dd72b580d7d8811636b54d2d44f391575`, introduced by E14 commit `0cd11d4f66fb7df078d7a0b3487220749db5ec25` ("Fix E14 shed overflow timing in scheduler projection"). The immediate parent is `e4e0fe6a5207c986a165e0db8b1671a5fa034779`, whose scheduler is Git blob `d68ae8bbeb0d6efb437770c08fbcc3e2da4f54ff`.

The treatment is **exact submitted V4 with only that scheduler member replaced by the immediate pre-E14 blob**. Every other archive member remains byte-for-byte and mode-for-mode unchanged.

This matters because submitted V3.1 (`a90d888f03987ef0b35cfd20ec3519c6144db08a`) and submitted V4 use the same active Arlene producer bytes: `reference/next-panel/vendor/arlene.py` is Git blob `bdb9cf58148a3c7961c085f4902759537decabf6` in both. The strong 13-tape R04 experiment is therefore a valuable *new V5 producer replacement*, not a causal restoration of the submitted V3.1 producer. E14 is an actual active-wrapper semantic delta between the submissions.

## What E14 changed

Before E14, seller feasibility started from the already-capped post-unit shed and pre-subtracted other current-turn sales before recording the current pre-market capacity checkpoint. That could make a same-turn market sale appear to rescue unit cargo that the engine had already discarded during the earlier unit stage.

E14 corrected the model by re-running the current unit stage with an unbounded shed **inside the projection only**, recording attempted arrivals before market relief, and rejecting true current unit-stage overflow before applying same-turn sales. The executable game state remains engine-capped.

That ordering is physically correct. Therefore:

- `control > treatment` supports keeping E14 and rules it out as the score regression;
- `treatment ≈ control` makes E14 cold for the submitted gap;
- `treatment > control` is a diagnostic signal that E14's stricter feasibility changed seller choices adversely. It **does not** authorize restoring impossible same-turn overflow rescue. The next step would be to inspect the action-diff cells and implement a physically correct planning rescue (for example, a producer-owned defer-DROP/EOD continuation where official timing proves it legal), then re-evaluate that new repair.

## Materialization

The builder never imports or executes candidate archive code. It:

1. reads the V4 archive once and verifies its exact SHA-256 before tar parsing;
2. rejects traversal, duplicate, symlink/hardlink/device or other non-regular members;
3. authenticates the V4/E14/pre-E14 scheduler and V3.1/V4 Arlene identities against a full Git checkout;
4. captures the pre-E14 scheduler by exact Git blob object;
5. finds exactly one control scheduler blob and exactly one held-constant Arlene producer blob in the authenticated archive;
6. proves exactly one member changes;
7. only then creates a fresh output directory and emits `E14-CAUSAL.json` with source/archive/blob/tree identities.

Example:

```bash
python -B compose_e14_off.py \
  --archive /path/to/exact-v4-submission.tar.gz \
  --output /tmp/titan-v4-e14-off \
  --repo-root /path/to/commons
```

The output directory is treatment evidence only. It never changes `TITAN-CONFIG.json`, runtime defaults, `CURRENT`, release authority, or Kaggle submission state.

## Game screen

Use the pinned official engine/evaluator and matched opponents, seeds and seats. Start cheap with the known gap cell (Arlene, seed `2051966578`, both seats where available) plus the current fresh `5501–5504` panel. If E14 engages sparsely, expand on the existing balanced panel rather than selecting only favorable cells.

For each complete matched cell report at least:

- control and treatment own score, rival score and margin;
- treatment-minus-control deltas for all three;
- first returned-action divergence and number of divergent callbacks;
- seller chosen-plan/forced-feasibility changes if trace instrumentation exposes them;
- E14 pre-market overflow-rejection engagements and physically discarded-unit differences when available;
- V3.1 champion score only as context, never as part of the causal treatment identity.

A treatment result is non-authorizing if archive, engine, evaluator, opponent, seed, seat or output receipt identity is missing.

## Source contracts

```bash
python -B -m py_compile compose_e14_off.py test_compose_e14_off.py
python -B -m unittest -v test_compose_e14_off.py
python -O -B -m unittest -v test_compose_e14_off.py
```
