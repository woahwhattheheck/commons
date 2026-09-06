from pathlib import Path
TEXT=(Path(__file__).resolve().parents[1]/"docs"/"COMMONS_ANDROID_APK.md").read_text(encoding="utf-8")
def test_android_apk_live_cash():
    assert "## Live cash" in TEXT
    assert "agent-rescue.html" in TEXT
