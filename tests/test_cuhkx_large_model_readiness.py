from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "competitions/cuhk_x_large_model_track/check_readiness.py"
STATE = ROOT / "competitions/cuhk_x_large_model_track/readiness.json"
spec = importlib.util.spec_from_file_location("cuhkx_readiness", TOOL)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class CuhkxReadinessTests(unittest.TestCase):
    def setUp(self):
        self.state = mod.load_state(STATE)

    def test_default_state_fails_every_stage_closed(self):
        for stage in mod.STAGES:
            ready, missing = mod.evaluate(self.state, stage)
            self.assertFalse(ready)
            self.assertTrue(missing)

    def test_written_permission_alone_does_not_clear_entry(self):
        self.assertTrue(self.state["organizer_authorization"]["written_permission_received"])
        ready, missing = mod.evaluate(self.state, "entry-ready")
        self.assertFalse(ready)
        self.assertIn("official_site_registered", missing)
        self.assertIn("kaggle_rules_accepted", missing)

    def test_complete_entry_receipts_clear_only_entry(self):
        state = copy.deepcopy(self.state)
        state["gates"].update(
            official_site_registered=True,
            kaggle_large_model_track_joined=True,
            kaggle_rules_accepted=True,
            cuhkx_data_use_terms_accepted=True,
        )
        state["team"].update(
            official_site_team_name="TokenJunkieLabs",
            kaggle_team_name="TokenJunkieLabs",
            team_name_match_verified=True,
        )
        state["receipts"].update(
            official_site_registration="receipt:example-registration",
            kaggle_join_and_terms="receipt:example-kaggle-terms",
        )
        self.assertTrue(mod.evaluate(state, "entry-ready")[0])
        self.assertFalse(mod.evaluate(state, "submission-complete")[0])

    def test_submission_requires_provider_receipts_and_claim_binding(self):
        state = copy.deepcopy(self.state)
        state["gates"].update(
            official_site_registered=True,
            kaggle_large_model_track_joined=True,
            kaggle_rules_accepted=True,
            cuhkx_data_use_terms_accepted=True,
            dataset_accessed_from_official_mirror=True,
            valid_submission_made=True,
        )
        state["team"].update(
            official_site_team_name="TokenJunkieLabs",
            kaggle_team_name="TokenJunkieLabs",
            team_name_match_verified=True,
        )
        state["receipts"].update(
            official_site_registration="receipt:registration",
            kaggle_join_and_terms="receipt:terms",
            dataset_access="receipt:official-mirror",
            submission="receipt:kaggle-submission",
        )
        state["authority"].update(dataset_access_claimed=True, submission_claimed=True)
        self.assertTrue(mod.evaluate(state, "submission-complete")[0])
        self.assertFalse(mod.evaluate(state, "verification-ready")[0])

    def test_top15_cannot_clear_without_deadline_recheck(self):
        state = copy.deepcopy(self.state)
        state["gates"]["top15_notified"] = True
        state["receipts"]["top15_notification"] = "receipt:top15"
        ready, missing = mod.evaluate(state, "verification-ready")
        self.assertFalse(ready)
        self.assertIn("verification_deadline_rechecked_after_top15", missing)
        self.assertIn("controlling verification deadline", missing)

    def test_prize_claim_is_invalid(self):
        state = copy.deepcopy(self.state)
        state["authority"]["prize_or_award_claimed"] = True
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(mod.InvalidState, "not permitted to claim"):
                mod.load_state(path)


if __name__ == "__main__":
    unittest.main()
