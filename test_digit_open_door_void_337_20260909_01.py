from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_open_door_no_void_337():
    html = (ROOT / "open-door.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert "coil-open-door-20260819-01" in html

if __name__ == "__main__":
    test_open_door_no_void_337()
    print("ok")
