"""DIGIT: mcp-tool-drift offer sells Autopsy $29, not Survival on agent-rescue."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "mcp-tool-drift.html").read_text(encoding="utf-8")

def test_offer_is_autopsy_not_survival():
    assert "Agent Failure Autopsy" in HTML
    assert "$29" in HTML
    assert 'href="./agent-rescue.html"' in HTML
    assert "Same-Day Agent Survival Proof" not in HTML
    assert "See the same-day offer" not in HTML
