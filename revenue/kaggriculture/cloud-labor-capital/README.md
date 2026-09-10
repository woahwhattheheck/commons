# T10: marginal hiring and operating capital

ASTRA-DOCK's additive research component for the [T10 assignment](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788805939641689). This is not a Kaggle upload, current-TITAN replacement, payment result, or general win-rate claim.

## Measured result

The frozen `reserve` policy adds **5 game dollars** in every tested paired case. It removes the second HIRE order at decision 121 (the fifth hire that day, costing 5) after evaluating the incumbent's actual remaining shift. No fixed worker cap or step-121 special case exists in the policy.

| Panel | Control | Reserve | Own cash versus paired control |
| --- | --- | --- | --- |
| Development, 8 games per arm | 4 wins / 4 ties | 8 wins | +5 in all 8 cases |
| Held, 8 games per arm | 4 wins / 4 ties | 8 wins | +5 in all 8 cases |

Both panels use intact Arlene and Apex in both seats. Development also tests `timed` in 8 games: its actions, scores and traces match reserve. It was not selected for held testing. Development seeds: 9800001, 9800019. Held seeds: 9800101, 9800119. The source selection and hashes were posted before held execution; see [FREEZE.json](evidence/FREEZE.json).

All **40 completed games** execute 719 decisions with no runtime failure. All final farm, private inventory and market state, excluding money, equals the corresponding control. The separately recorded first attempt stops at decision 122 because the old passive measurement hook indexes an unhired worker; it is an unscored observer failure, not omitted from the record or counted as a game loss.

Maximum reserve calls: 465 ms development and 502 ms held, with a parent-enforced 1-second limit and no overage. Timed peaks at 505 ms in development. This is significant computational cost for a small gain; hosted timing and broader-opponent performance remain untested. The sample does not establish a population win rate.

[RESULTS.json](evidence/RESULTS.json) contains all 40 game rows, scores, trace hashes, hire/wage totals, source pins, runtime environment, test counts, and failed-attempt details. It is a compact result record, not the complete per-game observation trace. Full raw JSON reports and a decision-121 observation are retained in the accompanying session evidence bundle; their hashes are recorded in RESULTS.json.

## Mechanism and interface

```python
policy = HiringAgent(intact_arlene.Agent(), official_engine, mode="reserve",
                     configuration=public_configuration)
action = policy.act(observation)
```

`project_shift(engine, observation, parent_after_call, first_action, configuration)` returns a `Projection`: conditional cash, after-market minimum cash, exact hiring outflow, net non-hire cash flows, productive/input state, market inventory, actual first-spawn positions, horizon, and whether only terminal cash matters. The parent must already have advanced through the current call.

The policy compares the intact action with progressively omitted suffixes of the current hire orders. Omitted orders become zero-quantity SELL slots rather than disappearing, preserving lockstep positions. `timed` additionally evaluates moving hires behind non-hire orders **within the same market phase**; it is not a general multi-turn deferred-hiring scheduler.

The rollout uses official unit, market, production, decay and ordered-overflow helpers. Future incumbent actions are recomputed from each projected observation, including its actual shed contents, rather than freezing previously clamped sale quantities. Atomic seed demand includes nonexistent taped hand slots, matching the interpreter. Hires spawn after unit actions and cannot work until a later decision.

Before final settlement, an alternative must improve projected cash while preserving the complete own productive/private state and market inventory at the daily boundary. This prevents calling lost seeds, assets or stock free wage savings. It is deliberately conservative and can reject genuinely valuable alternatives; equality is not a universal economic valuation rule. At the actual last decision, 718, only settled cash is valued.

The forecast assumes current visible shops and zero future rival orders. It stops before unknown next-day weed/shop draws and never reads the hidden episode seed. **Actual evaluation games use both real opponents' actions and the unmodified complete interpreter**; they do not use the forecast's zero-rival scenario.

## Reproduce in an isolated cloud workspace

Inputs are Commons `8329e78768906dc6e75ca3712e1690adc1ab2148` and official engine `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`. The validated [source-pack workflow](https://github.com/woahwhattheheck/commons/blob/87864c8b1f12045313adc15302e98efaec2f480a/.github/workflows/astra-dock-t10-sourcepack.yml) copies these immutable inputs, licenses and hashes. Its successful run is 34155188751, artifact 10030711718. The artifact has one-day retention; the committed workflow is the reconstruction recipe, not a promise of permanent artifact availability. It can be rerun through the existing public-repository workflow. No owner-PC work, paid runner, deployment, or Kaggle credential is needed.

After extracting that verified source pack to `$PACK` and checking out this source to `$T10`:

```sh
export T10_SOURCEPACK="$PACK"
python "$PACK/commons/revenue/kaggriculture/cloud-frontier-policy/next-panel/prepare.py" --runtime "$RUNTIME"
python "$T10/prepare_local.py" --sourcepack "$PACK" --runtime "$RUNTIME"
(cd "$T10" && python -m unittest -v test_labor_capital.py test_engine.py)
python "$T10/run_panel.py" --sourcepack "$PACK" --runtime "$RUNTIME" --seeds 9800001,9800019 --output development.json
python "$T10/run_panel.py" --sourcepack "$PACK" --runtime "$RUNTIME" --seeds 9800101,9800119 --variants control,reserve --output held.json
```

Use a new runtime directory for the existing baseline preparer. It compiles Apex with the preserved source and compiler flags. T10's builder checks source-pack hashes and uses the existing official file-loader adapter and offline network/exec restrictions. Generated adapters contain local absolute paths; regenerate them after moving the workspace. Standard evaluator observations include `step`. All 29 tests passed: 18 contract tests, 10 pinned-engine cases, and one missing-worker observer regression.

The seeds above are now spent for development of subsequent policies; rerunning them is a reproduction, not a fresh held evaluation. Reserve a new unused bank for changed candidates.

## Composition and next discriminating work

`_clone_parent` is a shallow copy validated for intact Arlene's immutable route/cache layout. **Do not directly wrap a nested T03/T04 controller and assume it is forked safely.** Such composition needs explicit independent controller-state cloning. Arlene source and route tapes remain unchanged.

T04's separately reported service intervention at decision 592 is distinct from T10's observed intervention at 121, but additive gains are not established without a composed run. A useful next experiment is to replace repeated full-shift projections with observation-validated task/value caching, then test preserved actions, terminal cash and timing. Another is to price differing productive terminal states with the T03/T04 oracle rather than rejecting all differences. Neither improvement is claimed implemented here.

## Attribution

Commons source and these additions are covered by the repository's Apache-2.0 license. Arlene / lynnsakurai's complete controller, routes, guards and sale scheduling are reused, not authored by ASTRA-DOCK; original SHA256 `1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4`. Apex and the official Kaggle interpreter are preserved from the source-pack references. The existing distribution's full licenses, notices, upstream metadata, loader, evaluator and compiler sources remain in the pinned source pack. T10 does not edit peer paths or redistribute stripped vendor source.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
