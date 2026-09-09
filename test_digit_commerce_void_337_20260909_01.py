from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_commerce_no_void_337():
    html = (ROOT / "commerce.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert 'type-stripe-door-20260826-01' in html

if __name__ == "__main__":
    test_commerce_no_void_337()
    print("ok")
