from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import assemble_requirements
import matrix
import safe_output


_POSIX_DIRFD = (
    os.name == "posix"
    and isinstance(getattr(os, "O_DIRECTORY", None), int)
    and bool(getattr(os, "O_DIRECTORY", 0))
    and isinstance(getattr(os, "O_NOFOLLOW", None), int)
    and bool(getattr(os, "O_NOFOLLOW", 0))
    and hasattr(os, "symlink")
)


@unittest.skipUnless(_POSIX_DIRFD, "requires POSIX no-follow retained-dirfd output")
class OutputCustodyTests(unittest.TestCase):
    @staticmethod
    def _swap_parent_once(parent: Path, held: Path, attacker: Path):
        real_verify = safe_output._verify_parent_identity
        swapped = False

        def swap_then_verify(path: Path, expected: tuple[int, int]) -> None:
            nonlocal swapped
            if not swapped:
                os.rename(parent, held)
                attacker.mkdir()
                parent.symlink_to(attacker, target_is_directory=True)
                swapped = True
            real_verify(path, expected)

        return swap_then_verify

    def test_materializer_parent_swap_fails_closed_without_redirected_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "live"
            parent.mkdir()
            held = root / "held"
            attacker = root / "attacker"
            output = parent / "requirements.json"
            hook = self._swap_parent_once(parent, held, attacker)

            with mock.patch.object(safe_output, "_verify_parent_identity", side_effect=hook):
                with self.assertRaisesRegex(
                    assemble_requirements.AssemblyError,
                    "unsafe output custody",
                ):
                    assemble_requirements.write_atomic(output, b'{"reviewed":true}\n')

            self.assertFalse((attacker / output.name).exists())
            self.assertFalse((held / output.name).exists())
            self.assertEqual(list(held.glob(f".{output.name}.*.tmp")), [])

    def test_receipt_parent_swap_fails_closed_without_redirected_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "live"
            parent.mkdir()
            held = root / "held"
            attacker = root / "attacker"
            output = parent / "receipt.json"
            hook = self._swap_parent_once(parent, held, attacker)

            with mock.patch.object(safe_output, "_verify_parent_identity", side_effect=hook):
                with self.assertRaisesRegex(matrix.MatrixError, "unsafe receipt output custody"):
                    matrix.write_receipt(output, {"classification": "UNKNOWN"})

            self.assertFalse((attacker / output.name).exists())
            self.assertFalse((held / output.name).exists())
            self.assertEqual(list(held.glob(f".{output.name}.*.tmp")), [])

    def test_ancestor_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            attacker = root / "attacker"
            attacker.mkdir()
            link = root / "link"
            link.symlink_to(attacker, target_is_directory=True)
            with self.assertRaisesRegex(
                safe_output.OutputCustodyError,
                "not a safe ordinary directory",
            ):
                safe_output.atomic_write_bytes(link / "nested" / "receipt.json", b"{}\n")
            self.assertFalse((attacker / "nested" / "receipt.json").exists())

    def test_safe_nested_output_commits_through_retained_dirfd(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "a" / "b" / "receipt.json"
            safe_output.atomic_write_bytes(output, b'{"ok":true}\n')
            self.assertEqual(output.read_bytes(), b'{"ok":true}\n')


if __name__ == "__main__":
    unittest.main()
