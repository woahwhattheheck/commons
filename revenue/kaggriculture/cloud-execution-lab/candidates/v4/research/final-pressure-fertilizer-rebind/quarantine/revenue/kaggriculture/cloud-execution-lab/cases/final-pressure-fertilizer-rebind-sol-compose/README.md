# Final-pressure fertilizer ledger rebind

Operation: `TITAN-V3-FINAL-PRESSURE-FERTILIZER-LEDGER-REBIND-20260910-01`

## Exact defect

Current `main.py` intentionally delays market pressure until `_finish_production()`: the initial pressure call is suppressed, `SpatialTempo.guard_returned()` validates the idle-fertilizer `DROP` plus `SELL FERTILIZER 1`, then feed-stock and early-capital finish, and only then `FinalPressureAgent._early_capital_selected()` runs pressure. `SpatialTempo.finish()` subsequently commits the delivery only when the final returned market row at `_sale_proposal['slot']` is still the exact fertilizer sale.

Pressure is allowed to reorder contiguous valid SELL lots, including FERTILIZER. Therefore the returned action can execute the intended DROP and sale while the proposal retains its pre-pressure slot. The delivery receipt is lost even though the engine-facing bytes are valid.

The focused predecessor is:

```text
before pressure: [SELL CARROT 1, SELL FERTILIZER 1], proposal.slot = 1
after pressure:  [SELL FERTILIZER 1, SELL CARROT 1], proposal.slot = 1
finish check:    row 1 is CARROT, so no sale_obligation commit
```

The actual landed pressure module and a bounded public quote curve reproduce that reorder in the test suite.

## Repair boundary

The carrier adds one late helper to `FinalPressureAgent`. After pressure returns, it:

1. inspects only the current existing `_sale_proposal`;
2. finds the unique exact `SELL FERTILIZER 1` in the already-supported ten-row idle-FERT prefix;
3. rebinds only `proposal['slot']` to those final returned bytes; and
4. cancels the paired DROP and any ambiguous fertilizer rows if the unique exact lot is unexpectedly missing or duplicated.

It does not create, delete, resize, reprioritize, or economically score any valid sale. With no current proposal, a different step, a deadline fallback, or no pressure movement, the action path remains identity-equivalent.

## Source custody

The carrier accepts only Git blob `4a8cf7bcda1f0fea231a144692cb84a779a9e73e` for `revenue/kaggriculture/cloud-execution-lab/main.py`. The causal pressure source is Git blob `7261674962d10fc8bc6af5ff73ff9212c40f61ad`. Any source drift fails closed before candidate materialization.

This PR is an additive source-bound repair/evidence handoff. It does not mutate canonical runtime/config/archive/pointers or authorize gameplay, provider, Kaggle, release, or submission operations.

## Run

```bash
cd revenue/kaggriculture/cloud-execution-lab/cases/final-pressure-fertilizer-rebind-sol-compose
python -m unittest -v test_rebind.py
python -O -m unittest -v test_rebind.py
python apply_rebind.py --tree ../../../../.. --output /tmp/main.rebound.py --receipt /tmp/rebind-receipt.json
```
