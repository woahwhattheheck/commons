from __future__ import annotations

import copy
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
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

    def _write(self, state):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        path = Path(td.name) / "state.json"
        path.write_text(json.dumps(state), encoding="utf-8")
        return path

    def _write_text(self, text):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        path = Path(td.name) / "state.json"
        path.write_text(text, encoding="utf-8")
        return path

    def _complete_entry(self, state):
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
            official_site_registration="receipt:registration",
            kaggle_join_and_terms="receipt:terms",
        )
        return state

    def _complete_submission(self, state):
        self._complete_entry(state)
        state["gates"].update(
            dataset_accessed_from_official_mirror=True,
            valid_submission_made=True,
        )
        state["receipts"].update(
            dataset_access="receipt:official-mirror",
            submission="receipt:kaggle-submission",
        )
        state["authority"].update(
            dataset_access_claimed=True,
            submission_claimed=True,
            submission_ready=True,
        )
        return state

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
        state = self._complete_entry(copy.deepcopy(self.state))
        loaded = mod.load_state(self._write(state))
        self.assertTrue(mod.evaluate(loaded, "entry-ready")[0])
        self.assertFalse(mod.evaluate(loaded, "submission-complete")[0])

    def test_match_flag_cannot_override_mismatched_names(self):
        state = copy.deepcopy(self.state)
        state["team"].update(
            official_site_team_name="TokenJunkieLabs",
            kaggle_team_name="TokenJunkieLabs-Other",
            team_name_match_verified=True,
        )
        with self.assertRaisesRegex(mod.InvalidState, "contradicts actual team names"):
            mod.load_state(self._write(state))

    def test_schema_boolean_cannot_masquerade_as_version_one(self):
        state = copy.deepcopy(self.state)
        state["schema_version"] = True
        with self.assertRaisesRegex(mod.InvalidState, "integer 1"):
            mod.load_state(self._write(state))

    def test_submission_requires_provider_receipts_and_claim_binding(self):
        state = self._complete_submission(copy.deepcopy(self.state))
        loaded = mod.load_state(self._write(state))
        self.assertTrue(loaded["authority"]["submission_ready"])
        self.assertTrue(mod.evaluate(loaded, "submission-complete")[0])
        self.assertFalse(mod.evaluate(loaded, "verification-ready")[0])

    def test_dataset_access_before_entry_sequence_is_invalid(self):
        state = copy.deepcopy(self.state)
        state["gates"]["dataset_accessed_from_official_mirror"] = True
        with self.assertRaisesRegex(mod.InvalidState, "requires completed registration"):
            mod.load_state(self._write(state))

    def test_valid_submission_without_dataset_access_is_invalid(self):
        state = copy.deepcopy(self.state)
        state["gates"]["valid_submission_made"] = True
        with self.assertRaisesRegex(mod.InvalidState, "requires prior official-mirror"):
            mod.load_state(self._write(state))

    def test_final_selection_without_valid_submission_is_invalid(self):
        state = copy.deepcopy(self.state)
        state["gates"]["final_submission_selected"] = True
        with self.assertRaisesRegex(mod.InvalidState, "requires a valid submission"):
            mod.load_state(self._write(state))

    def test_final_selection_requires_evidenced_submission_readiness(self):
        state = self._complete_entry(copy.deepcopy(self.state))
        state["gates"].update(
            dataset_accessed_from_official_mirror=True,
            valid_submission_made=True,
            final_submission_selected=True,
        )
        with self.assertRaisesRegex(mod.InvalidState, "requires evidenced submission readiness"):
            mod.load_state(self._write(state))

    def test_caller_cannot_mint_submission_ready(self):
        state = copy.deepcopy(self.state)
        state["authority"]["submission_ready"] = True
        with self.assertRaisesRegex(mod.InvalidState, "must equal mechanically evidenced"):
            mod.load_state(self._write(state))

    def test_fully_evidenced_submission_cannot_leave_ready_false(self):
        state = self._complete_submission(copy.deepcopy(self.state))
        state["authority"]["submission_ready"] = False
        with self.assertRaisesRegex(mod.InvalidState, "must equal mechanically evidenced"):
            mod.load_state(self._write(state))

    def test_duplicate_json_keys_are_invalid(self):
        raw = STATE.read_text(encoding="utf-8")
        raw = raw.replace(
            '"submission_ready": false,',
            '"submission_ready": false,\n    "submission_ready": true,',
            1,
        )
        with self.assertRaisesRegex(mod.InvalidState, "duplicate JSON key: submission_ready"):
            mod.load_state(self._write_text(raw))

    def test_semantic_contradiction_returns_cli_exit_one(self):
        state = copy.deepcopy(self.state)
        state["authority"]["submission_ready"] = True
        out = io.StringIO()
        with redirect_stdout(out):
            rc = mod.main(["--state", str(self._write(state)), "--stage", "submission-complete"])
        self.assertEqual(rc, 1)
        self.assertEqual(json.loads(out.getvalue())["decision"], "INVALID")

    def test_top15_cannot_clear_without_deadline_recheck(self):
        state = copy.deepcopy(self.state)
        state["gates"]["top15_notified"] = True
        state["receipts"]["top15_notification"] = "receipt:top15"
        loaded = mod.load_state(self._write(state))
        ready, missing = mod.evaluate(loaded, "verification-ready")
        self.assertFalse(ready)
        self.assertIn("verification_deadline_rechecked_after_top15", missing)
        self.assertIn("controlling verification deadline", missing)

    def test_prize_claim_is_invalid(self):
        state = copy.deepcopy(self.state)
        state["authority"]["prize_or_award_claimed"] = True
        with self.assertRaisesRegex(mod.InvalidState, "not permitted to claim"):
            mod.load_state(self._write(state))


if __name__ == "__main__":
    unittest.main()
