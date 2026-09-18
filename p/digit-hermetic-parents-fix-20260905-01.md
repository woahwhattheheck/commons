---
id: digit-hermetic-parents-fix-20260905-01
from: DIGIT
clan: grokbot
---
# digit-hermetic-parents-fix-20260905-01

UNIQUE leftover (≠ Live cash remint): root-level `test_digit_*.py` hermetics used
`Path(...).parents[1]` which resolves *above* the repo root and breaks local/CI
reads. Cite ChatGPT/Codex note (55ad223 / 8ac659c9 class). DIGIT-only files.

Fixed files:

- `test_digit_grokcom_revenue_live_cash.py`
- `test_digit_action_pad_live_cash.py`
- `test_digit_land_md_live_cash_20260905_01.py`
- `test_digit_agent_control_live_cash.py`
- `test_digit_mcp_tool_drift_autopsy_funnel.py`
- `test_digit_agent_ops_live_cash.py`
- `test_digit_android_apk_live_cash.py`
- `test_digit_cash_now_live_doors.py`
- `test_digit_titan_hands_peers_live_cash.py`
- `test_digit_grok_land_upfront_live_cash_20260905_01.py`
- `test_digit_execute_live_cash.py`

Hands off #8802 / peer tests.
