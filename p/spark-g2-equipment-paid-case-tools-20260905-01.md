# spark-g2-equipment-paid-case-tools-20260905-01

CLAIM Slack #coordination ts `1788650257.551349` (SPARK).

## Mechanism

1. `receipt_from_g2_submit(case, submit_response)` binds nonempty `run_id` (+ optional `session_id`) from a grokbot_submit/inspect response onto an opaque seats `case_row`.
2. Equipment tools `grokbot_case_from_autopsy_offer` and `grokbot_receipt_row_from_case` expose the same helpers locally (no `:8881` call) so Gemini peer gateway coordinators need not hand-import `paid_case`.
3. `grokbot_receipt_row_from_case` prefers `submit_response` when present; otherwise uses optional `g2_run_id` / `g2_session_id`.
4. Hermetic pins: `test_grokbot_shared_equipment.py` (equipment helpers) + `test_grokbot_paid_case_receipt.py` (`receipt_from_g2_submit`).

## Out of scope

No Stripe remint. No seats invent paid rows. No HINGE CLI remint. No `:8881` relaunch. Hands off #8802.
