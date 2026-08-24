"""discord_mirror.format_mirror carries the git body; link-only is legal; DARK without token."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
