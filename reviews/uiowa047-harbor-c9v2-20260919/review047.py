#!/usr/bin/env python3
"""Independent UIOWA-047 review. Executes one captured, Git-blob-bound source.

Run: python review047.py --source PATH --expected-blob GIT_BLOB
No network, checkout, production mutation, or provider-authorization claim.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import io
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

SOURCE = b""
SOURCE_PATH = Path()
ENGINE = None
ABSENT = object()
AS_OF = date(2026, 9, 19)
STATES = {"UNKNOWN", "EVIDENCED", "OBSERVED_GAP"}
PANELS = {}


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load(data):
    module = types.ModuleType("harbor047_captured")
    module.__file__ = str(SOURCE_PATH)
    exec(compile(data, str(SOURCE_PATH), "exec"), module.__dict__)
    return module


def catalog(**fields):
    row = {"dataset_id": "SYN-HARBOR", "service": "FICTIONAL", **fields}
    return {"as_of": AS_OF.isoformat(), "label": "FICTIONAL independent review", "datasets": [row]}


def states(payload, engine=None):
    report = (engine or ENGINE).evaluate_catalog(payload)
    return {c["check_id"]: c["state"] for c in report["datasets"][0]["checks"]}


def coverage_expected(required, covered):
    def valid(value):
        return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)
    if not valid(required) or not required or not valid(covered):
        return "UNKNOWN"
    # Deliberately membership-based, not a copy of the engine's set subtraction.
    return "EVIDENCED" if all(v in covered for v in required) else "OBSERVED_GAP"


class Review047(unittest.TestCase):
    def test_coverage_cross_product_and_no_mutation(self):
        values = [ABSENT, None, False, 0, 1, "", "a", {}, {"a": False}, [],
                  [""], [" "], ["a"], ["a", "b"], ["b", "a", "a"],
                  ["A"], [" a"], ["a "], ["é"], ["e\u0301"], [1],
                  [True], [["a"]], [{"a": True}], ["a", None], ["a|b\nc"]]
        count = 0
        for required, covered in itertools.product(values, repeat=2):
            fields = {}
            if required is not ABSENT:
                fields["required_boundary_cases"] = required
            if covered is not ABSENT:
                fields["covered_boundary_cases"] = covered
            payload = catalog(**fields)
            before = deepcopy(payload)
            with self.subTest(required=repr(required), covered=repr(covered)):
                actual = states(payload)["representativeness"]
                self.assertEqual(actual, coverage_expected(required, covered))
                self.assertEqual(payload, before)
            count += 1
        PANELS["coverage_cross_product"] = count

    def test_chronology_cleanup_cross_product(self):
        stamps = [None, "", "2026-09-19T00:00:00", "2026-02-30", False, 20260919,
                  "0001-01-01", "2024-02-29", "2026-09-18", "2026-09-19",
                  "2026-09-20", "9999-12-31"]
        cadences = [None, False, True, -1, 0, 1, 30, 365, "30", 1.0, [], {}]
        flags = [ABSENT, None, False, True, 0, 1, "false", "true", [], {}]
        count = 0
        for stamp, cadence, flag in itertools.product(stamps, cadences, flags):
            fields = {"last_refreshed": stamp, "refresh_cadence_days": cadence,
                      "cleanup_last_verified": stamp}
            if flag is not ABSENT:
                fields["cleanup_required"] = flag
            payload = catalog(**fields)
            valid_date = isinstance(stamp, str) and len(stamp) == 10
            try:
                parsed = date.fromisoformat(stamp) if valid_date else None
            except ValueError:
                parsed = None
            expected_refresh = "UNKNOWN"
            if parsed is not None and parsed <= AS_OF and type(cadence) is int and cadence > 0:
                expected_refresh = "EVIDENCED" if (AS_OF - parsed).days <= cadence else "OBSERVED_GAP"
            expected_cleanup = "UNKNOWN"
            if flag is False or flag is True and parsed is not None and parsed <= AS_OF:
                expected_cleanup = "EVIDENCED"
            with self.subTest(stamp=stamp, cadence=cadence, flag=repr(flag)):
                actual = states(payload)
                self.assertEqual(actual["refresh_freshness"], expected_refresh)
                self.assertEqual(actual["cleanup"], expected_cleanup)
            count += 1
        PANELS["chronology_cleanup_cross_product"] = count

    def test_cadence_boundaries_at_calendar_extremes(self):
        for stamp in (date.min, date(2024, 2, 29), AS_OF, date.max):
            for cadence in (1, 30, 365, 10**100):
                age = (AS_OF - stamp).days
                expected = "UNKNOWN" if age < 0 else "OBSERVED_GAP" if age > cadence else "EVIDENCED"
                self.assertEqual(states(catalog(last_refreshed=stamp.isoformat(),
                                                refresh_cadence_days=cadence))["refresh_freshness"], expected)

    def test_coverage_order_and_duplicates_are_not_new_evidence(self):
        outputs = []
        for required in (["a", "b"], ["b", "a", "a"]):
            for covered in (["a", "b"], ["b", "a", "b"]):
                result = ENGINE.evaluate_catalog(catalog(required_boundary_cases=required,
                                                        covered_boundary_cases=covered))
                outputs.append(result)
        self.assertTrue(all(v == outputs[0] for v in outputs))

    def test_incomplete_coverage_has_stable_sorted_diagnostics(self):
        results = [ENGINE.evaluate_catalog(catalog(required_boundary_cases=r, covered_boundary_cases=[]))
                   for r in (["z", "a", "é"], ["é", "z", "a", "z"])]
        self.assertEqual(results[0], results[1])
        check = next(c for c in results[0]["datasets"][0]["checks"] if c["check_id"] == "representativeness")
        self.assertEqual(check["detail"], "Missing boundary cases: a, z, é")
        self.assertTrue(check["follow_up"])

    def test_explicit_not_required_does_not_claim_verification(self):
        result = ENGINE.evaluate_catalog(catalog(cleanup_required=False,
                                                 cleanup_last_verified="9999-12-31"))
        check = next(c for c in result["datasets"][0]["checks"] if c["check_id"] == "cleanup")
        self.assertEqual(check["state"], "EVIDENCED")
        self.assertIn("not required", check["detail"])
        self.assertNotIn("verification recorded", check["detail"])

    def test_unknown_checks_have_actionable_followups(self):
        payload = catalog(last_refreshed="2026-09-20", cleanup_required=True,
                          cleanup_last_verified="2026-09-20", required_boundary_cases=["a"])
        for check in ENGINE.evaluate_catalog(payload)["datasets"][0]["checks"]:
            self.assertIn(check["state"], STATES)
            if check["state"] == "UNKNOWN":
                self.assertTrue(check["follow_up"].strip())

    def test_summary_is_additive_and_order_independent(self):
        row1 = catalog()["datasets"][0]
        row2 = catalog(required_boundary_cases=["a"], covered_boundary_cases=[]) ["datasets"][0]
        row3 = catalog(required_boundary_cases=["a"], covered_boundary_cases=["a"])["datasets"][0]
        expected = {key: 0 for key in STATES}
        for row in (row1, row2, row3):
            for key, value in ENGINE.evaluate_catalog({"as_of": AS_OF.isoformat(), "datasets": [row]})["summary"].items():
                expected[key] += value
        for rows in itertools.permutations([row1, row2, row3]):
            result = ENGINE.evaluate_catalog({"as_of": AS_OF.isoformat(), "datasets": list(rows)})
            self.assertEqual(result["summary"], expected)
            self.assertEqual(sum(result["summary"].values()), 21)

    def test_bad_catalog_shapes_are_explicit_errors(self):
        for payload in ([], None, 1, {}, {"as_of": "2026-09-19", "datasets": [None]},
                        {"as_of": "2026-09-19", "datasets": {}},
                        {"as_of": "2026-09-19T12:00:00", "datasets": []}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                ENGINE.evaluate_catalog(payload)

    def test_empty_catalog_is_not_an_evidenced_catalog(self):
        result = ENGINE.evaluate_catalog({"as_of": AS_OF.isoformat(), "datasets": []})
        self.assertEqual(result["dataset_count"], 0)
        self.assertEqual(result["summary"], {key: 0 for key in STATES})

    def test_cli_normal_optimized_and_api_agree(self):
        payload = catalog(required_boundary_cases=["a|b\nc", "é"], covered_boundary_cases=[],
                          last_refreshed="2026-09-20", refresh_cadence_days=30,
                          cleanup_required=True, cleanup_last_verified="2026-09-20")
        expected = ENGINE.evaluate_catalog(payload)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            script = base / "assessor.py"
            script.write_bytes(SOURCE)
            src = base / "catalog.json"
            raw = json.dumps(payload, ensure_ascii=False).encode()
            src.write_bytes(raw)
            for fmt in ("json", "markdown"):
                outputs = []
                for flags in ([], ["-O"]):
                    run = subprocess.run([sys.executable, *flags, "-B", str(script), str(src), "--format", fmt],
                                         capture_output=True, timeout=15, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr.decode(errors="replace"))
                    self.assertEqual(src.read_bytes(), raw)
                    outputs.append(run.stdout)
                self.assertEqual(outputs[0], outputs[1])
                if fmt == "json":
                    self.assertEqual(json.loads(outputs[0]), expected)
                else:
                    self.assertEqual(outputs[0].decode(), ENGINE.render_markdown(expected))
                    self.assertIn("a\\|b c", outputs[0].decode())

    def test_cli_invalid_input_does_not_truncate_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "assessor.py"
            script.write_bytes(SOURCE)
            catalog_path = root / "bad.json"
            catalog_path.write_text('{"as_of":"2026-09-19","datasets":[null]}')
            output = root / "keep.md"
            output.write_bytes(b"KEEP THIS ARTIFACT\n")
            run = subprocess.run([sys.executable, "-B", str(script), str(catalog_path), "--output", str(output)],
                                 capture_output=True, timeout=15, check=False)
            self.assertEqual(run.returncode, 2)
            self.assertIn(b"datasets[0]", run.stderr)
            self.assertEqual(output.read_bytes(), b"KEEP THIS ARTIFACT\n")

    def test_negative_controls_detect_all_three_semantic_regressions(self):
        controls = [
            (b"elif refreshed > as_of:", b"elif False:",
             catalog(last_refreshed="2026-09-20", refresh_cadence_days=30), "refresh_freshness", "UNKNOWN"),
            (b"elif cleanup_verified > as_of:", b"elif False:",
             catalog(cleanup_required=True, cleanup_last_verified="2026-09-20"), "cleanup", "UNKNOWN"),
            (b'covered = _case_set(dataset.get("covered_boundary_cases"))',
             b'covered = _case_set(dataset.get("covered_boundary_cases") or [])',
             catalog(required_boundary_cases=["a"]), "representativeness", "UNKNOWN"),
        ]
        for old, new, payload, check, expected in controls:
            with self.subTest(check=check):
                self.assertEqual(SOURCE.count(old), 1)
                self.assertEqual(states(payload)[check], expected)
                mutant = load(SOURCE.replace(old, new))
                self.assertNotEqual(states(payload, mutant)[check], expected)
        PANELS["detected_negative_controls"] = len(controls)


def main():
    global SOURCE, SOURCE_PATH, ENGINE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--expected-blob", required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    SOURCE_PATH = args.source
    SOURCE = SOURCE_PATH.read_bytes()
    actual = git_blob(SOURCE)
    if actual != args.expected_blob:
        parser.error(f"source mismatch: {actual} != {args.expected_blob}; nothing executed")
    ENGINE = load(SOURCE)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Review047))
    text = output.getvalue()
    sys.stdout.write(text)
    receipt = {"reviewer": "ZZ-HARBOR-C9V2", "operation": "uiowa047-review-harborc9v2-20260919",
               "source_git_blob": actual, "source_sha256": hashlib.sha256(SOURCE).hexdigest(),
               "source_bytes": len(SOURCE), "tests": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "skipped": len(result.skipped), "pass": result.wasSuccessful(),
               "python": sys.version, "optimize": sys.flags.optimize, "panels": PANELS, "literal_output": text,
               "execution_scope": "ephemeral cloud Python; not GitHub Actions or merge authority"}
    if args.receipt:
        with args.receipt.open("x", encoding="utf-8") as file:
            json.dump(receipt, file, indent=2, sort_keys=True)
            file.write("\n")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
