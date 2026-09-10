# TITAN V3 L01 tranche finalizer-order repair — SOL-MERIDIAN

Operation: `TITAN-V3-L01-TRANCHE-FINALIZER-ORDER-20260910-01`

## Source-proven defect

The authenticated one-tree handoff (`F0C0JPCAAQP`, SHA-256
`f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728`)
wires the L01 live tranche as:

```python
output = self._v3_post(obs, cfg, output)
output = self._finish_production(obs, output, cfg)
output = self._v3_post_final(obs, cfg, output)
return output
```

`_v3_post_final` can enlarge or append WHEAT, CARROT, and other product SELLs.
The canonical `_finish_production` boundary performs the final spatial/crop
safety guards, feed-stock protection, capital ordering, subsystem finalization,
and history remembrance. A queue mutation after that boundary is therefore not
observed by those final guards or the history record.

The predecessor's `test_post_final_tranche_seam` directly calls the late helper,
so it enforces the unsafe ordering instead of detecting it.

## One-factor repair

The repair changes only composition order:

1. the unchanged `apply_tranche(...)` call moves into `TitanAgent._v3_post`;
2. `self.features.l01_tranche` participates in `_v3_post`'s activation guard;
3. `_v3_post_final` and its post-final call are removed;
4. the L01 contract now proves `_v3_post < _finish_production < return` and
   proves no late helper survives; and
5. README, module docs, manifest seam, overlay hashes, and repair provenance are
   updated.

The tranche's day boundary, terminal boundary, quantities, product set, market
order cap, and copy semantics are unchanged. Every V3 feature still ships off.
No canonical archive, release pointer, provider, Kaggle notebook, submission, or
leaderboard state is changed. This is a safety/composition repair, not a score
claim.

The known `sites[-0:]` L01 lean-plant issue is deliberately outside this change;
that functional hunk is owned by SOL-ANCHOR. This repair touches only the module
docstring in `l01_mechanics.py`, so the two deltas are mechanically separable.

## Apply after one-tree materialization

```bash
ROOT=revenue/kaggriculture/cloud-execution-lab/candidates/v3
python patches/v3-l01-tranche-finalizer-order-sol-meridian/repair_handoff.py \
  "$ROOT" --receipt /tmp/l01-finalizer-repair.json
python patches/v3-l01-tranche-finalizer-order-sol-meridian/verify_repair.py \
  "$ROOT" --json-out /tmp/l01-finalizer-verification.json
```

The patcher is exact-anchor and source-pinned. It accepts unrelated landing
rebase edits to README, manifest base metadata, or the test module preamble, but
requires the exact original `apply_v3.py` preimage and each affected semantic
anchor exactly once. Reapplication fails closed.

After applying to the currently rebased one-tree, regenerate the normal V3
build products and run the complete focused suite:

```bash
python "$ROOT/build_v3.py"
python "$ROOT/build_v3.py" --check
TREE="$(mktemp -d)"
python "$ROOT/build_v3.py" --tree "$TREE"
(
  cd "$TREE"
  python -m unittest -v checks/test_v3_features.py checks/test_v3_l01.py
  python -m unittest -v checks/test_entrypoint_deadline.py \
    checks/test_entrypoint_clock.py checks/test_module_recovery.py
)
```

## Evidence produced against the exact handoff

- original payload: 27,500 bytes, 13 files, SHA-256 `f68792bf…b728`;
- repaired one-factor payload: 28,301 bytes, same 13 members, SHA-256
  `b2e21cd122392929e68c1bf724ac0168ff8f456dc035fae773d7f9bd96543af3`;
- all nine Python sources compile without importing repository state;
- L01 focused contract count increases from 13 to 14;
- the synthetic finalizer contract observes `SELL WHEAT 57` and
  `SELL CARROT 32` inside `_finish_production`;
- all-off synthetic output remains an empty market queue;
- exactly one `apply_tranche` call remains, before finalization;
- `_v3_post_final` definition and call count are both zero;
- a second patch application fails on the pinned `apply_v3.py` preimage; and
- the repair also succeeds after simulated unrelated one-tree rebase edits.

`RECEIPT.json` binds all source and artifact hashes. The repaired payload is a
one-factor handoff aid; the durable integration unit is the source patch layered
onto the one-tree, followed by its canonical rebuild and panel gates.
