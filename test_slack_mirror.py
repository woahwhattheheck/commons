"""slack_mirror.format_mirror must carry the git body, not a moth receipt."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

HOST = Path(__file__).resolve().parents[1] / "host" / "slack_mirror.py"
SPEC = importlib.util.spec_from_file_location("slack_mirror", HOST)
SM = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SM)

SAMPLE = """---
from: PLAYER1
to: TABLE
id: p1-slack-mirrors-git-20260822-01
---
PLAIN: Slack #commons must contain what git contains. A link is extra.

LAW. One file, two reaches.
"""


class FormatMirrorTests(unittest.TestCase):
    def test_payload_contains_plain_not_just_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "p1-slack-mirrors-git-20260822-01.md"
            p.write_text(SAMPLE, encoding="utf-8")
            parts = SM.format_mirror(p)
        blob = "\n".join(parts)
        self.assertIn("PLAIN: Slack #commons must contain what git contains", blob)
        self.assertIn("LAW. One file, two reaches.", blob)
        self.assertGreater(len(blob), 80)
        # A receipt-only moth line would be from= plus URL and almost no body.
        self.assertGreater(blob.count("\n"), 3)

    def test_empty_body_is_illegal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "thin.md"
            p.write_text("from: MOTH\n\nhttps://example.com/p/x.md\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                SM.format_mirror(p)


if __name__ == "__main__":
    unittest.main()
