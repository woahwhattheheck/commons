from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_dests_no_void_337():
    html = (ROOT / "dests.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert 'id="tools-jobs"' in html
    assert "job.html" in html
