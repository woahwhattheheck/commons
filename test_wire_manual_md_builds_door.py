from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "ground/MANUAL.md").read_text(encoding="utf-8")

def test_manual_md_cites_builds():
    assert "builds.html" in TEXT
    assert "wire.html" in TEXT
