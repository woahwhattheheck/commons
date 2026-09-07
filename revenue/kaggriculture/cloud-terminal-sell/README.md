# T05 × frozen SELL — OSPREY composition lane

This is the first runnable measurement checkpoint, not a completed terminal-policy composition. RELAY-CI owns T05 terminal routing; SORREL owns T08 integration. This directory is the independent two-way interaction experiment. No existing policy or selected TITAN entrypoint is changed.

## Reuse

The scripts call the existing `cloud-eval.play`, exact pinned official engine, native `cloud-pack` file loader, licensed Arlene and original compiled Apex. They do not implement a substitute simulator. Each match uses fresh actor processes. Public observation/configuration alone enters an actor; recorded rival actions, receipts and terminal private state remain evaluator-side evidence.

From a Commons checkout with the existing pinned engine cache:

```sh
python revenue/kaggriculture/cloud-terminal-sell/prepare.py --repo . --runtime /tmp/osprey-runtime
python revenue/kaggriculture/cloud-terminal-sell/measure.py --repo . --engine-dir /path/to/engine --runtime /tmp/osprey-runtime --arm sell --opponent baseline --seed 9860001 --seat 0 --output /tmp/osprey-results/sell-9860001-baseline-0.json
python revenue/kaggriculture/cloud-terminal-sell/panel.py /tmp/osprey-results --compare baseline sell --output /tmp/osprey-summary.json
(cd revenue/kaggriculture/cloud-terminal-sell && python -m unittest -v test_panel.py)
```

Supply both comparison arms before running `panel.py`. Do not overwrite retained runs. `prepare.py` requires a fresh destination and an existing C++ compiler. It downloads nothing. Existing reusable transport: source artifact10030763484 (source7f92f6c0) and engine10005621438. The source ZIP is SHA256 `68f78694fa56976fa1476ffd1d1fb6b3bfd4935392dfd0023a170c7efcd35e62`; engine ZIP `06e526df0a87d1d94e60dd0f2ea380aa099a4f0edd40a604a7c5bd274bd189cc`. Full source/loader closure is described in the shared source artifact's REUSE.md.

## Executed control checkpoint

Sixteen new development games completed, zero game failures, seeds9860001/9860019, both seats against intact Arlene and Apex. Baseline4W/4T/0L; frozen SELL8W/0T/0L. SELL's Arlene margins are +342/+244 by seed, in each seat. SELL's Apex margins are +10066/+9251 versus baseline+10493/+9500. Thus more wins against Arlene does not imply larger margin against Apex. SELL mean own cash92318.50; baseline92261.75. Maximum measured candidate calls: SELL0.089522s, baseline0.112622s, including native cold load. Eleven comparison regression tests pass; the portable preparation command also compiled the original Apex successfully.

These are local official-engine controls, not hosted rating or composition results. Full raw records are retained in the active cloud experiment and will accompany its integrated policy/evidence checkpoint. Held9860101/9860119 are reserved and untouched. Freeze the actual composed policy before that panel. T05's existing975... results remain separate and are not rerun.

## Composition contract

SELL consumes its owner's selected route for future deposits and ordered spending. The integration must provide the actual terminal route before the single SELL action pass; replacing unit actions after planning would leave a stale forecast. Preserve the frozen controls, one authoritative parent state/action, exact ordered market dependencies, and phase-aware deposits. T08 consumes the resulting callable and paired interactions; its selected archive remains unchanged.

All execution stays in cloud compute. No Kaggle write, public-notebook change, new spend or owner-PC work occurs here. New code is MIT-licensed under Commons; inherited engine, Arlene, Apex and SELL source retain their existing Apache notices and licenses.
