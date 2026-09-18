from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_agents_seats_pointer():
    md = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Named clan/grokbot seats" in md or "DIGIT, WIRE" in md
    assert "GROK_SURFACES.md" in md
    assert "DIGIT" in md
