from pathlib import Path
HTML = (Path(__file__).resolve().parent / "memory.html").read_text(encoding="utf-8")

def test_memory_html_write_doors():
    assert "writing.html" in HTML
    assert "WRITE-NOW" in HTML
    assert "builds.html" not in HTML  # stay off builds-cite remint class
