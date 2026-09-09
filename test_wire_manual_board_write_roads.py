from pathlib import Path
HTML = (Path(__file__).resolve().parent / "manual.html").read_text(encoding="utf-8")

def test_manual_distinguishes_board_write_roads():
    assert "writing.html" in HTML
    assert "post.html" in HTML
    assert "reply.html" in HTML
    assert "TOOLS jobs" in HTML or "not TOOLS" in HTML
    assert "builds.html" not in HTML
