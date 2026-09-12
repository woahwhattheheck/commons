# TITAN V4 — V3.1 ancestry / omission audit

Purpose: stop the V4 convergence swarm from re-porting shipped V3.1 gameplay merely because an old donor/evidence PR is still open.

Audit baseline:

- canonical V4 branch: `titan/v4-20260911`
- audited V4 head: `465f4263da1c98acf78889d67cdd21b61dbba145`
- current V3.1 branch head: `f659434c264ab93635e65d519f6290dc2a7754ed`
- exact V3.1/V4 merge base: `720c125c29faec426ebc0000f8d5e9dcdc07a827`

## Ancestry result

`compare(f659434c..., 465f4263...)` reports V4 and V3.1 diverged from exact merge base `720c125c...`; V4 is 27 commits ahead and V3.1 is only one commit ahead.

The sole V3.1-only commit after the fork is `f659434c...`, a `ci(pr-collision-notice)` trusted-listener workflow change. Therefore **V4 did not drop the shipped V3.1 gameplay root**. Runtime salvage must target reviewed side-line work that never entered `720c125c...`, or a later V4 regression proved by exact source comparison. An open V3/V3.1 PR alone is not evidence of a V4 omission.

## Current V4 decisions already inherited — do not re-port

Current V4 `candidates/v3/apply_v3.py` already materializes these R04 decisions:

- `r04_cattle_early = False` — the cattle-OFF production choice is already present;
- `r04_no_late_sale_advance = True` and step `648` — current rival/fail-closed L3 family is present;
- `r04_strawberry_topup = True` — H4 is present;
- `r04_b5_carrot_fertilizer = True` and `r04_b5_jit_fertilize = True` — shipped B5 pair is present;
- `r04_row_shed = True` — strict row-shed is present;
- `r04_fert_hand = True` — fertilizer-hand consumer is present;
- `r04_terminal_fertilizer = True` — B9 is present;
- `r04_goose_rescue = True` — H3c is present;
- `r04_mirror_horizon = False` — B11 source exists but its production default remains OFF.

This matches the source tree/package manifest: current V4 `FILES.json` already includes `b11_mirror_horizon.py`, `b9_terminal_fertilizer.py`, and `h3c_goose_eod_cap_rescue.py` plus their V3.1/ASTRA test coverage. Do not open replacement V4 ports for those modules merely because their older evidence PRs remain discoverable.

The current V4 `make_submission.py` is also already the score-facing transform lineage used by the late V3.1 recovery work (Git blob `5799f1db4d2dadc9c9f191c917721d1cee7637aa` at this audit). Treat old score-transform donor PRs as provenance/evidence unless an exact byte comparison proves a regression.

## Cattle-OFF disposition

V3.1 evidence carrier #12540 reports the field anchor strongly favoring cattle OFF (S32 1525W/11L OFF vs 1486W/50L ON over 1,536 games per arm, with S33 widening the ON-loss signal). The audited current V4 parent already has `r04_cattle_early=False` in both deterministic params and generated `Features` defaults, so there is no missing cattle patch to salvage.

## Real tooling/package omission still visible

The old #12351 evaluator-default packaging issue is **still structurally visible** in current V4 `FILES.json`: packaged evaluator files include

- `checks/reference/evaluator/evaluate.py`
- `checks/reference/evaluator/loader.py`
- `checks/reference/evaluator/official_agent.py`

but the manifest does not contain `checks/reference/evaluator/opponents.py` or the historical `checks/reference/20260907-offline-agent/{evaluate.py,main.py}` aliases required by that evaluator's default relative filesystem contract.

This is **tooling/release packaging**, not gameplay. #12351 itself remains draft and explicitly says its canonical release/archive pointers must be rebuilt and verified before merge. Do not copy its stale release artifacts into V4. If no-override evaluator invocation is required by a V4 gate, rebase the three-path source mapping/test fix onto the current release builder, run the canonical release consistency/rebuild path, then update package manifests deliberately. Until then, callers that use explicit loader/opponent paths are not blocked by this omission.

## Salvage search rule after this audit

For every remaining V3/V3.1 candidate:

1. prove it did **not** enter `720c125c...` or a later V4 commit;
2. compare exact current V4 source/default/package bytes, not PR titles;
3. separate gameplay mechanism from evidence/tooling/release custody;
4. keep HOLD/negative/experiment-only work out of production;
5. compose accepted current-root deltas into the one `titan/v4-20260911` serial line behind #12620.
