from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_listing_registry_no_void_337():
    html = (ROOT / "listing-registry.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert 'LISTING_REGISTRY.md' in html

if __name__ == "__main__":
    test_listing_registry_no_void_337()
    print("ok")
