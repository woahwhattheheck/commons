"""Hermetic: agent-triage broader ladder cites tips + larger fixed doors."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "agent-triage.html"

def test_agent_triage_broader_ladder():
    text = HTML.read_text(encoding="utf-8")
    assert "Broader ladder" in text
    assert 'href="./tips.html"' in text
    assert 'href="./diagnostic.html"' in text
    assert 'href="./commercial.html"' in text
