from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_nojs_no_void_337():
    html = (ROOT / "nojs.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert "latch-reach-any-player-20260819-01" in html

if __name__ == "__main__":
    test_nojs_no_void_337()
    print("ok")
