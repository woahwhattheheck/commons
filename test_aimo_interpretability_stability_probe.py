from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
MODULE_DIR = ROOT / "revenue" / "aimo_interpretability"
sys.path.insert(0, str(MODULE_DIR))

import public_val_prior_audit as audit
import stability_probe as probe


class AnswerSignatureTests(unittest.TestCase):
    def test_nested_boxed_fraction(self) -> None:
        self.assertEqual(probe.answer_signature(r"work\n\boxed{\frac{1}{2}}"), r"\frac{1}{2}")

    def test_explicit_final_answer(self) -> None:
        self.assertEqual(probe.answer_signature("Reasoning\nFinal answer: $ 42 $."), "42")

    def test_final_line_fallback(self) -> None:
        self.assertEqual(probe.answer_signature("short reasoning\n-17"), "-17")

    def test_empty_and_long_truncated_outputs_do_not_vote(self) -> None:
        self.assertEqual(probe.answer_signature(""), "")
        self.assertEqual(probe.answer_signature("x" * 161), "")

    def test_majority_requires_two_nonempty_matches(self) -> None:
        self.assertTrue(probe.classify_from_responses([r"\boxed{7}", "Answer: 7", "8"]))
        self.assertFalse(probe.classify_from_responses(["1", "2", "3"]))
        self.assertFalse(probe.classify_from_responses(["", "", "7"]))


class OrchestrationTests(unittest.TestCase):
    def test_generator_sees_three_exact_problem_preserving_prompts(self) -> None:
        seen: list[tuple[str, str]] = []

        def generator(model_id: str, prompt: str) -> str:
            seen.append((model_id, prompt))
            return "Answer: 5"

        result = probe.predict_with_generator("new/model", ["What is 2+3?"], generator)
        self.assertEqual(result, [True])
        self.assertEqual(len(seen), 3)
        self.assertTrue(all(model_id == "new/model" for model_id, _ in seen))
        self.assertTrue(all("What is 2+3?" in prompt for _, prompt in seen))

    def test_failure_is_one_native_false_not_invalid_prediction(self) -> None:
        def generator(_model_id: str, _prompt: str) -> str:
            raise RuntimeError("synthetic inference failure")

        result = probe.predict_with_generator("new/model", ["problem"], generator)
        self.assertEqual(result, [False])
        self.assertIs(type(result[0]), bool)

    def test_does_not_require_known_public_model_id(self) -> None:
        result = probe.predict_with_generator(
            "competition/checkpoint-never-in-public-sample",
            ["p1", "p2"],
            lambda _model, _prompt: r"\boxed{11}",
        )
        self.assertEqual(result, [True, True])
        self.assertTrue(all(type(value) is bool for value in result))

    def test_bad_problem_shape_fails_closed(self) -> None:
        calls = 0

        def generator(_model_id: str, _prompt: str) -> str:
            nonlocal calls
            calls += 1
            return "1"

        result = probe.predict_with_generator("model", ["", None], generator)  # type: ignore[list-item]
        self.assertEqual(result, [False, False])
        self.assertEqual(calls, 0)


class PublicPriorAuditTests(unittest.TestCase):
    def test_public_counts_and_leakage_signal(self) -> None:
        report = audit.report()
        self.assertEqual(report["rows"], 28)
        self.assertEqual(report["robust_rows"], 9)
        self.assertEqual(report["non_robust_rows"], 19)
        self.assertEqual(report["constant_false"]["correct"], 19)
        self.assertEqual(report["model_id_prior_resubstitution"]["correct"], 26)
        self.assertEqual(report["model_id_prior_leave_one_model_out"]["correct"], 19)
        self.assertAlmostEqual(report["model_id_prior_resubstitution"]["accuracy"], 26 / 28)
        self.assertAlmostEqual(report["model_id_prior_leave_one_model_out"]["accuracy"], 19 / 28)

    def test_runtime_source_does_not_import_audit_or_public_model_ids(self) -> None:
        source = (MODULE_DIR / "stability_probe.py").read_text(encoding="utf-8")
        self.assertNotIn("public_val_prior_audit", source)
        for model_id in audit.PUBLIC_MODEL_COUNTS:
            self.assertNotIn(model_id, source)


class SolutionContractTests(unittest.TestCase):
    def test_entrypoint_returns_one_bool_per_problem(self) -> None:
        path = MODULE_DIR / "solution.py"
        spec = importlib.util.spec_from_file_location("aimo_solution", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        original = probe.predict_robustness
        try:
            probe.predict_robustness = lambda _model, problems: [False for _ in problems]
            # solution.py imported the function by value, so patch that binding too.
            module.predict_robustness = probe.predict_robustness
            result = module.are_robust("model", ["a", "b", "c"])
        finally:
            probe.predict_robustness = original
        self.assertEqual(result, [False, False, False])
        self.assertTrue(all(type(value) is bool for value in result))


if __name__ == "__main__":
    unittest.main()
