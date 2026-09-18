from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_keep_sell_no_void_337():
    html = (ROOT / "keep-sell.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert "BUSINESS_PACK_KEEP_SELL.md" in html

if __name__ == "__main__":
    test_keep_sell_no_void_337()
    print("ok")
