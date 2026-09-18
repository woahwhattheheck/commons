from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from .cli import _open_retained_parent, _read_regular, _write_exclusive, _write_exclusive_at
from .core import ValidationError


class CliIoTests(unittest.TestCase):
    def test_write_exclusive_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "out.json"
            _write_exclusive(p, b"first")
            with self.assertRaises(ValidationError):
                _write_exclusive(p, b"second")
            self.assertEqual(b"first", p.read_bytes())

    def test_write_exclusive_refuses_symlink_target(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.write_bytes(b"keep")
            link = Path(td) / "link"
            os.symlink(target, link)
            with self.assertRaises(ValidationError):
                _write_exclusive(link, b"replace")
            self.assertEqual(b"keep", target.read_bytes())

    def test_read_regular_refuses_symlink(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.write_bytes(b"{}")
            link = Path(td) / "link"
            os.symlink(target, link)
            with self.assertRaises(ValidationError):
                _read_regular(link)

    def test_read_regular_refuses_directory(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValidationError):
                _read_regular(td)

    def test_read_regular_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "in.json"
            p.write_bytes(b'{"ok":true}')
            self.assertEqual(b'{"ok":true}', _read_regular(p))

    def test_read_regular_refuses_symlink_ancestor(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            real = Path(td) / "real"
            real.mkdir()
            target = real / "in.json"
            target.write_bytes(b'{"ok":true}')
            link_parent = Path(td) / "via"
            os.symlink(real, link_parent)
            with self.assertRaises(ValidationError):
                _read_regular(link_parent / "in.json")

    def test_write_exclusive_refuses_symlink_ancestor(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            real = Path(td) / "real"
            real.mkdir()
            link_parent = Path(td) / "via"
            os.symlink(real, link_parent)
            with self.assertRaises(ValidationError):
                _write_exclusive(link_parent / "out.json", b"payload")
            self.assertFalse((real / "out.json").exists())

    def test_write_stays_in_retained_parent_after_replacement(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = root / "held"
            original.mkdir()
            replacement = root / "other"
            replacement.mkdir()
            decoy = replacement / "out.json"
            decoy.write_bytes(b"decoy")
            dest = original / "out.json"
            parent_fd, name = _open_retained_parent(dest)
            try:
                os.rename(original, root / "held-moved")
                os.rename(replacement, original)
                _write_exclusive_at(parent_fd, name, b"retained", display_path=str(dest))
            finally:
                os.close(parent_fd)
            self.assertEqual(b"retained", (root / "held-moved" / "out.json").read_bytes())
            self.assertEqual(b"decoy", (original / "out.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
