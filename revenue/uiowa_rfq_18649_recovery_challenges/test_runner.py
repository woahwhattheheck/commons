"""Offline tests of the challenge mechanism, independent of any production assessor."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from build_suite import make_suite
from runner import (SCHEMA, SuiteError, canonical, digest, evaluate, materialize,
                    resolve, run, source_manifest, strict_loads, tokens, validate_suite)


def tiny_suite(expected_kind: str = "return", expected_value=True) -> dict:
    cases = [{"id": "positive", "purpose": "Successful control", "baseline": "good", "edits": [],
              "positive_control": True,
              "expected": {"kind": "return", "checks": [{"path": "/recovered", "op": "equals", "value": True}]}}]
    if expected_kind == "reject":
        cases.append({"id": "invalid", "purpose": "Deliberate rejection", "baseline": "bad", "edits": [],
                      "positive_control": False, "expected": {"kind": "reject", "checks": []}})
    else:
        cases[0]["expected"]["checks"][0]["value"] = expected_value
    return {"schema": SCHEMA, "title": "Synthetic runner test", "classification": "synthetic",
            "baselines": {"good": {"valid": True}, "bad": {"valid": False}}, "cases": cases}


class PointerTests(unittest.TestCase):
    def test_escaped_keys(self):
        self.assertEqual(resolve({"a/b": {"~key": ["yes"]}}, "/a~1b/~0key/0"), "yes")

    def test_root(self):
        self.assertEqual(resolve([1, 2], ""), [1, 2])

    def test_invalid_escapes(self):
        for pointer in ("bad", "/~", "/~2", None, []):
            with self.subTest(pointer=pointer), self.assertRaises(SuiteError):
                tokens(pointer)

    def test_invalid_array_indices(self):
        for pointer in ("/-1", "/01", "/1", "/999999999999999", "/-"):
            with self.subTest(pointer=pointer), self.assertRaises(SuiteError):
                resolve([1], pointer)

    def test_missing_pointer(self):
        with self.assertRaises(SuiteError):
            resolve({}, "/missing")

    def test_scalar_traversal(self):
        with self.assertRaises(SuiteError):
            resolve({"scalar": 4}, "/scalar/nope")

    def test_remove_append_replace_without_mutation(self):
        suite = tiny_suite()
        suite["baselines"]["good"] = {"items": ["a", "b"], "keep": True}
        before = copy.deepcopy(suite)
        case = copy.deepcopy(suite["cases"][0])
        case["edits"] = [{"op": "remove", "path": "/items/0"},
                         {"op": "append", "path": "/items", "value": "c"},
                         {"op": "replace", "path": "/keep", "value": False}]
        self.assertEqual(materialize(suite, case), {"items": ["b", "c"], "keep": False})
        self.assertEqual(suite, before)

    def test_invalid_edit_does_not_become_candidate_rejection(self):
        suite = tiny_suite()
        suite["cases"][0]["edits"] = [{"op": "remove", "path": "/missing"}]
        with self.assertRaises(SuiteError):
            validate_suite(suite)


class SuiteAndVerdictTests(unittest.TestCase):
    def test_full_corpus(self):
        suite = make_suite()
        self.assertEqual(len(suite["cases"]), 31)
        self.assertEqual(sum(c["positive_control"] for c in suite["cases"]), 2)
        self.assertEqual(len({c["id"] for c in suite["cases"]}), 31)

    def test_empty_suite_rejected(self):
        suite = tiny_suite()
        suite["cases"] = []
        with self.assertRaises(SuiteError):
            validate_suite(suite)

    def test_no_positive_control_rejected(self):
        suite = tiny_suite()
        suite["cases"][0]["positive_control"] = False
        with self.assertRaises(SuiteError):
            validate_suite(suite)

    def test_vacuous_return_rejected(self):
        suite = tiny_suite()
        suite["cases"][0]["expected"]["checks"] = []
        with self.assertRaises(SuiteError):
            validate_suite(suite)

    def test_duplicate_case_id_rejected(self):
        suite = tiny_suite()
        suite["cases"].append(copy.deepcopy(suite["cases"][0]))
        with self.assertRaises(SuiteError):
            validate_suite(suite)

    def test_duplicate_json_members(self):
        with self.assertRaises(SuiteError):
            strict_loads('{"a":1,"a":2}')

    def test_nonfinite_json(self):
        for raw in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(raw=raw), self.assertRaises(SuiteError):
                strict_loads(raw)

    def test_canonical_key_order(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))

    def test_type_sensitive_equality(self):
        case = tiny_suite()["cases"][0]
        self.assertEqual(evaluate(case, {"kind": "return", "output": {"recovered": 1}})["status"], "FAIL")
        self.assertNotEqual(canonical(1), canonical(1.0))
        self.assertNotEqual(canonical(0), canonical(False))

    def test_non_string_object_keys_rejected(self):
        with self.assertRaises(SuiteError):
            canonical({1: "silently-stringified"})

    def test_missing_output_never_passes_not_equals(self):
        case = tiny_suite()["cases"][0]
        case["expected"]["checks"][0]["op"] = "not_equals"
        result = evaluate(case, {"kind": "return", "output": {}})
        self.assertEqual(result["status"], "FAIL")

    def test_crash_not_input_rejection(self):
        case = tiny_suite("reject")["cases"][1]
        for kind in ("crash", "timeout", "protocol_error"):
            with self.subTest(kind=kind):
                self.assertEqual(evaluate(case, {"kind": kind})["status"], "ERROR")

    def test_deliberate_rejection_passes(self):
        case = tiny_suite("reject")["cases"][1]
        self.assertEqual(evaluate(case, {"kind": "reject", "exception": "InputError"})["status"], "PASS")

    def test_unexpected_rejection_fails_positive(self):
        case = tiny_suite()["cases"][0]
        self.assertEqual(evaluate(case, {"kind": "reject"})["status"], "FAIL")


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.target = self.root / "candidate.py"

    def tearDown(self):
        self.temp.cleanup()

    def candidate(self, source):
        self.target.write_text(source, encoding="utf-8")
        return self.target

    def test_real_child_success_and_rejection(self):
        target = self.candidate('def assess(p):\n    if not p["valid"]: raise ValueError("invalid")\n    return {"recovered": True}\n')
        report = run(tiny_suite("reject"), target)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["counts"], {"PASS": 2, "FAIL": 0, "ERROR": 0})
        self.assertTrue(report["source_bytes_unchanged"])
        stored = report.pop("report_sha256")
        self.assertEqual(stored, digest(report))

    def test_real_typeerror_is_error(self):
        target = self.candidate('def assess(p):\n    if not p["valid"]: raise TypeError("bad programmer path")\n    return {"recovered": True}\n')
        report = run(tiny_suite("reject"), target)
        self.assertEqual(report["status"], "ERROR")
        self.assertEqual(report["counts"]["ERROR"], 1)

    def test_nonserializable_output_is_error_not_rejection(self):
        target = self.candidate('def assess(p):\n    return {"recovered": True} if p["valid"] else {"bad": float("nan")}\n')
        report = run(tiny_suite("reject"), target)
        self.assertEqual(report["status"], "ERROR")
        self.assertEqual(report["cases"][1]["observed_kind"], "crash")

    def test_target_prints_do_not_corrupt_protocol(self):
        target = self.candidate('print("import note")\ndef assess(p):\n    print("execution note")\n    return {"recovered": True}\n')
        report = run(tiny_suite(), target)
        self.assertEqual(report["status"], "PASS")
        self.assertIn("execution note", report["cases"][0]["worker_stderr"])

    def test_timeout_is_error(self):
        target = self.candidate('import time\ndef assess(p):\n    time.sleep(2)\n    return {"recovered": True}\n')
        report = run(tiny_suite(), target, timeout=0.1)
        self.assertEqual(report["status"], "ERROR")
        self.assertEqual(report["cases"][0]["observed_kind"], "timeout")

    def test_import_error_is_error(self):
        target = self.candidate('raise ValueError("import failure is not input rejection")\n')
        self.assertEqual(run(tiny_suite(), target)["status"], "ERROR")

    def test_source_mutation_invalidates_green(self):
        target = self.candidate('from pathlib import Path\ndef assess(p):\n    path=Path(__file__)\n    path.write_text(path.read_text()+"\\n# changed\\n")\n    return {"recovered": True}\n')
        report = run(tiny_suite(), target)
        self.assertEqual(report["counts"]["PASS"], 1)
        self.assertEqual(report["status"], "ERROR")
        self.assertFalse(report["source_bytes_unchanged"])

    def test_manifest_hashes_actual_bytes(self):
        target = self.candidate("# test\n")
        first = source_manifest([target])
        target.write_text("# changed\n", encoding="utf-8")
        self.assertNotEqual(first, source_manifest([target]))

    def test_cli_exit_codes(self):
        target = self.candidate('def assess(p): return {"recovered": True}\n')
        suite = self.root / "suite.json"
        suite.write_text(json.dumps(tiny_suite()), encoding="utf-8")
        runner = Path(__file__).with_name("runner.py")
        command = [sys.executable, str(runner), str(suite), str(target)]
        good = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(good.returncode, 0, good.stderr)
        suite.write_text(json.dumps(tiny_suite(expected_value=False)), encoding="utf-8")
        failed = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(failed.returncode, 1, failed.stderr)
        suite.write_text("{}", encoding="utf-8")
        malformed = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(malformed.returncode, 2)
        self.assertIn("SUITE_ERROR", malformed.stderr)
        self.assertNotIn("Traceback", malformed.stderr)


if __name__ == "__main__":
    unittest.main()
