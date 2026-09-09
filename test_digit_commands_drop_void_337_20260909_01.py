from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_commands_no_void_337():
    html = (ROOT / "commands.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert "Dest FROM FILE" in html
