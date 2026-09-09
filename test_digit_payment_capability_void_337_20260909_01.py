from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_payment_capability_no_void_337():
    html = (ROOT / "payment-capability.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert "PAYMENT_CAPABILITY.md" in html

if __name__ == "__main__":
    test_payment_capability_no_void_337()
    print("ok")
