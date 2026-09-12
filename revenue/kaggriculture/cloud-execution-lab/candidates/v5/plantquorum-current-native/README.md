# TITAN V5 PLANTQUORUM current-native engagement gate

This directory is an evidence-only current-V5 closure for the already-merged canonical PLANTQUORUM theorem from `candidates/v4/research/unit-phase-chaining/plant_quorum_admission.py`.

It does **not** add a runtime feature, config key, production hook, composition edge, archive member, default, or Kaggle behavior.

## Question

Does current V5 naturally return a unit vector where the official engine's callback-wide same-crop PLANT preflight blocks all plants **only because** one or more authored PLANT rows are source-certain no-ops (missing actor or a unique actor on a non-empty tile), while at least one other authored PLANT is guaranteed legal on a unique empty tile?

The canonical helper may remove only those poison rows. Co-location, insufficient poison removal, zero seeds, malformed state, or any need to choose between legal plants fails closed.

## One evidence stack

- `census.py` is the single low-level observer boundary. It authenticates the canonical theorem and exact engine bytes once, keeps the returned control action detached from the hypothetical candidate, and requires any claimed change to alter the engine's atomic-PLANT preflight while leaving an effective PLANT survivor.
- `plantquorum_census.py` is the archive-bound runner. It authenticates current V5, loads `census.py` as a pinned snapshot, executes exact current V5 against the official starter agent, and records observer hits without ever applying candidate bytes to gameplay.
- `test_census.py` owns theorem/observer behavior tests. `test_plantquorum_census.py` owns current-package custody and strict panel aggregation tests. The layers intentionally do not maintain two theorem implementations.

## Custody

The runner pins and snapshots:

- current V5 archive SHA-256 `fe67d2daa00ba84348ef364db3b6dea9671d6b01349001e51546874e277adec3` from source commit `b9d696d4dd803bc0345f73cdd52cc35346f503f6`;
- its `SOURCE.json` SHA-256 `8182785b03f3c771901d6124d11b7e04d37c1ddcaabf6174d9748227a91c5526` and 116-file runtime closure;
- packaged official engine Git blob `3c202c7ee921da239356789e266b694635103fc4`;
- packaged `main.py` Git blob `9cf8feaa9a755ffdf85d8878baa07b1fc7940192`;
- packaged `TITAN-CONFIG.json` Git blob `ef0bfb1dfa1ce65103a0b178647fc16bc9c7e791`;
- observer Git blob `0d55822177714a4df22d5dc9084441d02d4319ae`;
- canonical PLANTQUORUM helper Git blob `15c24fbe305dfb7b4b1b2c39897af4af9b49f31f`;
- reviewed generic native-census custody loader Git blob `27ec7f411b0da36aeeecab2729d5d65adcf81dd2` plus its authenticated support dependency.

Archive bytes are read once, authenticated, and extracted from that immutable buffer. The native runtime is then revalidated from its manifest before execution. The observer authenticates the canonical theorem against the exact engine bytes extracted from that package.

## Method

One process runs one seed/seat. The player under observation uses exact current V5; the rival uses the official engine starter agent. For every current-V5 callback, the observer evaluates PLANTQUORUM on private copies only. A hit counts only when:

1. the helper reports an exact-bool change;
2. the baseline returned action is unchanged by observation;
3. the candidate differs from baseline;
4. the canonical engine-preflight result changes; and
5. at least one effective PLANT survives after source-certain poison removal.

The **original current-V5 action** is always the action passed to the official interpreter. Candidate and detached control copies are evidence only.

Fixed panel: seeds `17,101,6607,9922999,2026091201,2026091207,2026091213,2026091219`, both seats, exactly 719 observed callbacks per cell.

Example:

```bash
python -B plantquorum_census.py cell --seed 17 --seat 0 --output cell-17-p0.json
python -B plantquorum_census.py aggregate --output panel.json cell-*.json
```

Run cells in separate processes. The strict aggregator rejects missing/duplicate coordinates, source or archive drift, truncated cells, bool counter aliases, non-finite scores, and any cell claiming that candidate bytes were applied to gameplay.

## Interpretation

- `ENGAGED_CURRENT_NATIVE_STARTER`: natural witnesses exist. Next gate is matched official-engine baseline-vs-PLANTQUORUM economics against stronger pinned opponents. It is **not** an EV result and does not authorize a production hook.
- `NO_STARTER_ENGAGEMENT`: the fixed starter-opponent panel had zero hits. Widen natural engagement search before calling the lane globally cold.

Any future runtime carrier must be a separate, evidence-authorized step on current main. Do not infer activation from this directory.
