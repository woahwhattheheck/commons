import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import host.json_object_patch_guard as guard


class JsonObjectPatchGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.input = self.root / "catalog.json"
        self.replacement = self.root / "replacement.json"
        self.output = self.root / "patched.json"
        self.input.write_text(
            '{\n'
            '  "meta": {"label": "café", "version": 1},\n'
            '  "listings": [\n'
            '    {"id": "alpha", "price": 10},\n'
            '    {\n'
            '      "id": "beta",\n'
            '      "price": 20,\n'
            '      "nested": {"keep": true}\n'
            '    }\n'
            '  ],\n'
            '  "tail": {"unchanged": [1, 2, 3]}\n'
            '}\n',
            encoding="utf-8",
        )
        self.replacement.write_text(
            '{\n'
            '  "id": "beta",\n'
            '  "price": 21,\n'
            '  "nested": {"keep": true},\n'
            '  "note": "patched"\n'
            '}\n',
            encoding="utf-8",
        )
        self.pointer = "/listings/1"
        inspected = guard.inspect_file(self.input, self.pointer)
        self.input_sha = inspected["input"]["sha256"]
        self.target_sha = inspected["target"]["raw_sha256"]

    def tearDown(self):
        self.temp.cleanup()

    def _patch(self):
        return guard.patch_file(
            self.input,
            self.pointer,
            self.replacement,
            self.output,
            expect_input_sha256=self.input_sha,
            expect_target_sha256=self.target_sha,
        )

    def test_inspect_reports_file_and_target_hashes(self):
        report = guard.inspect_file(self.input, self.pointer)
        self.assertTrue(report["ok"])
        self.assertEqual(report["input"]["sha256"], hashlib.sha256(self.input.read_bytes()).hexdigest())
        self.assertEqual(report["target"]["pointer"], self.pointer)
        self.assertGreater(report["target"]["prefix_bytes"], 0)
        self.assertGreater(report["target"]["suffix_bytes"], 0)

    def test_patch_changes_only_target_region(self):
        before = self.input.read_bytes()
        before_parsed = guard.SpanParser(before.decode()).parse()
        start, end = before_parsed.spans[self.pointer]
        prefix = before_parsed.text[:start].encode()
        suffix = before_parsed.text[end:].encode()

        report = self._patch()
        after = self.output.read_bytes()
        parsed = guard.SpanParser(after.decode()).parse()
        after_start, after_end = parsed.spans[self.pointer]
        self.assertEqual(after[:len(prefix)], prefix)
        self.assertEqual(parsed.text[after_end:].encode(), suffix)
        self.assertEqual(parsed.value["listings"][1]["price"], 21)
        self.assertEqual(parsed.value["meta"]["label"], "café")
        self.assertTrue(all(report["proof"].values()))

    def test_sibling_semantics_and_key_order_are_preserved(self):
        self._patch()
        before = guard.SpanParser(self.input.read_text(encoding="utf-8")).parse().value
        after = guard.SpanParser(self.output.read_text(encoding="utf-8")).parse().value
        self.assertEqual(before["meta"], after["meta"])
        self.assertEqual(before["listings"][0], after["listings"][0])
        self.assertEqual(before["tail"], after["tail"])
        self.assertEqual(list(before), list(after))

    def test_stale_input_hash_fails_before_output(self):
        with self.assertRaisesRegex(guard.PatchGuardError, "input SHA-256 changed"):
            guard.patch_file(
                self.input,
                self.pointer,
                self.replacement,
                self.output,
                expect_input_sha256="0" * 64,
                expect_target_sha256=self.target_sha,
            )
        self.assertFalse(self.output.exists())

    def test_stale_target_hash_fails_before_output(self):
        with self.assertRaisesRegex(guard.PatchGuardError, "target SHA-256 changed"):
            guard.patch_file(
                self.input,
                self.pointer,
                self.replacement,
                self.output,
                expect_input_sha256=self.input_sha,
                expect_target_sha256="0" * 64,
            )
        self.assertFalse(self.output.exists())

    def test_non_object_replacement_is_rejected(self):
        self.replacement.write_text('[1, 2, 3]\n', encoding="utf-8")
        with self.assertRaisesRegex(guard.PatchGuardError, "replacement root must be an object"):
            self._patch()

    def test_duplicate_input_key_is_rejected(self):
        self.input.write_text('{"a": 1, "a": 2}\n', encoding="utf-8")
        with self.assertRaisesRegex(guard.PatchGuardError, "duplicate JSON key"):
            guard.inspect_file(self.input, "")

    def test_non_finite_json_is_rejected(self):
        self.input.write_text('{"a": NaN}\n', encoding="utf-8")
        with self.assertRaisesRegex(guard.PatchGuardError, "non-finite JSON number"):
            guard.inspect_file(self.input, "")

    def test_existing_output_is_rejected(self):
        self.output.write_text("do not overwrite\n", encoding="utf-8")
        with self.assertRaisesRegex(guard.PatchGuardError, "output already exists"):
            self._patch()
        self.assertEqual(self.output.read_text(), "do not overwrite\n")

    def test_missing_pointer_is_rejected(self):
        with self.assertRaisesRegex(guard.PatchGuardError, "pointer does not resolve"):
            guard.inspect_file(self.input, "/listings/99")

    def test_escaped_pointer_key_is_supported(self):
        special = self.root / "special.json"
        special.write_text('{"a/b": {"~key": {"x": 1}}}\n', encoding="utf-8")
        report = guard.inspect_file(special, "/a~1b/~0key")
        self.assertTrue(report["ok"])

    def test_cli_distinguishes_success_and_guard_failure(self):
        self.assertEqual(guard.main(["inspect", "--input", str(self.input), "--pointer", self.pointer]), 0)
        self.assertEqual(
            guard.main([
                "patch",
                "--input", str(self.input),
                "--pointer", self.pointer,
                "--replacement", str(self.replacement),
                "--output", str(self.output),
                "--expect-input-sha256", "0" * 64,
                "--expect-target-sha256", self.target_sha,
            ]),
            2,
        )
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
