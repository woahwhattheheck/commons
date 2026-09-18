from pathlib import Path
ROOT=Path(__file__).resolve().parent
TEXT=(ROOT/"ground"/"CASH_NOW.md").read_text(encoding="utf-8")
def test_cash_now_has_live_doors_not_zero_offer_lie():
    assert "## Live cash doors" in TEXT
    assert "agent-rescue.html" in TEXT
    assert "$29" in TEXT
    assert "dealer-service-lead-rescue.html" in TEXT
    assert "There is no USD collectable" not in TEXT
