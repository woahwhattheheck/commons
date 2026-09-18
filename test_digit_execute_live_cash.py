from pathlib import Path
TEXT=(Path(__file__).resolve().parent/"ground"/"EXECUTE.md").read_text(encoding="utf-8")
def test_execute_has_live_cash_doors():
    assert "## Live cash" in TEXT
    assert "agent-rescue.html" in TEXT
    assert "$29" in TEXT
    assert "dealer-service-lead-rescue.html" in TEXT
