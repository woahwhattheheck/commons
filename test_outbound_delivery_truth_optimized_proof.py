"""Negative controls for the retained real-optimized delivery smoke test.

These controls deliberately corrupt only the synthetic child-process result.
A healthy smoke must pass, and every false result must cause a nonzero child
exit. No provider, filesystem source, or shared repository is mutated.
"""
from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
import unittest


TEST_FILE = Path(__file__).with_name("test_outbound_delivery_truth.py")
METHOD = "test_real_python_O_legacy_hard_failure_path"
MARKER = "art=m.compile_delivery_truth(p)\n"


def retained_script() -> str:
    tree = ast.parse(TEST_FILE.read_text(encoding="utf-8"))
    classes = [node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == "DeliveryTruthTests"]
    if len(classes) != 1:
        raise ValueError("retained test class must be unique")
    methods = [node for node in classes[0].body
               if isinstance(node, ast.FunctionDef) and node.name == METHOD]
    if len(methods) != 1:
        raise ValueError("retained optimized test method must be unique")
    assignments = [node for node in methods[0].body
                   if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "script"
                           for target in node.targets)]
    if len(assignments) != 1:
        raise ValueError("retained optimized script must be an exact literal")
    script = ast.literal_eval(assignments[0].value)
    if type(script) is not str or script.count(MARKER) != 1:
        raise ValueError("retained optimized script marker changed")
    return script


def run_optimized(script: str) -> subprocess.CompletedProcess[str]:
    # The explicit runtime guard itself also survives -O.
    prefix = (
        "import sys\n"
        "if sys.flags.optimize < 1:\n"
        "    raise RuntimeError('real optimized interpreter required')\n"
    )
    return subprocess.run(
        [sys.executable, "-O", "-c", prefix + script],
        cwd=TEST_FILE.parent,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


class OptimizedProofTests(unittest.TestCase):
    def test_healthy_real_optimized_replay_passes(self):
        result = run_optimized(retained_script())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_retained_child_has_no_optimization_removed_asserts(self):
        tree = ast.parse(retained_script())
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))

    def require_mutant_rejected(self, change: str, expected_message: str):
        script = retained_script().replace(MARKER, MARKER + change + "\n", 1)
        result = run_optimized(script)
        self.assertNotEqual(result.returncode, 0, "optimized proof accepted false result")
        self.assertIn(expected_message, result.stderr)

    def test_wrong_delivery_state_is_detected(self):
        self.require_mutant_rejected(
            'art["delivery_state"] = "DELIVERED_EVIDENCE"', "changed delivery state")

    def test_true_authority_is_detected(self):
        self.require_mutant_rejected(
            'art["authority"]["cash_proven"] = True', "widened authority")

    def test_empty_authority_is_not_vacuously_false(self):
        self.require_mutant_rejected('art["authority"] = {}', "widened authority")

    def test_missing_authority_bit_is_detected(self):
        self.require_mutant_rejected(
            'art["authority"].pop("send_authorized")', "widened authority")

    def test_zero_is_not_boolean_false(self):
        self.require_mutant_rejected(
            'art["authority"]["payment_authorized"] = 0', "widened authority")

    def test_legacy_cannot_claim_provider_submission(self):
        self.require_mutant_rejected(
            'art["collision_projection"]["provider_submission_observed"] = True',
            "must not imply provider submission")

    def test_legacy_must_keep_duplicate_send_hold(self):
        self.require_mutant_rejected(
            'art["collision_projection"]["same_route_dedupe_hold"] = False',
            "must retain the duplicate-send hold")

    def test_failed_delivery_cannot_claim_contact(self):
        self.require_mutant_rejected(
            'art["collision_projection"]["counts_as_contacted"] = True',
            "must not count as successful contact")


if __name__ == "__main__":
    unittest.main()
