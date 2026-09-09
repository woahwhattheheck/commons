from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_muhl_tools_once_digit_cite():
    src = (ROOT / "host" / "muhl_tools_once.py").read_text(encoding="utf-8")
    assert "DIGIT cite" in src
    assert "clan/grokbot" in src
    assert "digit-clan-mark-20260902-01" in src
    assert "Not a gate" in src
    # still one-shot / no poller
    assert "Not a poller" in src
    assert "Does not fire dests" in src

if __name__ == "__main__":
    test_digit_muhl_tools_once_digit_cite()
    print("ok")
