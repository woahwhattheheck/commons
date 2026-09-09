from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_image_drop_no_void_337():
    html = (ROOT / "image-drop.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert "board_ingest.py" in html
    assert "HTTP is not the computer" in html
