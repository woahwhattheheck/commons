import unittest

import trace_polar_as9100 as polar


class ReviewerIdentityGuardTests(unittest.TestCase):
    def setUp(self):
        steps, manifest = polar.load_fixture()
        self.shadow = polar.PolarAs9100Shadow()
        self.shadow.replay(steps, manifest)

    def test_reserved_automation_tokens_are_rejected_across_delimiters(self):
        rejected = (
            "System Operator",
            "AI Reviewer",
            "bot user",
            "service account",
            "Agent Reviewer",
            "auto/reviewer",
            "worker.reviewer",
            "pipeline: reviewer",
            "scheduler_reviewer",
        )
        for name in rejected:
            with self.subTest(name=name):
                with self.assertRaises(PermissionError):
                    self.shadow.disposition_copy("W1", name)

    def test_ordinary_two_token_human_name_still_creates_copy_only_disposition(self):
        before = dict(self.shadow.evidence_packs["W1"])
        disposition = self.shadow.disposition_copy("W1", "Jordan Reviewer")
        self.assertEqual("APPROVED_FOR_HUMAN_DISPOSITION", disposition["disposition_state"])
        self.assertEqual("Jordan Reviewer", disposition["disposed_by"])
        self.assertFalse(disposition["sent"])
        self.assertEqual(before, self.shadow.evidence_packs["W1"])

    def test_reviewer_guard_change_does_not_relax_held_pack_gate(self):
        for wafer_id in ("W2", "W3"):
            with self.subTest(wafer_id=wafer_id):
                with self.assertRaises(PermissionError):
                    self.shadow.disposition_copy(wafer_id, "Jordan Reviewer")


if __name__ == "__main__":
    unittest.main()
