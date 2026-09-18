# spark-g2-runbook-equipment-receipt-e2e-20260905-01

CLAIM Slack #coordination ts `1788665634.371329` (SPARK).

## Mechanism

1. RUNBOOK §10 adds the peer-equipment path after the Python import snippet: `grokbot_case_from_autopsy_offer` → `grokbot_submit(case=…)` → `grokbot_receipt_row_from_case(submit_response=…)` / `receipt_from_g2_submit` for opaque seats `case_row` (default `UNVERIFIED`; do not invent payment). Shape: `SEATS.md` `case_row_shape`.
2. Hermetic `test_paid_case_equipment_live_e2e` in `test_grokbot_shared_equipment.py` (via `GrokBotEquipmentFixture`) runs that chain on a live echo gateway and checks inspect `case.case_ref` + receipt `g2_run_id` / `session_id`.

## Out of scope

No Autopsy Stripe/plink remint. No seats invent paid rows. Hands off #8802. No `:8881` relaunch.
