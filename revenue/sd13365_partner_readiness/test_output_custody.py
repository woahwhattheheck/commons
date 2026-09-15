from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _atomic_output
import assemble_requirements
import matrix


HERE = Path(__file__).resolve().parent
PAYLOAD = HERE / "requirements.json.gz.b64"


class OutputCustodyTests(unittest.TestCase):
    def setUp(self) -> None:
        missing = [name for name in ("O_DIRECTORY", "O_NOFOLLOW") if not hasattr(os, name)]
        if missing:
            self.skipTest("retained dirfd/no-follow output is unavailable")

    def _install_parent_swap(self, parent: Path, moved: Path, attacker: Path):
        real_replace = _atomic_output.os.replace
        swapped = False

        def swap_then_replace(
            src: str,
            dst: str,
            *,
            src_dir_fd: int | None = None,
            dst_dir_fd: int | None = None,
        ) -> None:
            nonlocal swapped
            if not swapped:
                parent.rename(moved)
                try:
                    parent.symlink_to(attacker, target_is_directory=True)
                except (OSError, NotImplementedError) as exc:
                    moved.rename(parent)
                    raise unittest.SkipTest("directory symlinks unavailable") from exc
                swapped = True
            real_replace(
                src,
                dst,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=dst_dir_fd,
            )

        return mock.patch.object(_atomic_output.os, "replace", side_effect=swap_then_replace)

    def _assert_attacker_untouched(self, attacker: Path, leaf: str) -> None:
        self.assertFalse((attacker / leaf).exists())
        self.assertEqual(list(attacker.iterdir()), [])

    def test_matrix_materializer_parent_swap_cannot_redirect_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "publish"
            moved = root / "publish-owned-generation"
            attacker = root / "attacker"
            parent.mkdir()
            attacker.mkdir()
            output = parent / "requirements.json"

            with self._install_parent_swap(parent, moved, attacker):
                with self.assertRaisesRegex(
                    assemble_requirements.AssemblyError,
                    "generation changed",
                ):
                    assemble_requirements.assemble(PAYLOAD, output)

            self._assert_attacker_untouched(attacker, output.name)
            self.assertTrue((moved / output.name).is_file())
            self.assertEqual(
                (moved / output.name).read_bytes(),
                assemble_requirements.decode_payload(PAYLOAD),
            )
            self.assertEqual(
                [child.name for child in moved.iterdir() if child.name.endswith(".tmp")],
                [],
            )

    def test_receipt_writer_parent_swap_cannot_redirect_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "publish"
            moved = root / "publish-owned-generation"
            attacker = root / "attacker"
            parent.mkdir()
            attacker.mkdir()
            output = parent / "receipt.json"

            with self._install_parent_swap(parent, moved, attacker):
                with self.assertRaisesRegex(matrix.MatrixError, "generation changed"):
                    matrix.write_receipt(output, {"ok": True})

            self._assert_attacker_untouched(attacker, output.name)
            self.assertEqual(
                (moved / output.name).read_text(encoding="utf-8"),
                '{\n  "ok": true\n}\n',
            )
            self.assertEqual(
                [child.name for child in moved.iterdir() if child.name.endswith(".tmp")],
                [],
            )

    def test_symlink_parent_is_rejected_before_any_leaf_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            attacker = root / "attacker"
            attacker.mkdir()
            parent = root / "publish"
            try:
                parent.symlink_to(attacker, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlinks unavailable")

            with self.assertRaises(assemble_requirements.AssemblyError):
                assemble_requirements.write_atomic(parent / "matrix.json", b"{}\n")
            with self.assertRaises(matrix.MatrixError):
                matrix.write_receipt(parent / "receipt.json", {"ok": True})
            self.assertEqual(list(attacker.iterdir()), [])

    def test_regular_existing_leaf_is_replaced_in_same_directory_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "receipt.json"
            output.write_text("old\n", encoding="utf-8")
            matrix.write_receipt(output, {"ok": True})
            self.assertEqual(output.read_text(encoding="utf-8"), '{\n  "ok": true\n}\n')


if __name__ == "__main__":
    unittest.main()
