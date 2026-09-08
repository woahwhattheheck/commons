# Current TITAN 87d7 — responsive-opponent development shard

This packet evaluates the exact canonical TITAN archive against the frozen T09 observation-only stress set on one previously unused development seed (`9969137`) in both seat orders. It changes no controller, feature default, CURRENT pointer, canonical archive, workflow, or provider state.

## Result

- Independent seeds: **1**
- Opponent definitions: **5**
- Mirrored seat records: **10**
- Completed: **10 / 10**
- Current TITAN: **10W / 0T / 0L**
- Failures/timeouts: **0**
- Maximum candidate call: **0.319577 s**
- Maximum candidate evaluator RPC: **0.443162 s**

The ten seat records are not ten independent samples. They are five opponent definitions on one seed, each mirrored across both seats.

| Opponent | Direct changed turns | Current cash | Rival cash | Margin | Result |
|---|---:|---:|---:|---:|---:|
| intact Arlene | 0 | 117,312 | 117,036 | +276 | 2W |
| intact Apex | 0 | 117,585 | 115,447 | +2,138 | 2W |
| Arlene + sale cadence | 122 | 104,723 | 14,090 | +90,633 | 2W |
| Apex + crop-demand filtering | 20 | 121,763 | 106,976 | +14,787 | 2W |
| Arlene + labor cadence | 54 | 181,040 | 0 | +181,040 | 2W |

## Paired stress effects

Each stress result is paired with its intact parent on the same seed and candidate seat.

| Variant | Δ current cash | Δ rival cash | Δ margin | Outcome |
|---|---:|---:|---:|---|
| sale cadence vs intact Arlene | −12,589 | −102,946 | +90,357 | W→W |
| crop demand vs intact Apex | +4,178 | −8,471 | +12,649 | W→W |
| labor cadence vs intact Arlene | +63,728 | −117,036 | +180,764 | W→W |

These variants are deterministic stress transformations, not calibrated stronger opponents. Sale cadence and labor cadence can severely damage the parent policy. Their large margins should not be interpreted as estimates of hosted strength.

The crop-demand case is the most discriminating responsive result on this seed: the variant filtered **20** parent decisions and produced **35** total rival-action divergences, while all **719 current-TITAN actions remained byte-equivalent** to the intact-Apex game. The different market flow increased current cash by 4,178 and reduced Apex cash by 8,471.

## Exact identities

- Canonical archive SHA-256: `87d7b8bf7c4e9467f4b6b46887abe2eb03735c42453cdbf4f2cac12c5962acc7` (292,007 bytes)
- Candidate `main.py` SHA-256: `a4ecdb513b48fa51877fe509597a84dd753dfe71d2d76a406ee3dc51475a9008`
- Arlene SHA-256: `1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4`
- Apex `main.py` SHA-256: `1f7cd5fb8a16585936d2562a3667f85bb6661688718ef58f73006de66148354a`
- Apex compiled bridge SHA-256: `859857b1e6139026460fd50ee83bfe9022d4f73f01c40b7cca4aeea4d9af673c`
- T09 `variants.py` Git blob: `374a23ffb3cf6cc1c67571df74fde9f84467e832`
- T09 `variants.py` SHA-256: `69df8c159d8f0b48377052d1637c49727ec551a8774f9f0215984fa89acd0746`
- Official engine pin: `kaggle/kaggle-environments@28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`

## Execution and interruption recovery

The first aggregate invocation completed the four intact Arlene/Apex records before its outer execution command timed out. No policy, engine, or actor failure was returned. The final panel used five source-identical per-opponent checkpoints. The four intact games were reproduced; their decompressed 719-row action/economic traces match the interrupted run exactly.

`run_responsive_shard.py` is the corrected reusable runner. It writes `PARTIAL.json` atomically after every game. `--resume` verifies source identities and every retained trace hash before skipping a completed cell. The test suite retained in the evidence packet proves that a modified score is rejected by the result verifier and a modified trace is rejected by resume validation.

## Verify

```bash
python -B verify_result.py \
  --results results/RESULTS.json \
  --trace-dir /path/to/evidence/traces \
  --output /tmp/current-87d7-responsive-verification.json
```

The verifier binds all source/archive/engine identities, ten complete games, trace hashes, active variant counts, seat-normalized candidate actions, economic/status/reward symmetry, paired cash effects, the unchanged crop-demand candidate tape, and the four reproduced intact traces.

Two parent actions differ across the otherwise economically mirrored variant seats: sale cadence step 693 (`COLLECT_FERTILIZER` versus `DIG`) and labor cadence step 676 (`HARVEST` versus `DIG`). The verifier binds these exact exceptions rather than claiming complete opponent-action symmetry. Candidate actions and the full bank/status/reward streams remain mirrored.

## Reproduce

```bash
python -B run_responsive_shard.py \
  --evaluator /path/to/cloud-eval/evaluate.py \
  --loader /path/to/offline-agent/evaluate.py \
  --engine-dir /path/to/pinned/engine \
  --candidate /path/to/extracted-87d7/main.py \
  --arlene /path/to/arlene.py \
  --apex /path/to/apex/main.py \
  --variants ../cloud-opponent-league/variants.py \
  --archive /path/to/titan-current.tar.gz \
  --seed 9969137 \
  --output-dir /tmp/current-87d7-responsive
```

After an external interruption, rerun the same command with `--resume`. This is cloud development evidence, not a hosted leaderboard result or a claim of statistical generalization.

## Durable evidence packet

Library path: `/TITAN-ALDER-current-87d7-responsive-9969137-20260908.zip`

- File ID: `file_00000000331081f5b6271f4fe574df71`
- Library file ID: `libfile_8e9d575726948191af4facaf591f9e96`
- Bytes: `773866`
- SHA-256: `4f28fa3ff708ef68b60720256e2c6ee6d392e65bb88a1ca20897d9d7c7795317`
- Internal package manifest SHA-256: `78d1f3b579d0f5eb168a8b35ef7a51359d58a64939bff0c39bb739d9f57d62ee`

The repository keeps the runnable source, exact machine summaries, and verifier. The Library packet retains the ten full ordered-action traces, interrupted-run reproduction traces, canonical archive, engine, evaluator, loader, opponent sources, licenses, and test logs.
