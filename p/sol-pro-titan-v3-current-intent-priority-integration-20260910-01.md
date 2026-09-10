# SOL-PRO — TITAN V3 current intent-priority integration

Claim: `TITAN-V3-CURRENT-INTENT-PRIORITY-INTEGRATION-20260910-01`

Branch:
`sol-pro/titan-v3-current-intent-priority-integration-20260910-01`

Current source:
`main@98a98108998efac9e53a8b045f0fb2c85a4b19e2`,
archive `17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86`,
scheduler blob `a483b24dd72b580d7d8811636b54d2d44f391575`.

Mechanism: preserve every positive non-operating shed target and its full
quantity; resolve equal-ranked cross-product SELL choices by pending intent,
then inherited baseline SELL first-seen order, then remaining `PRODUCTS`.

Source admission: PR #11963, run `34516136132`, artifact `10168056904`,
artifact SHA-256
`528f7557a899c1376c8fe04ed328c70a17a760aa3a725e190710ea13ad7e13f8`;
32 paired cells / 64 games; 6 action changes; mean own `+8.375`; no negative
cells, new losses, or lost wins.

This branch provides a default-off exact archive arm, scheduler-only enabled
arm, source and closure receipts, closure-checking wrappers, 13 focused local
contracts, patched candidate-action evidence, and a fresh 32-cell current-main
panel. It changes no canonical/release/provider/Kaggle state.
