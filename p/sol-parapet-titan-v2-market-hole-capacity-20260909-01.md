# SOL-PARAPET — Titan V2 executable-slot capacity

- operation: `titan-v2-market-hole-capacity-20260909-sol-parapet-01`
- branch: `sol-parapet/titan-v2-market-hole-capacity-20260909-01`
- branch point: `82faab26bbaabb5f1aecfa7736c6c429c4496d18`
- frozen V2 scheduler blob: `7c068b7078c3d7c09bb3836590ad42b0af934cdf`
- frozen V2 scheduler SHA-256: `72865b83e66d0c1ed27ddc35e5ab428f8212872e8e8e918f2826eb7665fbe7f8`
- frozen V1 scheduler blob: `cbc502a92fe9d790cfaf763f6990d1057bc9b82d`
- state: source witness and exact paired screen packaged; no promotion claim

## Owned paths

- `.github/workflows/titan-v2-market-hole-capacity-sol-parapet.yml`
- `revenue/kaggriculture/cloud-execution-lab/analysis/v2-market-hole-capacity-sol-parapet/**`
- `p/sol-parapet-titan-v2-market-hole-capacity-20260909-01.md`

## Acceptance

1. Frozen V1/V2 source blobs match the pins.
2. All local contracts pass and the patched scheduler compiles.
3. The predecessor rejects the exact false-full witness; the candidate fills the
   active no-op without moving a live row.
4. Materialization changes only `scheduler.py`, leaves frozen source untouched,
   and emits closure-verifying control/candidate entrypoints.
5. Both official panels complete the exact opponent × seed × seat grid.
6. Only broad, seat-balanced own-cash upside exits zero.
7. Canonical build remains byte-clean.

A witness, smoke, queued run, or arithmetic-only result cannot authorize a
promotion or hosted submission.
