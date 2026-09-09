# Titan v3 official-shadow differential oracle

This lane is an admission gate, not another controller heuristic. It captures the
small engine rules that repeatedly invalidated Titan v2/v3 experiments before a
game could count, produces deterministic counterexamples, and shrinks the most
important shared-resource mismatch to a two-action fixture.

Pinned source closure:

- Commons base: `9519f3b9b6a970c12ee37c64abb3e8e2246d53e1`
- Upstream Kaggriculture engine commit: `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`
- Preserved official engine blob: `3c202c7ee921da239356789e266b694635103fc4`
- Extracted mechanics blob: `044a4f9c0a4a44dde10ada57563238bcaf82075d`
- Live negative control: PR `#11127`, head `cce9e8e94211706d95e21325c54d121cebc16e11`

## Contracts

The gate checks:

1. **Atomic same-crop PLANT blocking.** Two workers requesting one available
   WHEAT seed cause *both* requests to become PASS. Sequential worker shadows
   incorrectly plant once.
2. **Raw market-prefix truncation.** `maxMarketOrdersPerTurn` is applied before
   malformed orders are parsed. A malformed head still consumes a slot.
3. **BUY_PRODUCT domain.** Only WHEAT and FERTILIZER are legal products.
4. **Exact shed-cap boundary.** A deposit ending exactly at capacity is legal.
5. **Two-player pre-commit market quotes.** Both players see the same inventory
   for each lockstep unit before either commit mutates inventory.
6. **Malformed action normalization.** Non-list hands and market values become
   empty lists; missing hand actions have PASS effect.
7. **Post-state activation.** A syntactically non-PASS action with no state
   change is not evidence of a candidate activation.

The live probe deliberately runs the exact `_apply_unit_action` primitive in the
one-worker-at-a-time pattern used by the active S01 beam adapter. The oracle must
observe a mismatch; if it does not, the negative control or source pin drifted.
This turns a Slack diagnosis into an executable predecessor discriminator.

## Run

From this directory:

```bash
python3 -B -m unittest -v test_official_shadow_oracle.py
python3 -B run_oracle.py --output /tmp/titan-v3-official-shadow-oracle.json
```

`run_oracle.py` verifies the mechanics git blob before importing it. The report
contains source identities, per-rule status, minimized fixtures, fingerprints,
and a deterministic evidence hash. `fixtures/expected-evidence.json` is the
reviewable golden receipt; tests fail when a rule, source identity, minimized
fixture, or fingerprint changes. No controller, evaluator, archive, candidate,
submission, provider, or Kaggle state is mutated.
