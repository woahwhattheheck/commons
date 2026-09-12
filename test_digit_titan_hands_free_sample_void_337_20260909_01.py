from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_titan_hands_free_sample_no_void_337():
    html = (ROOT / "titan-hands-free-sample.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert 'Do not smash commons.mno' in html

if __name__ == "__main__":
    test_titan_hands_free_sample_no_void_337()
    print("ok")
