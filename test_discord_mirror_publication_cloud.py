"""Cloud Discord outbound must send permitted CI receipts and skip true rejects."""
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import importlib.util
import tempfile
import unittest
import urllib.error

import commons_publication_policy as policy
from host.discord_mirror import mirror_payload

ROOT = Path(__file__).resolve().parent
HOST = ROOT / "host" / "discord_mirror.py"
SPEC = importlib.util.spec_from_file_location("discord_mirror_cloud", HOST)
DM = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(DM)

RECEIPT = ROOT / "p/astra-larch-current-work-details-state-20260907-01.md"


class CloudPublicationMirrorTests(unittest.TestCase):
    def _ok_urlopen(self, captured: dict):
        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"id":"snowflake-ci"}'

        def fake_urlopen(req, timeout=None):
            captured["called"] = captured.get("called", 0) + 1
            captured["url"] = req.full_url
            return Resp()

        return fake_urlopen

    def test_landed_software_receipt_payload_is_allowed(self):
        payload = mirror_payload(RECEIPT)
        decision = policy.check_publication(payload)
        self.assertTrue(decision["allowed"], decision)

    def test_send_parts_posts_permitted_ci_receipt(self):
        captured: dict = {}
        parts = DM.format_mirror(RECEIPT)
        with patch.object(DM.urllib.request, "urlopen", self._ok_urlopen(captured)):
            receipts = DM.send_parts(
                parts,
                token="bot-token",
                channel="1541336794967052338",
            )
        self.assertGreaterEqual(len(receipts), 1)
        self.assertTrue(all(item == "snowflake-ci" for item in receipts))
        self.assertGreaterEqual(captured.get("called"), 1)

    def test_send_parts_skips_true_reject_without_posting(self):
        captured: dict = {}
        with patch.object(DM.urllib.request, "urlopen", self._ok_urlopen(captured)):
            receipts = DM.send_parts(
                ["The service failed."],
                token="bot-token",
                channel="1541336794967052338",
            )
        self.assertEqual(receipts, [])
        self.assertEqual(captured.get("called", 0), 0)

    def test_cli_send_returns_zero_on_private_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "reject.md"
            path.write_text("The service failed.\n", encoding="utf-8")
            with patch.dict(
                "os.environ",
                {"DISCORD_BOT_TOKEN": "bot-token", "COMMONS_DISCORD_CHANNEL": "1"},
                clear=False,
            ):
                code = DM.main(["discord_mirror.py", "send", str(path)])
        self.assertEqual(code, 0)

    def test_http_errors_still_surface(self):
        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(
                req.full_url,
                403,
                "Forbidden",
                hdrs={},
                fp=BytesIO(b'{"message":"blocked"}'),
            )

        with patch.object(DM.urllib.request, "urlopen", fake_urlopen):
            with self.assertRaises(SystemExit) as ctx:
                DM.send_parts(["hello table"], token="bot-token", channel="1")
        self.assertIn("403", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
