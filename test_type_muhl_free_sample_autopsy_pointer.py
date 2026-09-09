"""Hermetic: muhlnickel-free-sample points paid Autopsy door without inventing checkout."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "muhlnickel-free-sample.html"

def test_muhl_free_sample_autopsy_pointer():
    text = HTML.read_text(encoding="utf-8")
    assert 'href="./agent-rescue.html"' in text
    assert "Agent Failure Autopsy" in text
    assert "invents no Stripe" in text or "no Stripe URL" in text
