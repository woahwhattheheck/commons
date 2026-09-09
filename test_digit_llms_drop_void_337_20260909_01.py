from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_llms_no_void_337():
    text = (ROOT / "llms.txt").read_text(encoding="utf-8")
    assert "337 NO" not in text
    assert "## Tools board" in text
    assert "job.html" in text
