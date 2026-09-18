from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_8walk_no_void_337():
    html = (ROOT / "8walk.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert "8bit.js" in html
    assert "BRYCE-1787138698752-iq4fh8" in html

if __name__ == "__main__":
    test_8walk_no_void_337()
    print("ok")
