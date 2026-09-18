from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_opportunity_no_void_337():
    html = (ROOT / "opportunity.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert 'Possessing the link is authorization' in html

if __name__ == "__main__":
    test_opportunity_no_void_337()
    print("ok")
