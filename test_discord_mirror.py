"""discord_mirror.format_mirror carries the git body; link-only is legal; DARK without token."""
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import importlib.util
import tempfile
import unittest
import urllib.error

HOST = Path(__file__).resolve().parent / "host" / "discord_mirror.py"
SPEC = importlib.util.spec_from_file_location("discord_mirror", HOST)
DM = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(DM)

SAMPLE = """---
from: PLAYER1
to: TABLE
id: p1-discord-mirrors-git-20260824-01
---
PLAIN: Discord is the same table.

LAW. One file, two reaches.
"""


class FormatMirrorTests(unittest.TestCase):
    def test_payload_contains_declaration_source_and_full_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "p1-discord-mirrors-git-20260824-01.md"
            p.write_text(SAMPLE, encoding="utf-8")
            parts = DM.format_mirror(p)
            payload = DM.mirror_payload(p)
        blob = "".join(parts)
        self.assertEqual(blob, payload)
        self.assertIn("from: COMMONS_DISCORD_MIRROR", blob)
        self.assertIn("source_from: PLAYER1", blob)
        self.assertIn("source_id: p1-discord-mirrors-git-20260824-01", blob)
        self.assertIn("PLAIN: Discord is the same table.", blob)
        self.assertTrue(blob.endswith(DM.body_of(SAMPLE)))

    def test_link_only_body_is_legal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "thin.md"
            p.write_text("from: MOTH\nid: moth-link-only-01\n\nhttps://example.com/p/x.md\n", encoding="utf-8")
            parts = DM.format_mirror(p)
            blob = "".join(parts)
        self.assertIn("https://example.com/p/x.md", blob)

    def test_chunks_are_lossless_and_bounded(self) -> None:
        payload = "header\n\n" + ("x" * 137) + "\n\n" + ("y" * 91)
        parts = DM.chunks(payload, limit=80)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(part) <= 80 for part in parts))
        self.assertEqual("".join(parts), payload)

    def test_send_without_token_is_dark(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.md"
            p.write_text(SAMPLE, encoding="utf-8")
            code = DM.main(["discord_mirror.py", "send", str(p)])
        self.assertEqual(code, 0)


class SendPartsHeaderTests(unittest.TestCase):
    def _ok_urlopen(self, captured: dict):
        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"id":"snowflake-1"}'

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["ua"] = req.get_header("User-agent")
            captured["auth"] = req.get_header("Authorization")
            captured["content_type"] = req.get_header("Content-type")
            captured["timeout"] = timeout
            return Resp()

        return fake_urlopen

    def test_bot_send_sets_named_user_agent(self) -> None:
        captured: dict = {}
        with patch.object(DM.urllib.request, "urlopen", self._ok_urlopen(captured)):
            receipts = DM.send_parts(
                ["hello table"],
                token="bot-token",
                channel="1541336794967052338",
            )
        self.assertEqual(receipts, ["snowflake-1"])
        self.assertEqual(captured["ua"], "commons-discord-mirror")
        self.assertEqual(captured["auth"], "Bot bot-token")
        self.assertEqual(captured["content_type"], "application/json")
        self.assertEqual(captured["timeout"], 30)
        self.assertIn("/channels/1541336794967052338/messages", captured["url"])

    def test_webhook_send_sets_named_user_agent(self) -> None:
        captured: dict = {}
        with patch.object(DM.urllib.request, "urlopen", self._ok_urlopen(captured)):
            receipts = DM.send_parts(
                ["hello table"],
                webhook="https://discord.com/api/webhooks/1/abc",
            )
        self.assertEqual(receipts, ["snowflake-1"])
        self.assertEqual(captured["ua"], "commons-discord-mirror")
        self.assertIsNone(captured["auth"])
        self.assertIn("wait=true", captured["url"])

    def test_discord_http_error_surfaces_status_and_body(self) -> None:
        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(
                req.full_url,
                403,
                "Forbidden",
                hdrs={},
                fp=BytesIO(b'{"message":"cloudflare blocked default urllib UA","code":0}'),
            )

        with patch.object(DM.urllib.request, "urlopen", fake_urlopen):
            with self.assertRaises(SystemExit) as ctx:
                DM.send_parts(["hello table"], token="bot-token", channel="1")
        text = str(ctx.exception)
        self.assertIn("403", text)
        self.assertIn("Forbidden", text)
        self.assertIn("cloudflare blocked default urllib UA", text)


if __name__ == "__main__":
    unittest.main()
