# TITAN V3 overlay metamorphic safety screen

Operation: `TITAN-V3-OVERLAY-METAMORPHIC-SAFETY-SCREEN-20260910-01`

This additive analysis lane authenticates the exact 13-file V3 handoff from
Slack object `F0C0JPCAAQP` (gzip SHA-256
`f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728`,
27,500 bytes), safely reads it without importing or executing handoff code,
and AST-screens every Python overlay for a proved non-idempotence class.

The first rule detects a mutating loop over `sequence[-count:]` when `count`
is defined as `max(0, len(sequence) - keep)` and zero is not excluded. Python
makes `sequence[-0:]` equal to the whole sequence, so a patcher that is meant
to remove only an excess instead destroys an already-at-target sequence. The
report seals three metamorphic witnesses:

* exact-target fixed point (`72 -> 0` for the handed-off lean-plant pattern),
* repeated application (`164 -> 72 -> 0`), and
* shared-object alias order (`164 -> 72 -> 0`, versus independent deep copies
  ending at `72, 72`).

The verifier also accepts both safe control forms: a positive `if count:`
guard around the loop, or a terminating `if count == 0:` guard before it.
Transport hash, byte count, regular-file-only tar shape, normalized unique
member names, and the exact allowlist all fail closed. Reports are canonical
JSON and must be byte-identical across two executions.

## Boundaries

This lane does **not** patch `l01_mechanics.py`, materialize the V3 candidate,
change any feature/config/default, run games, update the publisher branch, or
make a playing-strength claim. SOL-LEDGER retains discovery/review credit and
the one-tree publisher retains repair, source, ref, integration, merge, and
promotion custody. The output is a reusable admission gate for that owner and
future route-mutating overlays.

## Reproduce

From the repository root on this branch:

```bash
lane=revenue/kaggriculture/cloud-execution-lab/analysis/v3-overlay-metamorphic-screen-sol-metaguard
python -m unittest -v "$lane/test_audit.py"
python "$lane/audit.py" \
  --encoded-handoff revenue/kaggriculture/cloud-execution-lab/candidates/.v3-handoff-f68792.b64 \
  --require-path revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/l01_mechanics.py \
  --output /tmp/titan-v3-overlay-metamorphic-report.json
```

A critical finding makes `summary.safe_to_materialize` false. That is a source
admission result, not a claim that an already-fixed successor is unsafe.
