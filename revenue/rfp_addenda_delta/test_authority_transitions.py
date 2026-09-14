from __future__ import annotations

import unittest

try:
    from .engine import compile_delta
    from .test_helpers import decision_for, generation
except ImportError:
    from engine import compile_delta
    from test_helpers import decision_for, generation


class SourceAuthorityTransitionTests(unittest.TestCase):
    NOW = "2026-09-13T18:00:00Z"

    def report(self, old, new, decisions=None):
        return compile_delta(old, new, decisions or [], trusted_as_of=self.NOW)

    def test_incomplete_old_generation_cannot_carry_review_into_complete_new_generation(self):
        old = generation(complete=False)
        new = generation("g2", "2026-09-13T13:00:00Z", complete=True)
        out = self.report(old, new, [decision_for(old)])
        self.assertEqual(out["state"], "REVIEW_REQUIRED")
        self.assertEqual(out["source_set_delta"], {"old_complete": False, "new_complete": True})
        self.assertEqual(out["carried_review_decisions"], [])
        self.assertEqual(out["review_required"], ["R-001"])

    def test_stale_prior_review_cannot_carry_into_fresh_generation(self):
        old = generation(captured="2026-09-01T12:00:00Z")
        new = generation("g2", "2026-09-13T17:00:00Z")
        decision = decision_for(old)
        decision["decided_at"] = "2026-09-01T12:30:00Z"
        out = self.report(old, new, [decision])
        self.assertEqual(out["state"], "REVIEW_REQUIRED")
        self.assertEqual(out["carried_review_decisions"], [])
        self.assertEqual(
            out["stale_review_decisions"],
            [{"requirement_id": "R-001", "decision_id": "d-R-001"}],
        )
        self.assertEqual(out["review_required"], ["R-001"])


if __name__ == "__main__":
    unittest.main()
