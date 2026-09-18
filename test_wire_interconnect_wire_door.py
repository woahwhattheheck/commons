from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "interconnect.html").read_text(encoding="utf-8")

def test_interconnect_cites_wire_html():
    assert 'href="./wire.html"' in TEXT
    assert "capabilities.html" in TEXT
