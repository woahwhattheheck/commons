from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_incoming_models_no_void_337():
    html = (ROOT / "incoming-models.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert "HTTP is not the computer" in html

if __name__ == "__main__":
    test_incoming_models_no_void_337()
    print("ok")
