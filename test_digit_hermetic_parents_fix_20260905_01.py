from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['test_digit_grokcom_revenue_live_cash.py', 'test_digit_action_pad_live_cash.py', 'test_digit_land_md_live_cash_20260905_01.py', 'test_digit_agent_control_live_cash.py', 'test_digit_mcp_tool_drift_autopsy_funnel.py', 'test_digit_agent_ops_live_cash.py', 'test_digit_android_apk_live_cash.py', 'test_digit_cash_now_live_doors.py', 'test_digit_titan_hands_peers_live_cash.py', 'test_digit_grok_land_upfront_live_cash_20260905_01.py', 'test_digit_execute_live_cash.py']

def test_digit_root_hermetics_use_parent_not_parents1():
    for rel in FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "Path(__file__).resolve().parents[1]" not in text
        assert "Path(__file__).resolve().parent" in text
