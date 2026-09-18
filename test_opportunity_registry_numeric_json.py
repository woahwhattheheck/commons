"""Numeric JSON contracts through the real registry parser, files and CLI."""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host import opportunity_registry as registry


class NumericJSONTests(unittest.TestCase):
    def test_positive_exponent_overflow(self):
        with self.assertRaisesRegex(registry.RegistryError, "non-finite JSON number"):
            registry._parse_json("1e400", "number")

    def test_negative_exponent_overflow(self):
        with self.assertRaisesRegex(registry.RegistryError, "non-finite JSON number"):
            registry._parse_json("-1E+400", "number")

    def test_overflow_at_float_boundary(self):
        with self.assertRaisesRegex(registry.RegistryError, "non-finite JSON number"):
            registry._parse_json("1.7976931348623159e308", "number")

    def test_overflow_inside_nested_container(self):
        with self.assertRaisesRegex(registry.RegistryError, "non-finite JSON number"):
            registry._parse_json('{"offers":[{"price":{"amount":1e400}}]}', "offers")

    def test_decimal_without_exponent_can_overflow(self):
        with self.assertRaisesRegex(registry.RegistryError, "non-finite JSON number"):
            registry._parse_json("9" * 400 + ".0", "number")

    def test_named_nonfinite_constants_keep_their_diagnostic(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token):
                with self.assertRaisesRegex(registry.RegistryError, "non-finite JSON constant"):
                    registry._parse_json('[{"value":' + token + '}]', "number")

    def test_finite_float_values_and_types_match_standard_json(self):
        for token in ("1.0", "-123.75", "1e-6", "1E+12", "1e308",
                      "1.7976931348623157e308", "-1.7976931348623157e308", "5e-324"):
            with self.subTest(token=token):
                actual = registry._parse_json(token, "number")
                self.assertIs(type(actual), float)
                self.assertTrue(math.isfinite(actual))
                self.assertEqual(actual, json.loads(token))

    def test_float_negative_zero_is_preserved(self):
        for token in ("-0.0", "-0e400", "-1e-400"):
            with self.subTest(token=token):
                actual = registry._parse_json(token, "number")
                self.assertIs(type(actual), float)
                self.assertEqual(actual, 0.0)
                self.assertEqual(math.copysign(1, actual), -1)

    def test_underflow_keeps_existing_float_semantics(self):
        for token in ("1e-400", "0e400"):
            with self.subTest(token=token):
                actual = registry._parse_json(token, "number")
                self.assertEqual(actual, json.loads(token))
                self.assertIs(type(actual), float)
                self.assertTrue(math.isfinite(actual))

    def test_integer_values_stay_exact_and_do_not_pass_through_float(self):
        for token in ("0", "-42", "9007199254740993", "9" * 400):
            with self.subTest(token=token[:30]):
                actual = registry._parse_json(token, "number")
                self.assertIs(type(actual), int)
                self.assertEqual(actual, int(token))

    def test_other_json_values_and_numeric_strings_are_unchanged(self):
        text = '[true,false,null,"1e400",{"sku":"0001","amount":12.50}]'
        actual = registry._parse_json(text, "mixed")
        self.assertEqual(actual, json.loads(text))
        self.assertIs(actual[0], True)
        self.assertIs(actual[1], False)
        self.assertIsNone(actual[2])
        self.assertEqual(actual[3], "1e400")

    def test_duplicate_keys_still_raise_at_any_depth(self):
        for text in ('{"x":1,"x":2}', '[{"nested":{"x":1.5,"x":2.5}}]'):
            with self.subTest(text=text):
                with self.assertRaisesRegex(registry.RegistryError, "duplicate JSON key"):
                    registry._parse_json(text, "duplicates")

    def test_malformed_json_keeps_source_label(self):
        for text in ("1e", "[1.0,]", '{"value":.5}'):
            with self.subTest(text=text):
                with self.assertRaisesRegex(registry.RegistryError, "source is malformed JSON"):
                    registry._parse_json(text, "source")

    def test_finite_canonical_roundtrip_is_unchanged(self):
        text = '{"z":[1.25,1e308],"a":"caf\u00e9","integer":9007199254740993}'
        actual = registry._parse_json(text, "roundtrip")
        expected = json.dumps(json.loads(text), sort_keys=True,
                              separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(registry.canonical_dumps(actual), expected)
        self.assertEqual(registry._parse_json(expected, "roundtrip"), actual)

    def test_load_reads_finite_values_from_selected_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / registry.REGISTRY_PATH).parent.mkdir(parents=True)
            (root / registry.REGISTRY_PATH).write_text('{"value":12.5}', encoding="utf-8")
            (root / registry.SCHEMA_PATH).write_text('{"limit":1e308}', encoding="utf-8")
            self.assertEqual(registry.load(root), ({"value": 12.5}, {"limit": 1e308}))

    def test_load_rejects_overflow_from_either_file_without_writes(self):
        for failing_path in (registry.REGISTRY_PATH, registry.SCHEMA_PATH):
            with self.subTest(path=str(failing_path)), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / registry.REGISTRY_PATH).parent.mkdir(parents=True)
                originals = {}
                for path in (registry.REGISTRY_PATH, registry.SCHEMA_PATH):
                    raw = b'{"value":1e400}' if path == failing_path else b'{}'
                    (root / path).write_bytes(raw)
                    originals[path] = raw
                with self.assertRaisesRegex(registry.RegistryError, "non-finite JSON number"):
                    registry.load(root)
                self.assertEqual({path: (root / path).read_bytes() for path in originals}, originals)

    def test_cli_compile_reports_overflow_and_preserves_all_prior_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            schema = root / registry.SCHEMA_PATH
            schema.parent.mkdir(parents=True)
            schema.write_text('{"ignored":1e400}', encoding="utf-8")
            originals = {}
            for path in (registry.REGISTRY_PATH, registry.HTML_PATH, registry.PROOF_PATH,
                         registry.PACKET_DIR / "previous.md"):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                raw = ("previous bytes: " + str(path)).encode("utf-8")
                target.write_bytes(raw)
                originals[path] = raw
            result = subprocess.run(
                [sys.executable, str(Path(registry.__file__).resolve()), "compile", "--root", str(root)],
                text=True, capture_output=True, timeout=10,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("OPPORTUNITY REGISTRY INVALID: non-finite JSON number", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual({path: (root / path).read_bytes() for path in originals}, originals)


if __name__ == "__main__":
    unittest.main()
