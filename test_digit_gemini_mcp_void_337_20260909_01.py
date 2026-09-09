from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_gemini_mcp_no_void_337():
    html = (ROOT / "gemini-mcp.html").read_text(encoding="utf-8")
    assert "337 NO" not in html
    assert "google-services.json" in html

if __name__ == "__main__":
    test_gemini_mcp_no_void_337()
    print("ok")
