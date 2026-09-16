from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
LEGACY_PATH = HERE / "_test_parity_legacy.py"

_spec = importlib.util.spec_from_file_location("_saas_migration_parity_legacy", LEGACY_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load retained parity suite: {LEGACY_PATH}")
legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(legacy)

parity = legacy.parity
secure_io = legacy.secure_io
FIXTURE_RAW = legacy.FIXTURE_RAW

# These two legacy assertions required failed publication to erase a reserved
# pathname. That contract cannot be made foreign-successor-safe without an
# atomic inode-conditional unlink primitive. Updated tests below retain the
# same scenarios but require fail-visible zero-byte tombstones instead.
_REPLACED = {
    ("FileAndCliTests", "test_parent_replacement_cannot_redirect_publication_or_cleanup"),
    ("FileAndCliTests", "test_cli_refuses_existing_second_output_without_leaving_first"),
}
_LEGACY_CASES = (
    "CompileTests",
    "StrictSchemaTests",
    "VerificationTests",
    "FileAndCliTests",
)


class RollbackCustodyTests(unittest.TestCase):
    def test_parent_replacement_preserves_new_generation_and_leaves_owned_tombstones(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            parent = td / "out"
            held = td / "held"
            parent.mkdir()
            calls = 0
            original = secure_io._write_all

            def swapping_write(fd, data):
                nonlocal calls
                original(fd, data)
                calls += 1
                if calls == 1:
                    parent.rename(held)
                    parent.mkdir()
                    (parent / "foreign.txt").write_text("foreign", encoding="utf-8")

            with mock.patch.object(secure_io, "_write_all", side_effect=swapping_write):
                with self.assertRaises(parity.ParityError):
                    secure_io.write_pair_exclusive(
                        parent / "report.json", b"json", parent / "report.md", b"md"
                    )

            self.assertEqual((parent / "foreign.txt").read_text(encoding="utf-8"), "foreign")
            self.assertFalse((parent / "report.json").exists())
            self.assertFalse((parent / "report.md").exists())
            self.assertEqual((held / "report.json").read_bytes(), b"")
            self.assertEqual((held / "report.md").read_bytes(), b"")

    def test_second_output_collision_leaves_first_reserved_tombstone(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inp = td / "input.json"
            report = td / "report.json"
            md = td / "report.md"
            inp.write_bytes(FIXTURE_RAW)
            md.write_text("occupied", encoding="utf-8")

            rc = parity.cli([
                "compile",
                "--input", str(inp),
                "--report-json", str(report),
                "--report-md", str(md),
            ])
            self.assertEqual(rc, 2)
            self.assertEqual(report.read_bytes(), b"")
            self.assertEqual(md.read_text(encoding="utf-8"), "occupied")

    def test_same_parent_foreign_successor_survives_rollback(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            report = td / "report.json"
            markdown = td / "report.md"
            moved_owned = td / "owned-report.json"
            calls = 0
            original = secure_io._write_all

            def substitute_then_fail(fd, data):
                nonlocal calls
                original(fd, data)
                calls += 1
                if calls == 1:
                    # The retained fd still names our inode after this rename, while
                    # the original pathname is immediately reused by foreign state.
                    report.rename(moved_owned)
                    report.write_bytes(b"FOREIGN-SUCCESSOR")
                    raise parity.ParityError("injected post-substitution failure")

            with mock.patch.object(secure_io, "_write_all", side_effect=substitute_then_fail):
                with self.assertRaises(parity.ParityError):
                    secure_io.write_pair_exclusive(report, b"owned-json", markdown, b"owned-md")

            self.assertEqual(report.read_bytes(), b"FOREIGN-SUCCESSOR")
            self.assertEqual(moved_owned.read_bytes(), b"")
            self.assertEqual(markdown.read_bytes(), b"")

    def test_post_validation_parent_fsync_substitution_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            report = td / "report.json"
            markdown = td / "report.md"
            moved_owned = td / "owned-report.json"
            swapped = False
            original_fsync = secure_io.os.fsync

            def substitute_from_parent_fsync(fd):
                nonlocal swapped
                is_directory = secure_io.stat.S_ISDIR(secure_io.os.fstat(fd).st_mode)
                try:
                    result = original_fsync(fd)
                except OSError:
                    if not is_directory:
                        raise
                    # Production intentionally tolerates directory-fsync rejection on
                    # filesystems that do not implement it. Preserve that behavior in
                    # the injected hook while still exercising the post-check seam.
                    result = None
                if is_directory and not swapped:
                    swapped = True
                    report.rename(moved_owned)
                    report.write_bytes(b"FOREIGN-SUCCESSOR")
                return result

            with mock.patch.object(secure_io.os, "fsync", side_effect=substitute_from_parent_fsync):
                with self.assertRaises(parity.ParityError):
                    secure_io.write_pair_exclusive(report, b"owned-json", markdown, b"owned-md")

            self.assertTrue(swapped)
            self.assertEqual(report.read_bytes(), b"FOREIGN-SUCCESSOR")
            self.assertEqual(moved_owned.read_bytes(), b"")
            self.assertEqual(markdown.read_bytes(), b"")


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    combined = unittest.TestSuite()
    for class_name in _LEGACY_CASES:
        case = getattr(legacy, class_name)
        for method_name in loader.getTestCaseNames(case):
            if (class_name, method_name) in _REPLACED:
                continue
            combined.addTest(case(method_name))
    combined.addTests(loader.loadTestsFromTestCase(RollbackCustodyTests))
    return combined


if __name__ == "__main__":
    unittest.main()
