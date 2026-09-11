import json
import os
import tempfile
import unittest
from pathlib import Path

from large_json_patch import PatchError, main, patch_json_object, sha256_bytes


SOURCE = b'{"target":{"x":1},"tail":0}'
TARGET = b'{"x":1}'
REPLACEMENT = b'{"x":2}'


def cli_args(source: Path, replacement: Path, output: Path, receipt: Path | None = None):
    args = [
        str(source),
        "--pointer", "/target",
        "--expected-file-sha256", sha256_bytes(SOURCE),
        "--expected-target-sha256", sha256_bytes(TARGET),
        "--replacement-file", str(replacement),
        "--output", str(output),
    ]
    if receipt is not None:
        args.extend(["--receipt", str(receipt)])
    return args


class StrictJsonTests(unittest.TestCase):
    def test_rejects_nonstandard_constants_in_source(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                source = ('{"target":{"x":1},"bad":%s}' % constant).encode()
                with self.assertRaisesRegex(PatchError, "non-standard JSON constant"):
                    patch_json_object(
                        source,
                        pointer="/target",
                        expected_file_sha256=sha256_bytes(source),
                        expected_target_sha256=sha256_bytes(TARGET),
                        replacement=REPLACEMENT,
                    )

    def test_rejects_nonstandard_constants_in_replacement(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                replacement = ('{"x":%s}' % constant).encode()
                with self.assertRaisesRegex(PatchError, "non-standard JSON constant"):
                    patch_json_object(
                        SOURCE,
                        pointer="/target",
                        expected_file_sha256=sha256_bytes(SOURCE),
                        expected_target_sha256=sha256_bytes(TARGET),
                        replacement=replacement,
                    )

    def test_rejects_byte_identical_replacement(self):
        with self.assertRaisesRegex(PatchError, "byte-identical"):
            patch_json_object(
                SOURCE,
                pointer="/target",
                expected_file_sha256=sha256_bytes(SOURCE),
                expected_target_sha256=sha256_bytes(TARGET),
                replacement=TARGET,
            )

    def test_normal_json_still_patches_and_preserves_outside_bytes(self):
        patched, receipt = patch_json_object(
            SOURCE,
            pointer="/target",
            expected_file_sha256=sha256_bytes(SOURCE),
            expected_target_sha256=sha256_bytes(TARGET),
            replacement=REPLACEMENT,
        )
        self.assertEqual(patched, b'{"target":{"x":2},"tail":0}')
        self.assertEqual(json.loads(patched), {"target": {"x": 2}, "tail": 0})
        self.assertTrue(receipt["outside_target_bytes_preserved"])


class ProductAliasTests(unittest.TestCase):
    def fixture(self, root: Path):
        source = root / "source.json"
        replacement = root / "replacement.json"
        source.write_bytes(SOURCE)
        replacement.write_bytes(REPLACEMENT)
        return source, replacement

    def assert_inputs_unchanged(self, source: Path, replacement: Path):
        self.assertEqual(source.read_bytes(), SOURCE)
        self.assertEqual(replacement.read_bytes(), REPLACEMENT)

    def test_receipt_cannot_overwrite_source_and_output_is_not_created(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, replacement = self.fixture(root)
            output = root / "out.json"
            with self.assertRaisesRegex(PatchError, "receipt must differ from source"):
                main(cli_args(source, replacement, output, source))
            self.assert_inputs_unchanged(source, replacement)
            self.assertFalse(output.exists())

    def test_receipt_cannot_overwrite_replacement_and_output_is_not_created(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, replacement = self.fixture(root)
            output = root / "out.json"
            with self.assertRaisesRegex(PatchError, "receipt must differ from replacement"):
                main(cli_args(source, replacement, output, replacement))
            self.assert_inputs_unchanged(source, replacement)
            self.assertFalse(output.exists())

    def test_receipt_cannot_overwrite_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, replacement = self.fixture(root)
            output = root / "out.json"
            with self.assertRaisesRegex(PatchError, "receipt must differ from output"):
                main(cli_args(source, replacement, output, output))
            self.assert_inputs_unchanged(source, replacement)
            self.assertFalse(output.exists())

    def test_output_cannot_overwrite_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, replacement = self.fixture(root)
            with self.assertRaisesRegex(PatchError, "output must differ from replacement"):
                main(cli_args(source, replacement, replacement))
            self.assert_inputs_unchanged(source, replacement)

    def test_output_cannot_overwrite_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, replacement = self.fixture(root)
            with self.assertRaisesRegex(PatchError, "output must differ from source"):
                main(cli_args(source, replacement, source))
            self.assert_inputs_unchanged(source, replacement)

    def test_existing_hardlink_alias_is_rejected_before_write(self):
        if not hasattr(os, "link"):
            self.skipTest("hard links unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, replacement = self.fixture(root)
            alias = root / "source-alias.json"
            os.link(source, alias)
            output = root / "out.json"
            with self.assertRaisesRegex(PatchError, "receipt must differ from source"):
                main(cli_args(source, replacement, output, alias))
            self.assert_inputs_unchanged(source, replacement)
            self.assertEqual(alias.read_bytes(), SOURCE)
            self.assertFalse(output.exists())

    def test_symlink_alias_is_rejected_before_write(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, replacement = self.fixture(root)
            alias = root / "replacement-alias.json"
            try:
                alias.symlink_to(replacement)
            except OSError as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            output = root / "out.json"
            with self.assertRaisesRegex(PatchError, "receipt must differ from replacement"):
                main(cli_args(source, replacement, output, alias))
            self.assert_inputs_unchanged(source, replacement)
            self.assertFalse(output.exists())

    def test_distinct_products_succeed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, replacement = self.fixture(root)
            output = root / "out.json"
            receipt = root / "receipt.json"
            self.assertEqual(0, main(cli_args(source, replacement, output, receipt)))
            self.assert_inputs_unchanged(source, replacement)
            self.assertEqual(output.read_bytes(), b'{"target":{"x":2},"tail":0}')
            proof = json.loads(receipt.read_text())
            self.assertEqual(proof["before_sha256"], sha256_bytes(SOURCE))
            self.assertEqual(proof["after_sha256"], sha256_bytes(output.read_bytes()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
