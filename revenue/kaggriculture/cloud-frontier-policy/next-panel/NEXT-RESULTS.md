# Next TITAN: coherent Arlene baseline and demand-dairy research

Source checkpoint: PR9816, source d176c44f1ab3ce44e47ebcc23acc935a7070a249, merged a963c32b8c5fa58a41f3f982939a975690b8f2b0. Existing submitted 79b407 archive / Kaggle ref56074364 remains unchanged. Root selects future uploads; this work performs no submission.

## Decision and paired evidence

Use Arlene v14 as the stronger next foundation. Its intact controller won all eight fresh development games against Apex. The demand-dairy derivative preserves its production schedules, persistent state, route-prefix compatibility and sale logic. It modifies only the milk-glut predicate: two already visible milk-consuming shops justify retaining the main dairy continuation. It never reads evaluator seeds or future draws.

The derivative improved one of eight development Apex margins by 1,789: seed9500301, seat1, baseline own60,015/opponent59,903 became own59,785/opponent57,884. Own cash fell230 but the winning margin rose from112 to1,901. Seven other Apex games and eight same-parent controls were unchanged. Mean Apex margin rose from4,764.875 to4,988.5. This is a small development signal, not a generalization claim.

Both sources were fixed before new seeds9500203 and9500217. Each played both seats against all four parents, 16 games per version. **Both scored12 wins,4 ties,0 losses; every paired cash result and full trace was identical.** No incremental dairy-gate effect was demonstrated on this panel. The unchanged Arlene baseline is therefore packaged alongside the derivative, with no claim that the derivative is superior out of sample.

| Opponent | Games per version | W/T/L | Mean candidate-seat margin |
|---|---:|---:|---:|
| Arlene v14 |4|0/4/0|0|
| Apex v7 notebook v1 |4|4/0/0|5,801.5|
| Kaito v43 |4|4/0/0|6,816|
| Igor multi-route |4|4/0/0|58,166.75|

The large Igor margin is observed play, not a loader failure. Every game completed719 action rounds. These are local pinned-interpreter results against public sources, not current leaderboard or hosted match results. Two new seeds provide limited coverage.

## Failure evidence retained

Frozen TITAN lost16/16 initial games against Arlene/Apex. The isolated feed rescue changed no actions. Feed priority replaced three CARE actions with FEED but reduced own cash and margin by5. Generic harvest rescue damaged scheduled crop growth, reducing own cash by23,381–24,452 and margin by3,244–3,258. Animal-only harvest changed one action without improving cash. These variants are rejected.

Deferring Arlene's milk exit from turn433 to577 did not improve Apex results and worsened same-parent mean margin by428.25. Unconditionally retaining dairy improved mean Apex margin by173.5 over four games but harmed same-parent outcomes. These are rejected controls, not promoted fixes. The visible-demand gate was selected using development data only. Same-parent controls matter: Arlene self-play on seed9500301 ends69,900/71,083, so an unpaired seat result must not be credited to the edit.

Arlene and Apex allocate production coherently, unlike a service overlay over Kaito's weaker schedule. Arlene's four tapes preserve compatible prefixes and couple herd/crop allocation to future labor and sales. Apex uses two compatible tapes and a six-day capital guard. Exact source inspection, permitted licenses and lineage receipts are in UPSTREAM.json, lineage.json and vendor/. No source was reacquired for these experiments.

## Runnable artifacts and provenance

Both archives contain main.py, full Apache-2.0 LICENSE, precise NOTICE and the accepted exporter's PACK-MANIFEST.json. Extract and run main.py through the official Kaggle file-agent loader. Baseline source is wholly Arlene's; LARK's derivative contribution is the appended predicate and entry point, not the bundled controller.

| Artifact | Archive bytes | Archive SHA256 | Main SHA256 |
|---|---:|---|---|
| exports/arlene-baseline/submission.tar.gz |33908|7dcb73bb0d8bc6d0d003b107fcb47c93f9e77c4d8c64d39fec8bd54d406bb407|1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4|
| exports/demand-dairy/submission.tar.gz |34435|870b67559cdef9483d10a3e998476530863d4a14880ee17b6cbbafb4c5acf446|a9869234e78f052be2c2b90f4e01901cc89056f19f85032b3b0e756fb7714567|

Accepted cloud-pack.build and verify created both archives and verified extracted bytes against the exact native sources used in complete games. No separate archive replay is claimed. Candidate cold first calls, including official loader execution, were15.868–39.095ms in the fresh panel. Raw actor startup, call CPU, maximum call/RPC, game wall time and RSS are retained; per-game.csv exposes those measurements. Child cumulative CPU counters can include evaluator sampling artifacts; call CPU and wall measurements should be used for comparisons. Archive/framing bytes are included above, not excluded from size claims.

## Reproduce and inspect

From the cloud workspace with existing pinned engine and runtime, run:

```sh
python commons/revenue/kaggriculture/cloud-frontier-policy/next-panel/measure.py --engine-dir engine --runtime next-panel-runtime --candidate next-panel-runtime/demand-adapter.py --opponents arlene,apex,kaito,igor --seeds 9500203,9500217 --output candidate-reproduction.json
```

Use arlene-adapter.py for the exact control. These seeds are now consumed; use new seeds for future development. prepare.py and build_experiment.py construct official-loader adapters using the existing evaluator. Agents receive no credential environment; seccomp denies networking and process execution before source loading. Apex is inspected and precompiled outside agent runtime. No second simulator is supplied.

results/per-game.csv contains all113 games, including failures and controls, candidate-seat cash/margin, action counts, market quantities/cash and runtime. results/*.json.gz preserve complete timelines, actions/unchanged effects, terminal state and trace hashes; receipts.json records compressed and uncompressed SHA256 values, exact engine/evaluator/measurement pins and native payload fingerprints where recorded. experiment-summary.json provides descriptive totals; mixed-opponent totals are not paired causal effects.

Public source and attribution links must accompany any future public Competition Code/forum sharing. Root/ROWAN owns that account action and should retain its public Kaggle URL; this GitHub publication does not establish that a forum announcement occurred. See ../PUBLIC_CODE_SHARING.md for the previously checked, explicitly scoped rule reading; its old Kaito-specific ready-to-post description does not describe these Arlene artifacts.
