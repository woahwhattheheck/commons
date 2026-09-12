# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

import paired


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class EngineCustodyTest(unittest.TestCase):
    def fixture(self, root: Path):
        payloads = {
            "a.py": b"A\n",
            "b.json": b"{}\n",
            "c.py": b"C\n",
        }
        for name, raw in payloads.items():
            (root / name).write_bytes(raw)
        return payloads, {name: blob(raw) for name, raw in payloads.items()}

    def test_capture_survives_caller_swap_and_delete(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "caller"
            root.mkdir()
            payloads, pins = self.fixture(root)
            captured = paired.capture_engine_sources(root, pins)
            (root / "a.py").write_bytes(b"POISON\n")
            (root / "b.json").unlink()
            private = paired.publish_private_engine_sources(
                captured, Path(td) / "private", pins
            )
            for name, raw in payloads.items():
                self.assertEqual((private / name).read_bytes(), raw)

    def test_capture_rejects_symlink_member(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "caller"
            root.mkdir()
            target = root / "real.py"
            target.write_bytes(b"A\n")
            link = root / "a.py"
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "ordinary file"):
                paired.capture_engine_sources(root, {"a.py": blob(b"A\n")})

    def test_private_publish_rejects_wrong_captured_digest(self):
        with tempfile.TemporaryDirectory() as td:
            pins = {"a.py": blob(b"A\n")}
            with self.assertRaisesRegex(ValueError, "re-authentication"):
                paired.publish_private_engine_sources(
                    {"a.py": b"POISON\n"}, Path(td) / "private", pins
                )

    def test_publication_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            private = root / "private"
            public = root / "public"
            private.mkdir()
            public.mkdir()
            (private / "result.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                paired.publish_evidence(private, public)

    def test_argument_rewrite_handles_split_and_equals_forms(self):
        split = ["paired.py", "--engine-dir", "/old", "--output", "/out"]
        self.assertEqual(paired._argument(split, "--engine-dir"), "/old")
        self.assertEqual(
            paired._replace_argument(split, "--engine-dir", "/private")[2],
            "/private",
        )
        equals = ["paired.py", "--engine-dir=/old", "--output=/out"]
        self.assertEqual(paired._argument(equals, "--output"), "/out")
        self.assertIn(
            "--output=/private-out",
            paired._replace_argument(equals, "--output", "/private-out"),
        )


if __name__ == "__main__":
    unittest.main()
