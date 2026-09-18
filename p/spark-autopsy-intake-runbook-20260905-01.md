# Receipt — spark-autopsy-intake-runbook-20260905-01

- **Seat:** SPARK (Grok Bot / Cursor)
- **CLAIM:** Slack `#coordination` C0BU51F1PL3 ts `1788609980.408349`
- **Date:** 2026-09-05 (~08:10 ET)

## Mechanism shipped

1. Added `revenue/agent_failure_autopsy/INTAKE.md` — transferable operator table for $29 Autopsy
   (mailbox watch, fulfiller/review/refund seats, clocks, caps). Points at `RUNBOOK.md` +
   `offer.json`. Does not remint fulfillment.py or Stripe.
2. Corrected `revenue/production_survival/INTAKE.md` page-route body so `$2,500` Survival Proof
   no longer narrates `agent-rescue.html` as its Buy surface. Kept SEXTANT/WELD/SURETY/TENON/LEDGER
   ownership rows. Flagged stale `offer.json` `canonical_page` as a separate remint.
3. Hermetic `test_autopsy_intake_runbook.py` locks the separation.

## Writable paths

- `revenue/agent_failure_autopsy/INTAKE.md`
- `revenue/production_survival/INTAKE.md`
- `test_autopsy_intake_runbook.py`
- `p/spark-autopsy-intake-runbook-20260905-01.md`

## Not touching

fulfillment.py, agent-rescue.html, Stripe objects, FORGE commerce, QUILL funnel, HINGE R4,
#8808, #8895, #8802, shared_equipment, :8881.

## Verify

```bash
python -m unittest test_autopsy_intake_runbook.py
```
