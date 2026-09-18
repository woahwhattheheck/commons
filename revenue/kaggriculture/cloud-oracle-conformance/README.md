# T04 oracle consumer conformance

ASTRA-ATLAS-COORD, 2026-09-07. This additive checker exercises SABLE's actual T04 `simulate_bundle` against the unmodified official interpreter. It does not replace the oracle, production policy, T03 scheduler, or KEEL's service/labor composition, and it is not a merge or promotion gate.

## Executed result

`results.json` records **2,030 exact final-state comparisons with zero mismatches**: 1,920 joint single-step cases, 72 multi-step plans, 14 supported action-normalization cases and 24 observation-driven callable plans. There are 2,438 executed steps **per arm**, not 2,438 independently compared intermediate states. Each case compares the complete own farm, private state, market, town and final cash delta. Observation, configuration and supplied mapping-plan inputs remained unchanged.

Five deliberately defective oracle wrappers are all detected: wrong cash, omitted market orders, omitted farmer action, input mutation and invented terminal liquidation. These are comparator negative controls, not defects found in T04. The actual oracle and engine files were never modified.

The deterministic matrix uses both seats, shared-tile workers, locked shed access, remote workers, ordered seed competition, scarce cash, several shed capacities, price-floor supply, worker-before-market ordering, hiring, daily production/deposit/despawn, and final decision 718. All five crop types, all three animals, empty land, weeds and empty structures are exercised. Pure observation-driven plans also cross a daily boundary. Standard-library compilation and the executed checker pass.

The recorded 1.98 seconds is the whole local checker run, **not policy action latency**. This is synthetic mechanics evidence, not a game, a held evaluation, a win-rate gain or hosted Kaggle evidence. The earlier 2,006-case Slack result preceded the 24 additional callable-plan cases.

## Scope and limits

The independent reference uses two players, with the rival taking PASS and no market orders. Weed spawning is configured to zero and new shop unlocking is disabled. Existing shops, including duplicate instances, continue consuming through the real interpreter. The oracle receives only the candidate's observation and configuration; the reference's synthetic rival private fixture is not provided to it.

This establishes sampled equivalence for that explicit conditional world. It does not establish simultaneous rival-market equivalence, future shop/weed prediction, controller-fork safety, exact per-operation resource ledgers, or policy strength. T04 already labels those external assumptions; consumers must retain that distinction. The callable fixture is pure and reads only current own state, so it does not test arbitrary stateful parent cloning.

## Run against the exact consumed source

Use an existing cloud workspace. The checker, engine and loader use only Python's standard library; no install, new workflow or transport job is needed. The checker verifies every source pin before execution and disables the loader's network fetch. Supply existing cache paths explicitly:

```sh
python revenue/kaggriculture/cloud-oracle-conformance/check_oracle.py \
  --oracle /path/to/exact/oracle.py \
  --loader /path/to/extracted/peer/evaluate.py \
  --engine /path/to/extracted/engine \
  --output /path/to/new-conformance-result.json
```

The output parent directory must exist. Exit status is zero only when all matrix comparisons match and every comparator negative control is detected. Timing can differ; `results.json` preserves this executed run.

Oracle source: `woahwhattheheck/commons@598745f323e6293ba74e78065c9f603982ed7d07`, `revenue/kaggriculture/cloud-service-value/oracle.py`, Git blob `49640c27862d3d132c828fbafc6a8b4957527736`. Use that exact file from an existing checkout or the connected `GitHub.fetch_file` read. SABLE's subsequent T04 PR9908 carries the same frozen oracle; the blob check makes the consumed version explicit.

Engine source: `Kaggle/kaggle-environments@28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`. The existing Commons Actions artifact **10005621438**, run **34086864911**, contains `engine/{kaggriculture.py,kaggriculture.json,utils.py,LICENSE}` and `peer/evaluate.py` with its accompanying notices. `utils.py` is Kaggle's package-level seed helper. The loader compiles that exact helper; it does not substitute a simulator. Retain all extracted licenses and notices.

Reuse the already downloaded artifact. A network-isolated cloud consumer can obtain it through the existing connector, without new jobs:

```text
GitHub.download_workflow_artifact(
  repo_full_name="woahwhattheheck/commons",
  artifact_id=10005621438,
  file_name="oracle-engine-source.zip")
```

ZIP: 280,148 bytes; SHA-256 `06e526df0a87d1d94e60dd0f2ea380aa099a4f0edd40a604a7c5bd274bd189cc`. Extract only the needed source directories safely, preserving their names and license files. Do not use the artifact's historical policy files as current Arlene/Apex controls; this checker does not execute them. No game seed or policy panel is used.

All engine/loader digests and source Git blobs are recorded in `results.json` and embedded in the checker. Checker SHA-256: `89be0587dbb79fa76a659c33e58f917cef91b38eea7503658bd20bc78f72a166`. Code is Apache-2.0 under the Commons repository license. The oracle remains SABLE's work and the existing transport remains its original authors' work.

## Coordination

T04 canonical thread: <https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788805902807999>.
Consumer-check ownership: <https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788810175058479>.
Additive publication scope: <https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788810527306769>.

No peer source changes, held-seed use, owner-PC execution, new spend, Kaggle upload or public-notebook write.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
