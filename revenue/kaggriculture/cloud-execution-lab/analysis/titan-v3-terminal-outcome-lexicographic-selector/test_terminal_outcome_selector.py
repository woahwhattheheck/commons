from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import terminal_outcome_selector as selector


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def source() -> dict:
    return {
        "main_commit": "c51049d671b55d282e0fed5df37a0be7c513a838",
        "archive_sha256": "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1",
        "source_manifest_sha256": "3249398b6aa56d1b3464db8d0cce5aa35e8edee397fc4341bd710d1f74dad469",
        "engine_sha256": h("engine"),
        "evaluator_sha256": h("evaluator"),
        "scenario_model_sha256": h("scenario-model"),
        "scenario_set_sha256": h("scenario-set"),
    }


def row(scenario: str, own: int, rival: int, trace: str = "trace") -> dict:
    return {
        "scenario_id": scenario,
        "preworld_sha256": h(f"preworld:{scenario}"),
        "scenario_sha256": h(f"scenario:{scenario}"),
        "terminal_trace_sha256": h(f"{trace}:{scenario}:{own}:{rival}"),
        "own_cash": own,
        "rival_cash": rival,
        "terminal_complete": True,
        "score_equals_terminal_bank": True,
    }


def plan(plan_id: str, values: dict[str, tuple[int, int]], commitment: str | None = None) -> dict:
    return {
        "plan_id": plan_id,
        "commitment_sha256": commitment or h(f"commitment:{plan_id}"),
        "rows": [row(scenario, own, rival, plan_id) for scenario, (own, rival) in values.items()],
    }


def document(
    *plans: dict,
    scenarios: tuple[str, ...] = ("s0", "s1"),
    incumbent: str = "inc",
    minimum_own_cash: int = -selector.MAX_ABS_CASH,
    maximum_sacrifice: int = selector.MAX_ABS_CASH,
) -> dict:
    return {
        "schema": selector.INPUT_SCHEMA,
        "source": source(),
        "tail_policy": {
            "minimum_own_cash": minimum_own_cash,
            "maximum_outcome_improvement_sacrifice": maximum_sacrifice,
        },
        "required_scenarios": list(scenarios),
        "incumbent_plan_id": incumbent,
        "plans": list(plans),
    }


class SelectorTests(unittest.TestCase):
    def choose(self, doc: dict) -> dict:
        report = selector.select_document(doc)
        self.assertTrue(selector.verify_report_seal(report))
        return report

    def test_cash_collapse_is_allowed_only_when_loss_becomes_win(self) -> None:
        inc = plan("inc", {"s0": (0, 1), "s1": (100, 90)})
        cand = plan("cand", {"s0": (-46150, -53678), "s1": (100, 90)})
        report = self.choose(document(inc, cand, minimum_own_cash=-50000, maximum_sacrifice=50000))
        self.assertEqual(report["selected_plan_id"], "cand")
        self.assertEqual(report["status"], "SELECT_CANDIDATE")
        item = next(p for p in report["plans"] if p["plan_id"] == "cand")
        self.assertEqual(item["transitions"]["L->W"], 1)


    def test_outcome_improvement_below_cash_floor_is_rejected(self) -> None:
        inc = plan("inc", {"s0": (0, 1), "s1": (100, 90)})
        cand = plan("cand", {"s0": (-46150, -53678), "s1": (100, 90)})
        report = self.choose(document(inc, cand, minimum_own_cash=-1000, maximum_sacrifice=50000))
        item = next(p for p in report["plans"] if p["plan_id"] == "cand")
        self.assertIn("OWN_CASH_FLOOR_VIOLATION", item["reasons"])
        self.assertEqual(report["selected_plan_id"], "inc")

    def test_outcome_improvement_over_sacrifice_cap_is_rejected(self) -> None:
        inc = plan("inc", {"s0": (0, 1), "s1": (100, 90)})
        cand = plan("cand", {"s0": (-101, -200), "s1": (100, 90)})
        report = self.choose(document(inc, cand, minimum_own_cash=-1000, maximum_sacrifice=100))
        item = next(p for p in report["plans"] if p["plan_id"] == "cand")
        self.assertIn("OUTCOME_IMPROVEMENT_SACRIFICE_CAP_VIOLATION", item["reasons"])
        self.assertEqual(report["selected_plan_id"], "inc")

    def test_outcome_improvement_at_floor_and_cap_boundary_is_allowed(self) -> None:
        inc = plan("inc", {"s0": (0, 1), "s1": (100, 90)})
        cand = plan("cand", {"s0": (-100, -200), "s1": (100, 90)})
        report = self.choose(document(inc, cand, minimum_own_cash=-100, maximum_sacrifice=100))
        self.assertEqual(report["selected_plan_id"], "cand")

    def test_invalid_tail_policy_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        negative = document(inc)
        negative["tail_policy"]["maximum_outcome_improvement_sacrifice"] = -1
        with self.assertRaises(selector.ContractError):
            selector.select_document(negative)
        boolean = document(inc)
        boolean["tail_policy"]["minimum_own_cash"] = True
        with self.assertRaises(selector.ContractError):
            selector.select_document(boolean)

    def test_own_gain_that_creates_loss_is_rejected(self) -> None:
        inc = plan("inc", {"s0": (100, 90), "s1": (5, 0)})
        cand = plan("cand", {"s0": (200, 300), "s1": (6, 0)})
        report = self.choose(document(inc, cand))
        self.assertEqual(report["selected_plan_id"], "inc")
        item = next(p for p in report["plans"] if p["plan_id"] == "cand")
        self.assertIn("OUTCOME_REGRESSION", item["reasons"])

    def test_same_outcome_own_cash_regression_is_rejected(self) -> None:
        inc = plan("inc", {"s0": (100, 50), "s1": (50, 10)})
        cand = plan("cand", {"s0": (99, 40), "s1": (51, 10)})
        report = self.choose(document(inc, cand))
        item = next(p for p in report["plans"] if p["plan_id"] == "cand")
        self.assertIn("SAME_CLASS_OWN_REGRESSION", item["reasons"])
        self.assertEqual(report["selected_plan_id"], "inc")

    def test_same_outcome_margin_regression_is_rejected(self) -> None:
        inc = plan("inc", {"s0": (100, 50), "s1": (50, 10)})
        cand = plan("cand", {"s0": (101, 60), "s1": (51, 10)})
        report = self.choose(document(inc, cand))
        item = next(p for p in report["plans"] if p["plan_id"] == "cand")
        self.assertIn("SAME_CLASS_MARGIN_REGRESSION", item["reasons"])
        self.assertEqual(report["selected_plan_id"], "inc")

    def test_same_class_pareto_improvement_can_advance(self) -> None:
        inc = plan("inc", {"s0": (100, 50), "s1": (50, 10)})
        cand = plan("cand", {"s0": (101, 50), "s1": (50, 10)})
        report = self.choose(document(inc, cand))
        self.assertEqual(report["selected_plan_id"], "cand")

    def test_one_bad_scenario_cannot_be_masked_by_many_wins(self) -> None:
        inc = plan("inc", {"s0": (10, 0), "s1": (10, 0)})
        cand = plan("cand", {"s0": (1000, 0), "s1": (100, 101)})
        report = self.choose(document(inc, cand))
        self.assertEqual(report["selected_plan_id"], "inc")

    def test_unique_lexicographic_best_is_selected(self) -> None:
        inc = plan("inc", {"s0": (0, 1), "s1": (0, 1)})
        one = plan("one", {"s0": (2, 1), "s1": (0, 0)})
        two = plan("two", {"s0": (2, 1), "s1": (2, 1)})
        report = self.choose(document(inc, one, two))
        self.assertEqual(report["selected_plan_id"], "two")

    def test_ambiguous_best_preserves_incumbent(self) -> None:
        inc = plan("inc", {"s0": (0, 1), "s1": (0, 1)})
        one = plan("one", {"s0": (2, 1), "s1": (3, 2)})
        two = plan("two", {"s0": (3, 2), "s1": (2, 1)})
        report = self.choose(document(inc, one, two))
        self.assertEqual(report["selected_plan_id"], "inc")
        self.assertEqual(report["reason"], "AMBIGUOUS_BEST_PRESERVE_INCUMBENT")

    def test_exact_effect_tie_preserves_incumbent(self) -> None:
        values = {"s0": (10, 0), "s1": (10, 0)}
        inc = plan("inc", values)
        cand = plan("cand", values)
        report = self.choose(document(inc, cand))
        self.assertEqual(report["selected_plan_id"], "inc")
        self.assertEqual(report["reason"], "NO_ELIGIBLE_IMPROVEMENT")

    def test_no_strict_improvement_is_ineligible(self) -> None:
        values = {"s0": (10, 0), "s1": (10, 0)}
        inc = plan("inc", values)
        cand = plan("cand", values)
        report = self.choose(document(inc, cand))
        item = next(p for p in report["plans"] if p["plan_id"] == "cand")
        self.assertIn("NO_STRICT_IMPROVEMENT", item["reasons"])

    def test_commitment_alias_is_reported_and_not_selected(self) -> None:
        values = {"s0": (10, 0), "s1": (10, 0)}
        commitment = h("same")
        inc = plan("inc", values, commitment)
        cand = copy.deepcopy(inc)
        cand["plan_id"] = "cand"
        report = self.choose(document(inc, cand))
        self.assertEqual(report["behavior_aliases"], [["cand", "inc"]])
        self.assertEqual(report["selected_plan_id"], "inc")

    def test_same_commitment_with_different_score_is_rejected(self) -> None:
        commitment = h("same")
        inc = plan("inc", {"s0": (10, 0), "s1": (10, 0)}, commitment)
        cand = plan("cand", {"s0": (11, 0), "s1": (10, 0)}, commitment)
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc, cand))

    def test_duplicate_plan_id_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        duplicate = plan("inc", {"s0": (2, 0), "s1": (2, 0)})
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc, duplicate))

    def test_duplicate_row_scenario_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        inc["rows"][1]["scenario_id"] = "s0"
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc))

    def test_missing_scenario_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0)})
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc))

    def test_extra_scenario_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0), "s2": (1, 0)})
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc))

    def test_boolean_cash_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        inc["rows"][0]["own_cash"] = True
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc))

    def test_float_cash_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        inc["rows"][0]["own_cash"] = 1.0
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc))

    def test_cash_overflow_bound_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        inc["rows"][0]["own_cash"] = 1 << 63
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc))

    def test_duplicate_json_key_rejected(self) -> None:
        with self.assertRaises(selector.ContractError):
            selector.strict_loads('{"schema":1,"schema":2}')

    def test_nonfinite_json_rejected(self) -> None:
        with self.assertRaises(selector.ContractError):
            selector.strict_loads('{"x":NaN}')

    def test_preworld_mismatch_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        cand = plan("cand", {"s0": (2, 0), "s1": (2, 0)})
        cand["rows"][0]["preworld_sha256"] = h("different")
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc, cand))

    def test_scenario_digest_mismatch_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        cand = plan("cand", {"s0": (2, 0), "s1": (2, 0)})
        cand["rows"][0]["scenario_sha256"] = h("different")
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc, cand))

    def test_incomplete_terminal_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        inc["rows"][0]["terminal_complete"] = False
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc))

    def test_score_bank_assertion_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        inc["rows"][0]["score_equals_terminal_bank"] = False
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc))

    def test_bad_hash_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        doc = document(inc)
        doc["source"]["engine_sha256"] = "ABC"
        with self.assertRaises(selector.ContractError):
            selector.select_document(doc)

    def test_bad_identifier_rejected(self) -> None:
        inc = plan("inc space", {"s0": (1, 0), "s1": (1, 0)})
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc, incumbent="inc space"))

    def test_wrong_schema_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        doc = document(inc)
        doc["schema"] = "wrong"
        with self.assertRaises(selector.ContractError):
            selector.select_document(doc)

    def test_missing_incumbent_rejected(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc, incumbent="absent"))

    def test_empty_scenario_set_rejected(self) -> None:
        inc = {"plan_id": "inc", "commitment_sha256": h("inc"), "rows": []}
        with self.assertRaises(selector.ContractError):
            selector.select_document(document(inc, scenarios=()))

    def test_plan_and_row_order_do_not_change_report(self) -> None:
        inc = plan("inc", {"s0": (0, 1), "s1": (0, 1)})
        cand = plan("cand", {"s0": (2, 1), "s1": (2, 1)})
        first = self.choose(document(inc, cand))
        inc2 = copy.deepcopy(inc)
        cand2 = copy.deepcopy(cand)
        inc2["rows"].reverse()
        cand2["rows"].reverse()
        second_doc = document(cand2, inc2)
        second_doc["required_scenarios"].reverse()
        second = self.choose(second_doc)
        self.assertEqual(selector.canonical_bytes(first), selector.canonical_bytes(second))

    def test_report_tamper_breaks_seal(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        report = self.choose(document(inc))
        report["selected_plan_id"] = "tampered"
        self.assertFalse(selector.verify_report_seal(report))

    def test_trace_can_differ_when_commitment_differs(self) -> None:
        inc = plan("inc", {"s0": (0, 1), "s1": (0, 1)})
        cand = plan("cand", {"s0": (2, 1), "s1": (2, 1)})
        report = self.choose(document(inc, cand))
        self.assertEqual(report["selected_plan_id"], "cand")

    def test_cli_writes_atomic_sealed_report(self) -> None:
        inc = plan("inc", {"s0": (0, 1), "s1": (0, 1)})
        cand = plan("cand", {"s0": (2, 1), "s1": (2, 1)})
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "input.json"
            output_path = root / "output.json"
            input_path.write_bytes(selector.canonical_bytes(document(inc, cand)))
            result = subprocess.run(
                [sys.executable, str(Path(selector.__file__)), str(input_path), str(output_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = selector.strict_loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(selector.verify_report_seal(report))
            self.assertFalse(any(root.glob(".*.tmp")))

    def test_cli_failure_does_not_replace_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "bad.json"
            output_path = root / "output.json"
            input_path.write_text('{"x":NaN}', encoding="utf-8")
            output_path.write_text("sentinel", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(Path(selector.__file__)), str(input_path), str(output_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "sentinel")


    def test_malformed_json_rejected_as_contract_error(self) -> None:
        with self.assertRaises(selector.ContractError):
            selector.strict_loads('{"x":')

    def test_cli_rejects_input_output_alias(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "same.json"
            original = selector.canonical_bytes(document(inc))
            path.write_bytes(original)
            result = subprocess.run(
                [sys.executable, str(Path(selector.__file__)), str(path), str(path)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(path.read_bytes(), original)

    def test_cli_rejects_hardlink_output_alias(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "input.json"
            output_path = root / "output.json"
            original = selector.canonical_bytes(document(inc))
            input_path.write_bytes(original)
            output_path.hardlink_to(input_path)
            result = subprocess.run(
                [sys.executable, str(Path(selector.__file__)), str(input_path), str(output_path)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(input_path.read_bytes(), original)

    def test_cli_rejects_symlink_input_and_output(self) -> None:
        inc = plan("inc", {"s0": (1, 0), "s1": (1, 0)})
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real_input = root / "real-input.json"
            real_output = root / "real-output.json"
            real_input.write_bytes(selector.canonical_bytes(document(inc)))
            real_output.write_text("sentinel", encoding="utf-8")
            symlink_input = root / "input-link.json"
            symlink_output = root / "output-link.json"
            symlink_input.symlink_to(real_input)
            symlink_output.symlink_to(real_output)
            first = subprocess.run(
                [sys.executable, str(Path(selector.__file__)), str(symlink_input), str(root / "new.json")],
                check=False, capture_output=True, text=True,
            )
            second = subprocess.run(
                [sys.executable, str(Path(selector.__file__)), str(real_input), str(symlink_output)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(first.returncode, 2)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(real_output.read_text(encoding="utf-8"), "sentinel")

    def test_exhaustive_small_domain_safety_property(self) -> None:
        values = range(-2, 3)
        for io in values:
            for ir in values:
                inc = plan("inc", {"s0": (io, ir)}, h(f"i:{io}:{ir}"))
                for co in values:
                    for cr in values:
                        cand = plan("cand", {"s0": (co, cr)}, h(f"c:{co}:{cr}"))
                        report = self.choose(document(inc, cand, scenarios=("s0",)))
                        item = next(p for p in report["plans"] if p["plan_id"] == "cand")
                        if item["eligible"]:
                            inc_out = (io > ir) - (io < ir)
                            cand_out = (co > cr) - (co < cr)
                            self.assertGreaterEqual(cand_out, inc_out)
                            if cand_out == inc_out:
                                self.assertGreaterEqual(co, io)
                                self.assertGreaterEqual(co - cr, io - ir)


if __name__ == "__main__":
    unittest.main()
