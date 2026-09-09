# Frozen V2 internal market-vacancy experiment — SOL-PRO

Operation: `titan-v2-internal-market-vacancy-20260909-sol-pro-01`

## Exact seam

Frozen V2 correctly preserves inherited market indices by leaving a withheld
SELL position as `[]`. It then treats raw `len(orders) >=
maxMarketOrdersPerTurn` as saturation during feasibility and permits extra
scheduler-owned quantity only through an end append. The official interpreter
takes the first N raw rows and parses each index independently. An empty row
inside that executable window is therefore a real unused slot, while an append
at N+1 is ignored.

This lane is deliberately narrower than SOL-VACANCY: **trailing empty rows are
never consumed here**. The candidate uses only the last empty row that precedes
a later non-empty row inside the first-N window. Every inherited non-empty row
retains its exact index and bytes.

## What is delivered

`materialize.py` copies frozen V2, binds scheduler Git blob
`7c068b7078c3d7c09bb3836590ad42b0af934cdf` and SHA-256
`72865b83e66d0c1ed27ddc35e5ab428f8212872e8e8e918f2826eb7665fbe7f8`,
and changes only `scheduler.py`. It adds one helper and wires that helper into
the existing feasibility and output boundaries. Source and candidate complete
tree closures are recorded.

`probe.py` binds the preserved official-engine SHA-256, checks the exact queue
slice/parse contract, verifies the materialized closure, and executes a
predecessor-discriminating transition:

- ten executable rows contain an internal empty row at index 8 and an inherited
  CARROT purchase at index 9;
- frozen-V2 append behavior places a two-unit MILK sale at index 10, where the
  engine ignores it;
- the experimental arm fills index 8, sells both units, preserves all inherited
  non-empty row indices, and still executes the index-9 CARROT purchase;
- a trailing-empty negative control remains untouched.

## Admission boundary

The only valid first verdict is
`MECHANISM_CONFIRMED_ACTIVATION_UNMEASURED`. It proves a source/interpreter
mechanism, not that submitted V2 or current V3 reaches it and not that it
improves playing strength.

No official game panel is authorized until an exact returned-action trace
census finds all of:

1. a raw first-N market tape at the configured limit;
2. an internal `[]` before a later non-empty inherited row;
3. scheduler-selected or pending SELL quantity that exceeds executable
   inherited SELL capacity; and
4. candidate-only action activation attributable to filling that slot.

No canonical runtime, frozen variant, config, archive, pointer, provider,
submission, or Kaggle state is modified.
