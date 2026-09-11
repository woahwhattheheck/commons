import json
from pathlib import Path
import tempfile
import unittest

from host.gate_objective import ObjectiveError, load_objective, parse_objective_bytes, reduce_pairs


ROOT = Path(__file__).resolve().parent
OBJECTIVE = ROOT / "ground" / "TITAN_GATE_OBJECTIVE.v1.json"


class GateObjectiveTests(unittest.TestCase):
    def test_repository_objective_and_reduction(self):
        obj = load_objective(OBJECTIVE)
        receipt = reduce_pairs(
            obj,
            [
                {"seed": 1, "candidate_score": 110, "control_score": 100},
                {"seed": 2, "candidate_score": 96, "control_score": 100},
                {"seed": 3, "candidate_score": 100, "control_score": 100},
            ],
        )
        self.assertEqual(receipt["sample_size"], 3)
        self.assertEqual(receipt["sum_delta"], 6.0)
        self.assertEqual(receipt["mean_delta"], 2.0)
        self.assertEqual((receipt["better"], receipt["equal"], receipt["worse"]), (1, 1, 1))
        self.assertEqual(len(receipt["objective_sha256"]), 64)

    def test_bool_is_not_a_numeric_score(self):
        obj = load_objective(OBJECTIVE)
        with self.assertRaisesRegex(ObjectiveError, "bool"):
            reduce_pairs(obj, [{"candidate_score": True, "control_score": 0}])

    def test_non_finite_scores_fail_closed(self):
        obj = load_objective(OBJECTIVE)
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaisesRegex(ObjectiveError, "finite"):
                reduce_pairs(obj, [{"candidate_score": value, "control_score": 0}])

    def test_missing_pair_field_fails_closed(self):
        obj = load_objective(OBJECTIVE)
        with self.assertRaisesRegex(ObjectiveError, "missing 'control_score'"):
            reduce_pairs(obj, [{"candidate_score": 1}])

    def test_empty_panel_fails_closed(self):
        obj = load_objective(OBJECTIVE)
        with self.assertRaisesRegex(ObjectiveError, "at least one"):
            reduce_pairs(obj, [])

    def test_duplicate_objective_key_is_rejected(self):
        raw = OBJECTIVE.read_text(encoding="utf-8")
        poisoned = raw.replace(
            '"objective_id": "titan-paired-evaluator-score-delta-v1",',
            '"objective_id": "one",\n  "objective_id": "two",',
        ).encode()
        with self.assertRaisesRegex(ObjectiveError, "duplicate JSON key"):
            parse_objective_bytes(poisoned)

    def test_unknown_schema_and_extra_fields_are_rejected(self):
        data = json.loads(OBJECTIVE.read_text(encoding="utf-8"))
        data["schema"] = "commons-gate-objective/v2"
        with self.assertRaisesRegex(ObjectiveError, "unsupported objective schema"):
            parse_objective_bytes(json.dumps(data).encode())

        data["schema"] = "commons-gate-objective/v1"
        data["surprise"] = 1
        with self.assertRaisesRegex(ObjectiveError, "keys mismatch"):
            parse_objective_bytes(json.dumps(data).encode())

    def test_objective_digest_changes_with_definition_bytes(self):
        obj = load_objective(OBJECTIVE)
        raw = OBJECTIVE.read_bytes()
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(raw + b"\n")
            path = Path(handle.name)
        try:
            changed = load_objective(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertNotEqual(obj.sha256, changed.sha256)


if __name__ == "__main__":
    unittest.main()
