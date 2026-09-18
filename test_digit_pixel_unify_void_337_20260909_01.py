from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_pixel_unify_no_void_337():
    html = (ROOT / "pixel-unify.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert 'grok-pixel-unify-20260828-01' in html

if __name__ == "__main__":
    test_pixel_unify_no_void_337()
    print("ok")
