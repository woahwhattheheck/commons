import json
import unittest
from pathlib import Path

import incident_learning


HERE = Path(__file__).resolve().parent


class IncidentLearningTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads((HERE / "examples.json").read_text(encoding="utf-8"))

    def test_examples_distinguish_narrative_from_follow_through(self):
        result = incident_learning.assess_packet(self.packet)
        incidents = {item["incident_id"]: item for item in result["incidents"]}

        first = incidents["SYN-INC-001"]
        self.assertEqual(first["learning_evidence"], "NARRATIVE_WITH_ACTIONS_PENDING")
        states = {a["action_id"]: a["state"] for a in first["actions"]}
        self.assertEqual(states["ACT-001-A"], "OVERDUE")
        self.assertEqual(states["ACT-001-B"], "COMPLETED")
        self.assertEqual(states["ACT-001-C"], "CHANGED_APPROACH")
        self.assertIn(
            "effectiveness_followup_missing",
            next(a for a in first["actions"] if a["action_id"] == "ACT-001-B")["issues"],
        )

        second = incidents["SYN-INC-002"]
        self.assertEqual(second["learning_evidence"], "FOLLOW_THROUGH_EVIDENCED")
        self.assertEqual(second["action_summary"]["completed_with_effectiveness"], 1)

    def test_restore_time_is_derived_from_supported_timestamps(self):
        result = incident_learning.assess_packet(self.packet)
        incidents = {item["incident_id"]: item for item in result["incidents"]}
        self.assertEqual(incidents["SYN-INC-001"]["restore_minutes"], 45.0)
        self.assertEqual(incidents["SYN-INC-002"]["restore_minutes"], 18.0)

    def test_missing_due_date_is_unknown_not_overdue(self):
        now = incident_learning.parse_time("2026-09-19T13:40:00Z", "now")
        action = {
            "action_id": "SYN-A",
            "description": "Fictional action",
            "owner_role": "Service owner",
            "due_at": None
        }
        assessed = incident_learning.assess_action(action, now)
        self.assertEqual(assessed["state"], "UNKNOWN")
        self.assertIn("due_date_missing", assessed["issues"])

    def test_bad_timeline_order_is_rejected(self):
        now = incident_learning.parse_time("2026-09-19T13:40:00Z", "now")
        record = {
            "incident_id": "SYN-BAD",
            "service": "Fictional service",
            "detected_at": "2026-08-01T10:00:00Z",
            "restored_at": "2026-08-01T09:00:00Z",
            "timeline": [{"at": "2026-08-01T10:00:00Z", "event": "Synthetic event"}],
            "postmortem": {},
            "corrective_actions": []
        }
        with self.assertRaisesRegex(ValueError, "cannot precede"):
            incident_learning.assess_incident(record, now)


if __name__ == "__main__":
    unittest.main()
