# TITAN V5 — submitted-V4 added-feature factorial

Evidence-only causal screen for the owner-reported **submitted V3.1 > submitted V4** regression. It does not change a runtime default, republish `titan-current`, or create a second V5 policy tree.

## Causal boundary

The exact submitted configurations differ cleanly at four V4 additions.

- V3.1 source: `a90d888f03987ef0b35cfd20ec3519c6144db08a`
- V4 source: `4af1113154e78c662780e6658cd920daac7902e3`
- exact submitted V4 archive: `4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b`
- exact V4 `TITAN-CONFIG.json` SHA256: `ba18563683125fd89d5473ddb8a5c3e9431db1787a3046f618a9e03af2cb44af`

V3.1 and V4 share the same values for the pre-existing core feature keys. V4 additionally enables:

1. `idle_fertilizer`
2. `crop_release`
3. `early_capital`
4. `town_procurement`

This harness asks whether those additions explain the regression without mixing in any other source change.

## Hard experiment contract

Every arm is created in memory from the **exact submitted V4 archive**. Archive membership is invariant. All non-config members are byte-identical. An experimental arm may change only `TITAN-CONFIG.json`, and within that file it may change only the four booleans above.

Execution reuses and Git-binds the existing `candidates/v5/joint-liquidity-bench/paired.py` authenticated harness helper at blob `fbc5e320b8a2ee63af11dc9856c956a679823409`. Evaluator, loader, packer, reference-policy bank and opponent support are copied once into the helper's authenticated private snapshot; games then execute only from that snapshot.

## Screen design

`--design screen` runs six arms per seed / seat / opponent cell:

- `v4`: TTTT, byte-identical submitted V4 baseline
- `v31_flags`: FFFF, the V3.1-like state for only these four additions
- `off_idle_fertilizer`
- `off_crop_release`
- `off_early_capital`
- `off_town_procurement`

The baseline is run once per cell, not once per comparison. Arm order rotates across cells. The default two seeds are the already-known Sian/Gracie loss-rematch seeds `2051966578,1378040481`, both seats, against authenticated `apex_v7` and `arlene_v14`.

If the screen shows interactions, `--design full` runs all 16 masks (`mask_0000` through `mask_1111`) with the same byte-custody contract.

## Interpretation

- If `v31_flags` materially beats `v4`, the regression is inside these four V4 additions. The single-off arms localize main effects; the full factorial resolves interactions.
- If `v31_flags` does not recover the gap, stop blaming these additions and spend effort on the V3.1↔V4 returned-action divergence / source differences instead.
- This package produces evidence only. No arm is eligible for a production default change without a separate current-V5 natural-engagement and promotion gate.

## Run

```bash
cd revenue/kaggriculture/cloud-execution-lab/candidates/v5/v4-added-features-factorial

python3 -B paired.py \
  --kg-root /workspace/commons/revenue/kaggriculture \
  --engine-dir /workspace/engine \
  --baseline /workspace/titan-v4-4af11131-rebuilt.tar.gz \
  --output /workspace/results/v4-added-feature-screen
```

Full factorial:

```bash
python3 -B paired.py ... --design full --output /workspace/results/v4-added-feature-full
```

Source gates:

```bash
python3 -B -m py_compile paired.py test_paired.py
python3 -B -m unittest -v test_paired.py
python3 -O -B -m unittest -v test_paired.py
```
