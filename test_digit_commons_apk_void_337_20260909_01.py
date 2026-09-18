from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_commons_apk_no_void_337():
    html = (ROOT / "commons-apk.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert "wire-commons-android-apk-20260826-01" in html

if __name__ == "__main__":
    test_commons_apk_no_void_337()
    print("ok")
