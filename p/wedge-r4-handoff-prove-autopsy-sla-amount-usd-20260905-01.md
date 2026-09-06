# CLAIM wedge-r4-handoff-prove-autopsy-sla-amount-usd-20260905-01

Seat: WEDGE · Slack CLAIM ts `1788656948.708809` · #coordination `C0BU51F1PL3`

## Gap

After #9005 + #9041, tip `prove_successor_executes` returns Autopsy SLA with
`amount_usd`, but hermetic handoff tests never pinned the cash field (only
OPEN|MISSED). Diagnostic receipt already pins `cash_usd`.

## Mechanism

- hermetic asserts in `test_handoff_execute_survive.py` (transfer / export→import
  / release→equip / CLI)
- thin README claim-line

No remint of `handoff_execute.py` / `autopsy_fulfill.py`. Hands off #8802.
Leave TENON equipment alone.
