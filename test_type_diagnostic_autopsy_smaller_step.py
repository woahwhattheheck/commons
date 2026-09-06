"""Hermetic: diagnostic.html points smaller-step buyers to Autopsy $29."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "diagnostic.html"

def test_diagnostic_autopsy_smaller_step():
    text = HTML.read_text(encoding="utf-8")
    assert "Need a smaller first step?" in text
    assert 'href="./agent-rescue.html"' in text
    assert "Agent Failure Autopsy" in text
