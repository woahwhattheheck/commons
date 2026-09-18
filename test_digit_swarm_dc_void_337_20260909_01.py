from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_swarm_dc_no_void_337():
    html = (ROOT / "swarm-dc.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert "DIRECTIVES.md" in html
    assert "Muhlnickel" in html

if __name__ == "__main__":
    test_swarm_dc_no_void_337()
    print("ok")
