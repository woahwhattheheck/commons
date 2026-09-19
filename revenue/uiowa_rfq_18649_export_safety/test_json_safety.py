#!/usr/bin/env python3
"""Regression tests for the JSON strict-parser conformance auditor.

Run:  python3 -m unittest -v   (from this directory)
"""

import json
import os
import shutil
import tempfile
import unittest

import json_safety as js

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures", "json")


def scan_one(name):
    return js.scan_json(os.path.join(FIXTURES, name), "fixtures", name)


def codes(findings):
    return sorted(f["code"] for f in findings)


class Checks(unittest.TestCase):
    def test_bare_nan_and_infinity_are_high(self):
        findings = scan_one("nonstrict.json")
        self.assertEqual(codes(findings), ["NON_STRICT_LITERAL"] * 3)
        self.assertEqual({f["severity"] for f in findings}, {js.HIGH})
        self.assertEqual({f["sample"] for f in findings},
                         {"NaN", "Infinity", "-Infinity"})
        self.assertEqual({f["location"] for f in findings}, {"value"})
        self.assertIn("allow_nan=False", findings[0]["detail"])

    def test_duplicate_object_key_is_caught_though_python_accepts_it(self):
        """json.load keeps the last value and raises nothing, so the earlier one
        is lost with no error anywhere."""
        with open(os.path.join(FIXTURES, "duplicate_keys.json"), encoding="utf-8") as fh:
            parsed = json.load(fh)
        self.assertEqual(parsed["finding_id"], "F-2")   # the first value is gone
        findings = scan_one("duplicate_keys.json")
        self.assertEqual(codes(findings), ["DUPLICATE_OBJECT_KEY"])
        self.assertEqual(findings[0]["location"], "finding_id")

    def test_invalid_json_is_reported(self):
        self.assertEqual(codes(scan_one("invalid.json")), ["INVALID_JSON"])

    def test_integer_beyond_2_53_is_flagged_and_the_safe_one_is_not(self):
        findings = scan_one("big_int.json")
        self.assertEqual(codes(findings), ["INT_PRECISION_LOSS"])
        self.assertEqual(findings[0]["location"], "$.count")

    def test_control_character_in_a_string(self):
        self.assertEqual(codes(scan_one("control_char.json")),
                         ["CONTROL_CHAR_IN_STRING"])

    def test_decomposed_unicode_is_low_not_high(self):
        findings = scan_one("decomposed.json")
        self.assertEqual(codes(findings), ["UNNORMALIZED_UNICODE"])
        self.assertEqual(findings[0]["severity"], js.LOW)

    def test_bom_and_missing_trailing_newline(self):
        self.assertIn("BOM_PRESENT", codes(scan_one("bom.json")))
        self.assertEqual(codes(scan_one("no_newline.json")), ["NO_TRAILING_NEWLINE"])

    def test_empty_file_is_reported_never_treated_as_produced(self):
        findings = scan_one("empty.json")
        self.assertEqual(codes(findings), ["EMPTY_FILE"])
        self.assertEqual(findings[0]["severity"], js.MEDIUM)

    def test_a_clean_file_produces_nothing(self):
        self.assertEqual(scan_one("clean.json"), [])


class AuditorDiscipline(unittest.TestCase):
    def test_it_survives_the_lone_surrogate_it_detects(self):
        """Regression. The first run crashed writing its own findings: the sample
        captured for a LONE_SURROGATE finding was itself a lone surrogate and
        could not be encoded as UTF-8. A detector that dies on a detection is not
        a detector."""
        findings = scan_one("surrogate.json")
        self.assertEqual(codes(findings), ["LONE_SURROGATE"])
        with tempfile.TemporaryDirectory() as out:
            js.run(FIXTURES, out, include_self_fixtures=True)
            with open(os.path.join(out, "json_findings.json"), encoding="utf-8") as fh:
                payload = json.load(fh)
        self.assertTrue(payload["findings"])

    def test_its_own_output_is_strict_json(self):
        with tempfile.TemporaryDirectory() as out:
            js.run(FIXTURES, out, include_self_fixtures=True)
            produced = js.scan_json(os.path.join(out, "json_findings.json"),
                                    "self", "json_findings.json")
        self.assertEqual([f for f in produced if f["severity"] == js.HIGH], [])

    def test_the_word_NaN_in_prose_is_not_a_non_strict_literal(self):
        """Regression. A regex over the raw bytes flagged the WORD "NaN" wherever
        it appeared -- including inside this auditor's own explanatory prose, so
        it reported itself. Detection is the parser's job."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "prose.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write('{"note": "bare NaN and Infinity are not JSON"}\n')
            findings = js.scan_json(path, "tmp", "prose.json")
        self.assertEqual(findings, [])

    def test_lane_prefix_scopes_the_audit(self):
        """The repository holds many unrelated projects; auditing them and handing
        the result to a delivery-kit owner would be wrong twice over."""
        with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as out:
            shutil.copytree(FIXTURES, os.path.join(workspace, "uiowa_rfq_18649_a"))
            shutil.copytree(FIXTURES, os.path.join(workspace, "unrelated_project"))
            _, files = js.run(workspace, out, lane_prefix="uiowa_rfq_18649_",
                              include_self_fixtures=True)
        self.assertTrue(files)
        self.assertEqual({f.split(os.sep)[0] for f in files}, {"uiowa_rfq_18649_a"})

    def test_it_modifies_nothing_outside_its_output_directory(self):
        with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as out:
            copied = os.path.join(workspace, "lane")
            shutil.copytree(FIXTURES, copied)
            before = {p: os.stat(os.path.join(copied, p)) for p in os.listdir(copied)}
            js.run(workspace, out, include_self_fixtures=True)
            for name, stat in before.items():
                after = os.stat(os.path.join(copied, name))
                self.assertEqual(stat.st_mtime_ns, after.st_mtime_ns, name)

    def test_report_states_clean_is_not_a_certification(self):
        with tempfile.TemporaryDirectory() as out:
            js.run(FIXTURES, out, include_self_fixtures=True)
            with open(os.path.join(out, "json_safety_report.md"), encoding="utf-8") as fh:
                text = fh.read()
        self.assertIn('never "certified"', text)
        self.assertIn("never counted as a pass", text)

    def test_fail_on_gate(self):
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(js.main(["scan", "--root", FIXTURES, "--out", out,
                                      "--include-self-fixtures", "--fail-on", js.HIGH]), 1)
        with tempfile.TemporaryDirectory() as out:
            clean = os.path.join(out, "clean")
            os.makedirs(clean)
            shutil.copy(os.path.join(FIXTURES, "clean.json"), clean)
            self.assertEqual(js.main(["scan", "--root", clean,
                                      "--out", os.path.join(out, "o"),
                                      "--include-self-fixtures", "--fail-on", js.INFO]), 0)

    def test_safe_text_never_raises(self):
        self.assertIn("\\ud800", js.safe_text("\ud800"))
        self.assertIsNone(js.safe_text(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
