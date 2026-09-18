import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from large_json_patch import PatchError, main, patch_json_object, sha256_bytes


def target_sha(source: bytes, literal: bytes) -> str:
    if source.count(literal) != 1:
        raise AssertionError("fixture target must be unique")
    return hashlib.sha256(literal).hexdigest()


class PatchJsonObjectTests(unittest.TestCase):
    def setUp(self):
        self.source = (
            b'{\n  "meta": {"keep": true},\n  "offers": [\n'
            b'    { "sku": "alpha", "price": 49 },\n'
            b'    {"sku":"beta","price":250,"note":"caf\\u00e9"}\n'
            b'  ],\n  "tail": { "unchanged": [1, 2, 3] }\n}\n'
        )
        self.target = b'{"sku":"beta","price":250,"note":"caf\\u00e9"}'

    def patch(self, replacement=b'{"sku":"beta","price":299,"note":"caf\\u00e9"}', **kwargs):
        params = dict(
            pointer="/offers/1",
            expected_file_sha256=sha256_bytes(self.source),
            expected_target_sha256=target_sha(self.source, self.target),
            replacement=replacement,
        )
        params.update(kwargs)
        return patch_json_object(self.source, **params)

    def test_replaces_only_target_bytes_and_preserves_semantics_elsewhere(self):
        patched, receipt = self.patch()
        before_prefix, before_suffix = self.source.split(self.target)
        new_target = b'{"sku":"beta","price":299,"note":"caf\\u00e9"}'
        self.assertEqual(patched, before_prefix + new_target + before_suffix)
        self.assertTrue(receipt["outside_target_bytes_preserved"])
        before = json.loads(self.source)
        after = json.loads(patched)
        self.assertEqual(before["meta"], after["meta"])
        self.assertEqual(before["offers"][0], after["offers"][0])
        self.assertEqual(before["tail"], after["tail"])
        self.assertEqual(299, after["offers"][1]["price"])

    def test_unicode_before_target_uses_byte_offsets_not_character_offsets(self):
        source = '{"label":"café 🚀","target": {"a":1},"tail":2}\n'.encode("utf-8")
        target = b'{"a":1}'
        patched, _ = patch_json_object(
            source,
            pointer="/target",
            expected_file_sha256=sha256_bytes(source),
            expected_target_sha256=sha256_bytes(target),
            replacement=b'{"a":2}',
        )
        self.assertEqual(source.split(target)[0] + b'{"a":2}' + source.split(target)[1], patched)

    def test_pointer_escapes_slash_and_tilde(self):
        source = b'{"a/b":{"~key":{"x":1}},"keep":0}'
        target = b'{"x":1}'
        patched, _ = patch_json_object(
            source,
            pointer="/a~1b/~0key",
            expected_file_sha256=sha256_bytes(source),
            expected_target_sha256=sha256_bytes(target),
            replacement=b'{"x":2}',
        )
        self.assertEqual({"a/b": {"~key": {"x": 2}}, "keep": 0}, json.loads(patched))

    def test_rejects_whole_file_preimage_drift(self):
        with self.assertRaisesRegex(PatchError, "file SHA-256 mismatch"):
            self.patch(expected_file_sha256="0" * 64)

    def test_rejects_target_preimage_drift(self):
        with self.assertRaisesRegex(PatchError, "target SHA-256 mismatch"):
            self.patch(expected_target_sha256="0" * 64)

    def test_rejects_missing_pointer(self):
        with self.assertRaisesRegex(PatchError, "does not resolve"):
            self.patch(pointer="/offers/9")

    def test_rejects_scalar_target(self):
        scalar = b'250'
        with self.assertRaisesRegex(PatchError, "target JSON value must be an object"):
            self.patch(pointer="/offers/1/price", expected_target_sha256=sha256_bytes(scalar))

    def test_rejects_non_object_replacement(self):
        with self.assertRaisesRegex(PatchError, "replacement JSON value must be an object"):
            self.patch(replacement=b'[1,2,3]')

    def test_rejects_duplicate_key_in_source(self):
        source = b'{"target":{"a":1,"a":2}}'
        with self.assertRaisesRegex(PatchError, "duplicate object key"):
            patch_json_object(
                source,
                pointer="/target",
                expected_file_sha256=sha256_bytes(source),
                expected_target_sha256=sha256_bytes(b'{"a":1,"a":2}'),
                replacement=b'{"a":3}',
            )

    def test_rejects_duplicate_key_in_replacement(self):
        with self.assertRaisesRegex(PatchError, "duplicate object key"):
            self.patch(replacement=b'{"sku":"beta","sku":"evil"}')

    def test_rejects_invalid_pointer_escape(self):
        with self.assertRaisesRegex(PatchError, "invalid JSON Pointer escape"):
            self.patch(pointer="/offers/~2")

    def test_cli_output_and_receipt_are_atomic_products(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "source.json"
            repl = root / "replacement.json"
            out = root / "out.json"
            receipt = root / "receipt.json"
            src.write_bytes(self.source)
            repl.write_bytes(b'{"sku":"beta","price":299,"note":"caf\\u00e9"}')
            rc = main([
                str(src),
                "--pointer", "/offers/1",
                "--expected-file-sha256", sha256_bytes(self.source),
                "--expected-target-sha256", sha256_bytes(self.target),
                "--replacement-file", str(repl),
                "--output", str(out),
                "--receipt", str(receipt),
            ])
            self.assertEqual(0, rc)
            self.assertEqual(299, json.loads(out.read_text())["offers"][1]["price"])
            proof = json.loads(receipt.read_text())
            self.assertTrue(proof["outside_target_bytes_preserved"])
            self.assertEqual(sha256_bytes(self.source), proof["before_sha256"])

    def test_cli_refuses_overwriting_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "source.json"
            repl = root / "replacement.json"
            src.write_bytes(self.source)
            repl.write_bytes(b'{"sku":"beta","price":299,"note":"caf\\u00e9"}')
            with self.assertRaisesRegex(PatchError, "never overwrites its input"):
                main([
                    str(src),
                    "--pointer", "/offers/1",
                    "--expected-file-sha256", sha256_bytes(self.source),
                    "--expected-target-sha256", sha256_bytes(self.target),
                    "--replacement-file", str(repl),
                    "--output", str(src),
                ])


if __name__ == "__main__":
    unittest.main()
