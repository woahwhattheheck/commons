"""Regression coverage for empty pursuit input, using only fictional records.

This validates that a supplied pursuit cannot disappear from the crosswalk.
It does not establish completeness of the caller-selected requirement set.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import compiler

FIXTURE = json.loads((ROOT / "fixtures/pursuits.synthetic.json").read_text(encoding="utf-8"))
ERROR = "requirements: at least one retained requirement is required"


def empty_pursuit():
    packet = deepcopy(FIXTURE)
    packet["pursuits"][0]["requirements"] = []
    packet["pursuits"][0]["evidence"] = []
    return packet


class EmptyRequirementTests(unittest.TestCase):
    def test_known_empty_requirements_rejected_without_input_mutation(self):
        packet = empty_pursuit()
        before = deepcopy(packet)
        with self.assertRaisesRegex(compiler.InputError, ERROR):
            compiler.compile_payload(packet)
        self.assertEqual(packet, before)

    def test_unknown_empty_requirements_rejected(self):
        packet = empty_pursuit()
        packet["pursuits"][0]["pursuit_id"] = "SYN-UNKNOWN"
        with self.assertRaisesRegex(compiler.InputError, ERROR):
            compiler.compile_payload(packet)

    def test_mixed_empty_pursuit_cannot_disappear_in_either_order(self):
        empty = empty_pursuit()["pursuits"][0]
        empty["pursuit_id"] = "SYN-UNKNOWN"
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                packet = deepcopy(FIXTURE)
                packet["pursuits"].append(deepcopy(empty))
                if reverse:
                    packet["pursuits"].reverse()
                with self.assertRaisesRegex(compiler.InputError, ERROR):
                    compiler.compile_payload(packet)

    def test_live_empty_input_is_invalid_not_a_completed_blocked_report(self):
        packet = empty_pursuit()
        packet["materialization_mode"] = "LIVE"
        with self.assertRaisesRegex(compiler.InputError, ERROR):
            compiler.compile_payload(packet)

    def test_nonempty_unknown_pursuit_still_reports_owner_input(self):
        packet = deepcopy(FIXTURE)
        packet["pursuits"][0]["pursuit_id"] = "SYN-UNKNOWN"
        result = compiler.compile_payload(packet)["payload"]
        self.assertEqual(len(result["crosswalk"]), 3)
        self.assertEqual(result["status"], "HOLD_OWNER_INPUT")
        self.assertTrue(all(row["state"] == "OWNER_INPUT" for row in result["crosswalk"]))
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_nonempty_uncovered_requirements_remain_valid(self):
        packet = deepcopy(FIXTURE)
        packet["pursuits"][0]["evidence"] = []
        result = compiler.compile_payload(packet)["payload"]
        self.assertEqual(len(result["crosswalk"]), 3)
        self.assertTrue(all(row["state"] == "PARTNER_REQUIRED" for row in result["crosswalk"]))
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_cli_rejects_before_creating_outputs_normal_and_optimized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "empty.json"
            source.write_text(json.dumps(empty_pursuit()), encoding="utf-8")
            original = source.read_bytes()
            for optimized in (False, True):
                with self.subTest(optimized=optimized):
                    output = root / ("optimized" if optimized else "normal")
                    args = [sys.executable] + (["-O"] if optimized else [])
                    args += [str(ROOT / "compiler.py"), "compile", "--input", str(source), "--out-dir", str(output)]
                    process = subprocess.run(args, capture_output=True, text=True, timeout=20)
                    self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
                    self.assertIn(ERROR, process.stderr)
                    self.assertNotIn("COMPILE_OK", process.stdout)
                    self.assertFalse(output.exists())
                    self.assertEqual(source.read_bytes(), original)

    def test_original_four_artifacts_keep_their_retained_hashes(self):
        expected = {
            "canonical_input.json": "f84a521f40ce456a8fde6aac6bcd0e8e7d96bbd3cd836feeda0ed6085e4766eb",
            "crosswalk.json": "f176f308ca12af9fbb7fe4e8a501a8bdd74f26375639b7e084ecdfc12d03fab5",
            "receipt.json": "c152d910d981186e5b5beb4298d7addfcd646bd2557c4b4a721c4ede22ecb87b",
            "shortlist.md": "cee8edb92ae68f4c3212a769b1ec7d14198c83b0cce3103212316c39dc92104c",
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out"
            compiler.compile_to_dir(ROOT / "fixtures/pursuits.synthetic.json", output)
            self.assertEqual(set(p.name for p in output.iterdir()), set(expected))
            for name, digest in expected.items():
                self.assertEqual(hashlib.sha256((output/name).read_bytes()).hexdigest(), digest, name)


if __name__ == "__main__":
    unittest.main()
