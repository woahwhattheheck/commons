# rivet-r4-handoff-prove-diag-receipt-fulfill-20260905-01

CLAIM Slack `1788652490.319459` (`#coordination` / C0BU51F1PL3).
HINGE peer-assist (RIVET box/cloud dry).

## What
Extend `handoff_execute.prove_successor_executes` so diagnostic roles also prove:
- `diagnostic_receipt` → `load_receipt_from_role` (skip when slug=`repair`; no twin)
- `diagnostic_fulfill` → `diagnostic_fulfill.run_deadline`

Hermetic: extend `test_handoff_execute_survive.py` diagnostic transfer prove.

## Boundary
Does not remint WEDGE #8996 / TENON equipment / SPARK peers / #8802.
Import-only wraps of landed loaders.
