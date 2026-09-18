from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_dj_trail_no_void_337():
    html = (ROOT / "dj-trail.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert "from= is a claim" in html

if __name__ == "__main__":
    test_dj_trail_no_void_337()
    print("ok")
