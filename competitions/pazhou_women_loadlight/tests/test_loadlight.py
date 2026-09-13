from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from loadlight.dashboard import render
from loadlight.engine import IntakeError, analyze
from loadlight.model import DOMAIN_MODEL, STAGE_MODEL, tokenize

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "fixtures" / "demo.json").read_text(encoding="utf-8"))


class ModelTests(unittest.TestCase):
    def test_tokenize_is_deterministic(self):
        self.assertEqual(tokenize("Plan PICK-UP, Friday!"), ["plan", "pick-up", "friday"])

    def test_stage_model_learns_clear_plan_language(self):
        pred = STAGE_MODEL.predict("compare childcare options and make a plan")
        self.assertEqual(pred.label, "plan")
        self.assertGreater(pred.confidence, 0.2)

    def test_stage_model_learns_monitor_language(self):
        self.assertEqual(STAGE_MODEL.predict("follow up and check the deadline reminder").label, "monitor")

    def test_domain_model_learns_food_language(self):
        self.assertEqual(DOMAIN_MODEL.predict("groceries pantry meal dinner").label, "food")


class EngineTests(unittest.TestCase):
    def test_demo_is_deterministic(self):
        self.assertEqual(analyze(fixture()), analyze(fixture()))

    def test_raw_text_is_not_emitted(self):
        report = analyze(fixture())
        dumped = json.dumps(report)
        self.assertNotIn("Remember the field trip", dumped)
        self.assertFalse(report["privacy"]["raw_text_emitted"])
        self.assertTrue(all("source_text_sha256" in item for item in report["classified_items"]))

    def test_no_health_or_safety_inference(self):
        privacy = analyze(fixture())["privacy"]
        self.assertFalse(privacy["medical_or_mental_health_inference"])
        self.assertFalse(privacy["safety_decisioning"])

    def test_not_a_moral_fairness_score(self):
        self.assertFalse(analyze(fixture())["interpretation"]["is_moral_fairness_score"])

    def test_handoff_candidate_for_concentrated_cognitive_stages(self):
        report = analyze(fixture())
        tasks = {item["task"] for item in report["handoff_candidates"]}
        self.assertIn("school field trip", tasks)
        self.assertIn("washing machine repair", tasks)

    def test_execution_alone_never_generates_handoff(self):
        data = fixture()
        data["items"] = [
            {"id":"x","task":"trash","text":"take out trash","actor":"Alex","effort_minutes":10,"stage":"execute","domain":"home"},
            {"id":"y","task":"trash","text":"replace bin liner","actor":"Jordan","effort_minutes":5,"stage":"execute","domain":"home"}
        ]
        self.assertEqual(analyze(data)["handoff_candidates"], [])

    def test_human_stage_override_is_preserved(self):
        report = analyze(fixture())
        first = report["classified_items"][0]
        self.assertEqual(first["stage"], "anticipate")
        self.assertEqual(first["stage_source"], "human")
        self.assertEqual(first["stage_confidence"], 1.0)

    def test_unlabeled_item_uses_local_model(self):
        report = analyze(fixture())
        row = next(item for item in report["classified_items"] if item["id"] == "12")
        self.assertEqual(row["stage_source"], "local_nb")
        self.assertEqual(row["domain_source"], "local_nb")
        self.assertIn(row["stage"], {"anticipate", "plan", "decide", "monitor", "execute"})

    def test_actor_shares_sum_to_one_when_cognitive_work_exists(self):
        report = analyze(fixture())
        total = sum(v["cognitive_share"] for v in report["actor_metrics"].values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_duplicate_ids_fail_closed(self):
        data = fixture()
        data["items"][1]["id"] = data["items"][0]["id"]
        with self.assertRaisesRegex(IntakeError, "duplicate item id"):
            analyze(data)

    def test_unknown_actor_fails_closed(self):
        data = fixture()
        data["items"][0]["actor"] = "Mallory"
        with self.assertRaisesRegex(IntakeError, "not in actors"):
            analyze(data)

    def test_bool_effort_is_rejected(self):
        data = fixture()
        data["items"][0]["effort_minutes"] = True
        with self.assertRaisesRegex(IntakeError, "must be numeric"):
            analyze(data)

    def test_nonpositive_effort_is_rejected(self):
        data = fixture()
        data["items"][0]["effort_minutes"] = 0
        with self.assertRaisesRegex(IntakeError, "must be in"):
            analyze(data)

    def test_due_time_requires_timezone(self):
        data = fixture()
        data["items"][0]["due_at"] = "2026-09-14T09:00:00"
        with self.assertRaisesRegex(IntakeError, "include timezone"):
            analyze(data)

    def test_unknown_fields_fail_closed(self):
        data = fixture()
        data["spy_on_partner"] = True
        with self.assertRaisesRegex(IntakeError, "unknown intake fields"):
            analyze(data)

    def test_item_unknown_fields_fail_closed(self):
        data = fixture()
        data["items"][0]["mood"] = "angry"
        with self.assertRaisesRegex(IntakeError, "unknown fields"):
            analyze(data)

    def test_report_hash_changes_when_assignment_changes(self):
        one = analyze(fixture())
        data = fixture()
        data["items"][0]["actor"] = "Jordan"
        two = analyze(data)
        self.assertNotEqual(one["report_sha256"], two["report_sha256"])

    def test_dashboard_contains_boundary_and_no_raw_text(self):
        page = render(analyze(fixture()))
        self.assertIn("not a verdict on fairness", page)
        self.assertNotIn("Remember the field trip", page)
        self.assertIn("LoadLight", page)

    def test_two_actor_minimum(self):
        data = fixture()
        data["actors"] = ["Alex"]
        with self.assertRaisesRegex(IntakeError, "2..8"):
            analyze(data)

    def test_duplicate_actors_rejected(self):
        data = fixture()
        data["actors"] = ["Alex", "Alex"]
        with self.assertRaisesRegex(IntakeError, "unique"):
            analyze(data)


class CLITests(unittest.TestCase):
    def test_cli_writes_report_and_dashboard(self):
        from loadlight.cli import main
        with tempfile.TemporaryDirectory() as td:
            rc = main(["--input", str(ROOT / "fixtures" / "demo.json"), "--output-dir", td])
            self.assertEqual(rc, 0)
            self.assertTrue((Path(td) / "report.json").is_file())
            self.assertTrue((Path(td) / "dashboard.html").is_file())
            report = json.loads((Path(td) / "report.json").read_text(encoding="utf-8"))
            self.assertFalse(report["privacy"]["raw_text_emitted"])


if __name__ == "__main__":
    unittest.main()
