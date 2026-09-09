from pathlib import Path
HTML=(Path(__file__).resolve().parent/"stripe-payment-links-20260826.html").read_text(encoding="utf-8")
def test_live_cash():
    assert "live-cash" in HTML and "agent-rescue.html" in HTML
