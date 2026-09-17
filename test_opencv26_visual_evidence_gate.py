from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest

_OPTIONAL_IMPORT_ERROR = None
try:
    import cv2
    import numpy as np
except ModuleNotFoundError as exc:  # global Commons battery does not install optional CV deps
    cv2 = None
    np = None
    _OPTIONAL_IMPORT_ERROR = exc

if _OPTIONAL_IMPORT_ERROR is None:
    from competitions.opencv_ai_competition_2026.visual_evidence_gate.aws_boundary import (
        deployment_claim_is_admissible,
        inactive_aws_plan,
    )
    from competitions.opencv_ai_competition_2026.visual_evidence_gate.core import (
        GateError,
        compile_synthetic_run,
        evaluate_synthetic_suite,
        generate_synthetic_scene,
        verify_trace,
    )


@unittest.skipIf(
    _OPTIONAL_IMPORT_ERROR is not None,
    "OpenCV/NumPy are optional to the global Commons battery; the pinned OpenCV 5 workflow is execution authority",
)
class VisualEvidenceGateTests(unittest.TestCase):
    def test_synthetic_generation_is_deterministic(self) -> None:
        first = generate_synthetic_scene("warning")
        second = generate_synthetic_scene("warning")
        self.assertTrue(np.array_equal(first, second))
        self.assertEqual(first.dtype, np.uint8)
        self.assertEqual(first.shape, (256, 256, 3))

    def test_clear_scene_continues_monitoring(self) -> None:
        trace = compile_synthetic_run("clear", compatibility_mode=True)
        self.assertEqual(trace["terminal"]["state"], "CONTINUE_MONITORING")
        self.assertEqual(len(trace["steps"]), 1)
        self.assertTrue(verify_trace(trace))

    def test_warning_requests_human_approval(self) -> None:
        trace = compile_synthetic_run("warning", compatibility_mode=True)
        self.assertEqual(trace["terminal"]["state"], "REQUEST_HUMAN_APPROVAL")
        self.assertTrue(trace["terminal"]["human_control_required"])
        self.assertIn("RED_WARNING_EVIDENCE", trace["terminal"]["reason_codes"])

    def test_ambiguous_visual_evidence_changes_next_tool_call(self) -> None:
        trace = compile_synthetic_run("ambiguous", compatibility_mode=True)
        self.assertEqual(len(trace["steps"]), 2)
        first = trace["steps"][0]
        second = trace["steps"][1]
        self.assertEqual(first["decision"]["state"], "RUN_TARGETED_RECHECK")
        self.assertEqual(first["decision"]["next_tool"], "opencv_targeted_roi_recheck")
        self.assertEqual(second["tool"], "opencv_targeted_roi_recheck")
        self.assertEqual(trace["terminal"]["state"], "REQUEST_HUMAN_APPROVAL")

    def test_stale_warning_fails_closed(self) -> None:
        trace = compile_synthetic_run("stale_warning", compatibility_mode=True)
        self.assertEqual(trace["terminal"]["state"], "HOLD_STALE_EVIDENCE")
        self.assertEqual(trace["steps"][0]["decision"]["reason_codes"], ["STALE_VISUAL_EVIDENCE"])

    def test_unsafe_action_class_fails_closed(self) -> None:
        trace = compile_synthetic_run("unsafe_requested_action", compatibility_mode=True)
        self.assertEqual(trace["terminal"]["state"], "HOLD_UNSAFE_ACTION_CLASS")
        self.assertFalse(trace["authority"]["production_actuation_authorized"])

    def test_trace_tamper_fails_semantic_verification(self) -> None:
        trace = compile_synthetic_run("warning", compatibility_mode=True)
        tampered = copy.deepcopy(trace)
        tampered["steps"][0]["evidence"]["measurements"]["red_fraction"] = 0.0
        self.assertFalse(verify_trace(tampered))

    def test_trace_digest_rewrite_still_fails_exact_recompile(self) -> None:
        trace = compile_synthetic_run("warning", compatibility_mode=True)
        tampered = copy.deepcopy(trace)
        tampered["terminal"]["state"] = "CONTINUE_MONITORING"
        no_digest = dict(tampered)
        no_digest.pop("receipt_sha256")
        import hashlib

        payload = (json.dumps(no_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
        tampered["receipt_sha256"] = hashlib.sha256(payload).hexdigest()
        self.assertFalse(verify_trace(tampered))

    def test_evaluation_suite_is_complete_and_deterministic(self) -> None:
        first = evaluate_synthetic_suite(compatibility_mode=True)
        second = evaluate_synthetic_suite(compatibility_mode=True)
        self.assertEqual(first, second)
        self.assertEqual(first["passed"], 5)
        self.assertEqual(first["total"], 5)
        self.assertEqual(first["success_basis_points"], 10000)
        self.assertTrue(first["all_expected_behaviors_observed"])
        self.assertFalse(first["official_score_or_rank_claimed"])

    def test_public_api_defaults_to_competition_mode(self) -> None:
        major = int(str(cv2.__version__).split(".", 1)[0])
        if major >= 5:
            trace = compile_synthetic_run("clear")
            runtime = trace["steps"][0]["evidence"]["runtime"]
            self.assertTrue(runtime["opencv5_verified"])
            self.assertFalse(runtime["compatibility_mode"])
        else:
            with self.assertRaises(GateError):
                compile_synthetic_run("clear")

    def test_compatibility_mode_requires_an_actual_boolean(self) -> None:
        for value in (1, "true", None, [], {}):
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(GateError, "compatibility_mode must be a boolean"):
                    compile_synthetic_run("clear", compatibility_mode=value)
                with self.assertRaisesRegex(GateError, "compatibility_mode must be a boolean"):
                    evaluate_synthetic_suite(compatibility_mode=value)

    def test_competition_mode_requires_opencv5(self) -> None:
        major = int(str(cv2.__version__).split(".", 1)[0])
        if major >= 5:
            trace = compile_synthetic_run("clear", compatibility_mode=False)
            self.assertTrue(trace["steps"][0]["evidence"]["runtime"]["opencv5_verified"])
        else:
            with self.assertRaises(GateError):
                compile_synthetic_run("clear", compatibility_mode=False)

    def test_malformed_scene_rejected(self) -> None:
        from competitions.opencv_ai_competition_2026.visual_evidence_gate import core

        with self.assertRaises(GateError):
            core._perceive(np.zeros((16, 16), dtype=np.uint8), compatibility_mode=True, scope="bad")

    def test_aws_boundary_cannot_be_promoted_by_caller_evidence(self) -> None:
        plan = inactive_aws_plan()
        self.assertEqual(plan["status"], "DESIGN_ONLY_NOT_DEPLOYED")
        self.assertFalse(plan["aws_deployment_verified"])
        forged = {"deployed": True, "stack_arn": "arn:aws:cloudformation:fake"}
        self.assertFalse(deployment_claim_is_admissible(plan, forged))

    def test_cli_evaluation_emits_truthful_compatibility_ceiling(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "competitions.opencv_ai_competition_2026.visual_evidence_gate",
                "evaluate",
                "--compatibility-mode",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["competition_evidence_ceiling"], "LOCAL_SYNTHETIC_SOURCE_DEVELOPMENT_ONLY")
        self.assertEqual(payload["success_basis_points"], 10000)

    def test_optimized_python_executes_full_suite_logic(self) -> None:
        code = """
from competitions.opencv_ai_competition_2026.visual_evidence_gate.core import compile_synthetic_run, evaluate_synthetic_suite, verify_trace
r = evaluate_synthetic_suite(compatibility_mode=True)
if r['passed'] != 5 or r['success_basis_points'] != 10000:
    raise SystemExit(21)
t = compile_synthetic_run('ambiguous', compatibility_mode=True)
if len(t['steps']) != 2 or t['steps'][0]['decision']['next_tool'] != 'opencv_targeted_roi_recheck':
    raise SystemExit(22)
if t['terminal']['state'] != 'REQUEST_HUMAN_APPROVAL' or not verify_trace(t):
    raise SystemExit(23)
print('OPENCV26_OPTIMIZED_OK')
"""
        proc = subprocess.run([sys.executable, "-O", "-c", code], check=True, text=True, capture_output=True)
        self.assertIn("OPENCV26_OPTIMIZED_OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
