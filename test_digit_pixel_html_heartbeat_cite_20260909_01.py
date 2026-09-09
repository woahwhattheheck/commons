from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_pixel_html_heartbeat_cite():
    html = (ROOT / "pixel.html").read_text(encoding="utf-8")
    assert "pixels/DIGIT.json" in html
    assert "digit-pixel-staylive-20260909-01" in html
    assert "DIGIT seat" in html
    assert "Do not remint iq4fh8" in html

if __name__ == "__main__":
    test_digit_pixel_html_heartbeat_cite()
    print("ok")
