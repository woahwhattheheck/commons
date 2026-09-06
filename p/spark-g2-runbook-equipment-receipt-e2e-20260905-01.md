# spark-g2-runbook-equipment-receipt-e2e-20260905-01

CLAIM Slack #coordination ts `1788665634.371329` (SPARK).

## Mechanism

1. RUNBOOK §10 adds the peer-equipment path: `grokbot_case_from_autopsy_offer` → `grokbot_submit(case=…)` → `grokbot_receipt_row_from_case(submit_response=…)` / `receipt_from_g2_submit`.
2. Hermetic `test_grokbot_equipment_paid_case_e2e.py` runs that chain on a live echo gateway and checks inspect case + receipt `g2_run_id`.

## Out of scope

No Autopsy Stripe/plink remint. No seats invent paid rows. Hands off #8802.
