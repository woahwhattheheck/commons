# TITAN V3 S13 action-applicability certificate

Operation: `TITAN-V3-S13-ACTION-APPLICABILITY-CERTIFICATE-20260910-01`

This is an additive evidence and adapter-contract child of route experiment PR #11992 and replay-identity child PR #12052. It does not alter the canonical TITAN runtime, archive, tournament outcome, promotion state, provider state, or Kaggle state.

## Finding

The parent route runtime treats a replay prestate as applicable when only two integers match:

```text
(number of farm hands, number of unlocked quadrants)
```

That is a useful coarse trajectory guard, but it is not an action-applicability certificate. The five selected route tapes contribute 3,475 post-day-one source rows. The exact pinned-source audit found:

- 1,826 `(step, structural signature)` groups;
- 806 groups containing multiple selected routes;
- 484 groups containing different complete action bundles;
- 2,556 ordered bundle disagreements;
- 12,492 non-PASS unit-component comparisons under the pinned official executor;
- **5,274 false-applicability witnesses across 285 steps**: a source unit action is active in its own source prestate, is a no-op in another source prestate accepted by the same coarse signature, while that target route's own component is active;
- zero witness collisions under the new own-prestate certificate.

The deterministic first witness is step 49, signature `(4 hands, 1 quadrant)`. Himanshu/Pensukesan/Terry issue main-farmer `FEED`. SpaTaro has the same coarse signature, but the main farmer carries no WHEAT; the pinned official `_apply_unit_action` therefore makes `FEED` a no-op, while SpaTaro's `PICKUP WHEAT 4` is active.

The largest witness classes are not edge-only: `WATER` contributes 1,291 witnesses, `FEED` 839, `CARE` 665, `COLLECT_FERTILIZER` 579, and `HARVEST` 531.

## Certificate contract

`prestate_certificate()` binds the exact replay action plus the state domain read by the pinned engine:

- `units`: complete own farm, own private state, day, and unit-executor configuration;
- `market`: exact market queue, complete own/private state needed by HIRE/BUY_LAND/BUY/SELL, shared market state, and market-executor configuration;
- `full`: both domains.

`step` and `remainingOverageTime` are deliberately excluded. Rival public farm state is excluded because the unit executor does not read it. For market actions, this proves equal own/public prestate only; it **does not bind the rival's hidden simultaneous market queue**, so it is not an exact market-outcome certificate.

A future runtime adapter can embed the source certificate beside each tape row and permanently hand off to the baseline on mismatch:

```python
expected = tape[str(step)]["prestate_certificate"]
if not certificate_matches(expected, obs, configuration, source_action, seat=obs["player"]):
    handoff = True
    return baseline_action
```

The current positive Pensukesan panel remains valuable as schedule-transplantation evidence. It must not be described as source-equivalent route imitation until an adapter using this or a narrower formally justified certificate is re-evaluated.

## Exact evidence

Inputs:

- source-pin manifest SHA-256: `4a9b56673469fec0caab053a8bdf2724ff859087ae03326836a0ce552d30d5cc`;
- six replay objects: 195,114,984 bytes, each checked against the manifest before route-row extraction;
- pinned official `kaggriculture.py` SHA-256: `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`;
- oracle: exact `_apply_unit_action` loaded only after engine digest verification.

Outputs:

- `CORPUS-RECEIPT.json` SHA-256: `fcb672c7e72de7f77b6d5d30bce69c2703943c78c763e96987c99b293b6cb0ff`;
- complete witness-set SHA-256: `c90ac034a91ea1dac873fb4b805015d96abfe9691a05f00a4882a477a2712d1a`;
- 13 focused predecessor/contract tests: PASS.

Reproduce after obtaining the six exact replay JSON objects and the pinned official engine:

```bash
python -m unittest -v test_action_applicability.py
python action_applicability.py \
  --replay-dir /path/to/exact/replays \
  --source-pins ../titan-v3-s13-leader-route-distillation-sol-pro/SOURCE-PINS.json \
  --engine /path/to/pinned/kaggriculture.py \
  --engine-sha256 bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e \
  --output CORPUS-RECEIPT.json
sha256sum CORPUS-RECEIPT.json
```

The audit fails closed on replay hash/byte/frame/team/reward drift, engine hash drift, duplicate/nonfinite JSON, malformed action rows, player/seat mismatch, and any false-applicability witness not separated by the certificate.
