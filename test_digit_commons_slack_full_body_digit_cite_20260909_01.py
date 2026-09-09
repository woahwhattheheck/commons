from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
KEEP_HOST_PREFIX = "3bf97dc1"
POST = ROOT / "p" / "digit-commons-slack-full-body-digit-cite-20260909-01.md"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def test_digit_commons_slack_full_body_digit_cite_20260909_01():
    """DIGIT cite stays on the unique post. KEEP leftover host bytes stay unreminted."""
    post = POST.read_text(encoding="utf-8")
    assert "DIGIT" in post
    assert "clan/grokbot" in post
    assert "host/commons_slack_full_body.py" in post
    assert "Tip KEEP" in post
    assert "Hands off #8802" in post

    src = (ROOT / "host" / "commons_slack_full_body.py").read_text(encoding="utf-8")
    blob = git_blob("host/commons_slack_full_body.py")
    assert blob.startswith(KEEP_HOST_PREFIX), f"KEEP reminted: want {KEEP_HOST_PREFIX} got {blob[:8]}"
    assert "DIGIT cite" not in src
    assert "clan/grokbot" not in src
    assert "commons-slack.html" in src
    assert "--send" in src
    assert "REFUSED" in src
    assert "slack_mirror.py" in src


if __name__ == "__main__":
    test_digit_commons_slack_full_body_digit_cite_20260909_01()
    print("ok")
