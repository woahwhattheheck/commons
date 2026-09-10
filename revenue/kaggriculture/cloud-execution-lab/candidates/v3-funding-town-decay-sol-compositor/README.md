# TITAN V3 authenticated town → decay composition

Operation: `TITAN-V3-FUNDING-TOWN-DECAY-AUTHENTICATED-COMPOSITION-20260910-01`

This additive carrier closes the exact composition blocker reported against PR
#12075: the town-consumption donor (#12053) and plant-decay donor (#12075) each
authenticate only the pristine `frozen_selected.py`, so either donor's ordinary
CLI rejects the other's postimage. The former synthetic ordering test called a
raw patch helper and did not prove donor-head ancestry, intermediate receipt
custody, or production-consumer reachability.

## Exact inputs

- base main: `6f6f2f0fefd972050dbfa4c4d1ccbb1a9fe67701`
- town donor: PR #12053, head `e701b8bf348b8ccacda854722d1e510cfd3c67c6`
- decay donor: PR #12075, head `30d9d09561a07e3f9eef2c7128b6139bf0acdea7`
- pristine `frozen_selected.py`: Git blob `fc7baf5c179818a55037f6a61d92984d81d1a21c`
- scheduler: `a483b24dd72b580d7d8811636b54d2d44f391575`
- runtime mechanics: `044a4f9c0a4a44dde10ada57563238bcaf82075d`
- official interpreter: `3c202c7ee921da239356789e266b694635103fc4`
- selected runtime: `b952c9c228ecbde592bf3d2df01638677abb0d24`
- selected config: `3a3bef83899d3010fad623b628d9e95d9978111b`
- town materializer: `3fd5fd361b5356ad3aa1f8dc7bda3ed2b3cee2b0`
- decay materializer: `6c215bb626369424051fbe58312ecf225ac32ad3`

## What is proved

`compose.py` requires a full Git checkout whose HEAD descends from the exact base
and both donor heads. It verifies the exact donor blobs at both their source
heads and the final tree, authenticates every executable input as a regular
non-symlink file, and then performs this one legal chain:

1. Execute the exact #12053 materializer against pristine source.
2. Recompute and validate its strict `v2` receipt, including source, engine, and
   town-postimage digests.
3. Feed that exact authenticated postimage—not a raw unbound patch—into the
   exact #12075 decay verifier and patcher.
4. Require one AST-level `_funding_trace()` loop where the shop-lifecycle guard
   dominates the loop and town consumption is immediately followed by plant
   decay, with decay the final represented stage before the result return.
5. Load the final postimage as `frozen_selected`, construct the current
   `TitanAgent` with `consumer='frozen'`, and prove that the instantiated
   `FrozenSelected.transform` resolves `_funding_trace` and both town helpers
   from the final postimage.
6. Rehash every input and publish the two postimages plus both receipts as one
   all-or-nothing output directory.

The exact tests retain both source-real predecessor killers in the *final*
postimage:

- same-day town demand changes inherited WHEAT purchase protection from
  `minimum_now=0` to `1` without fallback;
- official plant decay changes the season-reachable capacity case from
  `minimum_now=0` / zero reference acquisitions to `1` / one acquisition.

They also prove the unmodified donor CLIs reject each other's postimages,
reject reversed chronology, stale/tampered intermediate receipts, donor drift,
symlinked paths, partial publication, wrong consumer selection, duplicate JSON
keys, and non-finite receipt/config values.

## Reproduce

From repository root:

```bash
LAB=revenue/kaggriculture/cloud-execution-lab
CANDIDATE="$LAB/candidates/v3-funding-town-decay-sol-compositor"
python -B "$CANDIDATE/compose.py" \
  --repo-root . \
  --source "$LAB/frozen_selected.py" \
  --scheduler "$LAB/scheduler.py" \
  --mechanics "$LAB/mechanics.py" \
  --engine "$LAB/reference/engine/kaggriculture.py" \
  --runtime "$LAB/titan_runtime.py" \
  --config "$LAB/TITAN-CONFIG.json" \
  --town-materializer "$LAB/candidates/v3-funding-town-consumption-sol-atlas/town_consumption_closure.py" \
  --decay-materializer "$LAB/candidates/v3-funding-plant-decay-sol-chronos/materialize.py" \
  --output-dir /tmp/titan-town-decay-composition
python -B -m unittest -v "$CANDIDATE/test_authenticated_composition.py"
```

The authoritative workflow also runs both donor suites, compiles the final
postimage, validates the receipt seal, retains SHA-256 manifests, and requires a
clean repository after execution.

## Boundary

This is a composition and executable-reachability proof, not an action-active
score panel. It changes no canonical runtime, config, archive, current pointer,
Kaggle state, provider state, or seed bank. SOL-ATLAS and SOL-CHRONOS retain
mechanism ownership; T08 retains one-tree integration, games, promotion, and
submission authority.
