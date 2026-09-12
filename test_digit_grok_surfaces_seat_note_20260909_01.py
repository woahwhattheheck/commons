from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_named_seats_note():
    md = (ROOT / "ground/GROK_SURFACES.md").read_text(encoding="utf-8")
    assert "Named Grok Bot seats" in md
    assert "DIGIT" in md
    assert "clan/grokbot" in md
    assert "GOAT" in md
