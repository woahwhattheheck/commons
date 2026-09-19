"""Executable regression cases for exact JSON semantics and usable diagnostics."""
import copy
import csv
import io
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

import transport as t


class TransportTests(unittest.TestCase):
    def roundtrip(self, value):
        recovered = t.from_rows(t.to_rows(value))
        self.assertEqual(t.canonical_json(recovered), t.canonical_json(value))
        return recovered

    def test_scalars_and_empty_containers(self):
        for value in [None, True, False, 0, -1, 2**90, 0.0, -0.0, 1.23e-100,
                      "", "null", {}, []]:
            with self.subTest(value=value):
                self.roundtrip(value)

    def test_absent_null_empty_false_zero_distinct(self):
        value = [{}, {"value": None}, {"value": ""}, {"value": False},
                 {"value": 0}, {"value": []}, {"value": {}}]
        self.roundtrip(value)
        self.assertEqual(len({t.document_sha256(x) for x in value}), 7)

    def test_integer_float_boolean_distinct(self):
        self.assertEqual(len({t.document_sha256(x) for x in [1, 1.0, True]}), 3)

    def test_negative_zero(self):
        self.assertEqual(math.copysign(1, self.roundtrip(-0.0)), -1)

    def test_unicode_combining_and_controls(self):
        self.roundtrip({"é": "e\u0301", "資料": "Δ — café", "notes": "a\r\nb\nc\t\u0000"})

    def test_pointer_escape_empty_and_numeric_keys(self):
        self.roundtrip({"": {"/~0~1": "value"}, "0": [{"a/b": 1}]})

    def test_exact_dates_identifiers_and_decimal_strings(self):
        self.roundtrip({"date": "2026-09-19T09:00:00-04:00", "id": "000123",
                        "amount": "24.00", "large": 9007199254740993})

    def test_formula_strings_are_transport_text(self):
        rows = t.to_rows({"=field": ["=SUM(1,2)", "+1", "-2", "@SUM(A1)", "'x"]})
        for row in rows:
            for value in row:
                self.assertFalse(value.startswith(("=", "+", "-", "@")))
        self.roundtrip({"formula": "=SUM(1,2)"})

    def test_csv_roundtrip_multiline_and_large_field(self):
        value = {"note": "line1\r\nline2,\"quoted\"" + "x" * 140000}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.csv"
            t.write_csv(value, path)
            self.assertEqual(value, t.read_csv(path))

    def test_existing_outputs_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "existing"
            path.write_text("retained")
            for writer in (t.write_csv, t.write_json):
                with self.assertRaises(FileExistsError):
                    writer({}, path)
            self.assertEqual(path.read_text(), "retained")

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(t.InterchangeError):
            t.loads('{"a":1,"a":2}')

    def test_nonfinite_numbers_rejected(self):
        for text in ["NaN", "Infinity", "-Infinity", "1e999"]:
            with self.subTest(text=text), self.assertRaises(t.InterchangeError):
                t.loads(text)

    def test_non_json_objects_and_surrogates_rejected(self):
        for value in [{1: "x"}, (1, 2), float("nan"), "\ud800"]:
            with self.subTest(value=repr(value)), self.assertRaises(t.InterchangeError):
                t.to_rows(value)

    def test_bad_header_and_row_width(self):
        for mutation in [lambda r: r.__setitem__(0, ["v999", "", ""]),
                         lambda r: r.append(["extra"])]:
            rows = t.to_rows({"a": 1}); mutation(rows)
            with self.assertRaises(t.InterchangeError):
                t.from_rows(rows)

    def test_missing_and_extra_nodes_rejected(self):
        rows = t.to_rows({"a": [1, 2]})
        for mutated in [rows[:-1], rows + [rows[-1]]]:
            with self.assertRaises(t.InterchangeError):
                t.from_rows(mutated)

    def test_reordered_array_rejected(self):
        rows = t.to_rows([1, 2]); rows[-2:] = reversed(rows[-2:])
        with self.assertRaises(t.InterchangeError):
            t.from_rows(rows)

    def test_duplicate_object_member_rejected(self):
        rows = t.to_rows({"a": 1, "b": 2}); rows[-1] = rows[-2].copy()
        with self.assertRaises(t.InterchangeError):
            t.from_rows(rows)

    def test_kind_literal_disagreement(self):
        rows = t.to_rows(True); rows[-1][1] = "integer"
        with self.assertRaises(t.InterchangeError):
            t.from_rows(rows)

    def test_bad_pointer_escape(self):
        rows = t.to_rows({"a": 1}); rows[-1][0] = 'p:"/~2"'
        with self.assertRaises(t.InterchangeError):
            t.from_rows(rows)

    def test_nontext_cell_and_missing_prefix(self):
        for value in [42, "=1+1"]:
            rows = t.to_rows("x"); rows[-1][2] = value
            with self.assertRaises(t.InterchangeError):
                t.from_rows(rows)

    def test_depth_limit_explicit(self):
        value = None
        for _ in range(130):
            value = [value]
        with self.assertRaises(t.InterchangeError):
            t.to_rows(value)

    def test_seeded_nested_cases(self):
        rng = random.Random(18649)
        def sample(depth):
            scalar = rng.choice([None, True, False, "", "a/b~", 2**64, -0.0, "2026-09-19"])
            if depth == 0:
                return scalar
            kind = rng.randrange(3)
            if kind == 0:
                return [sample(depth-1) for _ in range(rng.randrange(5))]
            if kind == 1:
                return {str(i)+"/~": sample(depth-1) for i in range(rng.randrange(4))}
            return scalar
        for _ in range(150):
            self.roundtrip(sample(4))

    def test_cli_workflow(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, csvfile, restored = (root / n for n in ["in.json", "data.csv", "out.json"])
            t.write_json({"authority": False, "score": None}, source)
            for action, a, b in [("export", source, csvfile), ("import", csvfile, restored),
                                 ("compare", source, restored)]:
                result = subprocess.run([sys.executable, str(Path(t.__file__)), action, str(a), str(b)],
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("FORMAT_INTEGRITY_ONLY", result.stdout)


if __name__ == "__main__":
    unittest.main()
