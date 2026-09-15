from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "qualification_spec.json").read_text(encoding="utf-8"))

base_spec = importlib.util.spec_from_file_location("qualification", HERE / "qualification.py")
base = importlib.util.module_from_spec(base_spec)
assert base_spec.loader is not None
sys.modules["qualification"] = base
base_spec.loader.exec_module(base)

guard_spec = importlib.util.spec_from_file_location("alcorn_addendum_guard", HERE / "qualification_guarded.py")
guard = importlib.util.module_from_spec(guard_spec)
assert guard_spec.loader is not None
guard_spec.loader.exec_module(guard)

fixture_spec = importlib.util.spec_from_file_location("alcorn_base_fixtures", HERE / "test_qualification.py")
fixtures = importlib.util.module_from_spec(fixture_spec)
assert fixture_spec.loader is not None
fixture_spec.loader.exec_module(fixtures)


class AddendumGuardTests(unittest.TestCase):
    def test_current_evidence_records_addendum_and_stays_hold(self):
        evidence = base.load_json_strict(HERE / "current_evidence.json")
        result = guard.evaluate(SPEC, evidence)
        self.assertEqual(result["state"], "HOLD")
        self.assertIn(guard.TEAMING_ROUTE_BLOCKER, result["blockers"])
        finding = result["source_findings"][guard.ADDENDUM_ID]
        self.assertEqual(finding["sha256"], guard.ADDENDUM_SHA256)
        self.assertFalse(finding["teaming_route_affirmatively_permitted"])
        self.assertTrue(all(v is False for v in result["authority"].values()))

    def test_predecessor_false_green_team_fixture_is_killed(self):
        evidence = fixtures.team_ready()
        predecessor = base.evaluate(SPEC, evidence)
        self.assertEqual(predecessor["state"], "TEAMING_READY")
        guarded = guard.evaluate(SPEC, evidence)
        self.assertEqual(guarded["state"], "HOLD")
        self.assertIn(guard.TEAMING_ROUTE_BLOCKER, guarded["blockers"])

    def test_direct_prime_route_is_not_blocked_by_partner_structure_question(self):
        evidence = fixtures.direct_ready()
        result = guard.evaluate(SPEC, evidence)
        self.assertEqual(result["state"], "PRIME_READY")
        self.assertNotIn(guard.TEAMING_ROUTE_BLOCKER, result["blockers"])
        self.assertFalse(result["source_findings"][guard.ADDENDUM_ID]["teaming_route_affirmatively_permitted"])

    def test_addendum_digest_is_source_bound(self):
        spec = copy.deepcopy(SPEC)
        spec["buyer_addenda"][0]["sha256"] = "a" * 64
        with self.assertRaisesRegex(base.EvidenceError, "source binding mismatch for sha256"):
            guard.evaluate(spec, fixtures.team_ready())

    def test_addendum_message_id_is_source_bound(self):
        spec = copy.deepcopy(SPEC)
        spec["buyer_addenda"][0]["gmail_message_id"] = "invented-message"
        with self.assertRaisesRegex(base.EvidenceError, "source binding mismatch for gmail_message_id"):
            guard.evaluate(spec, fixtures.team_ready())

    def test_addendum_semantic_effect_cannot_be_promoted_by_editing_spec(self):
        spec = copy.deepcopy(SPEC)
        spec["buyer_addenda"][0]["normalized_effect"] = "AFFIRMATIVELY_PERMITTED"
        with self.assertRaisesRegex(base.EvidenceError, "source binding mismatch for normalized_effect"):
            guard.evaluate(spec, fixtures.team_ready())

    def test_duplicate_bound_addendum_is_rejected(self):
        spec = copy.deepcopy(SPEC)
        spec["buyer_addenda"].append(copy.deepcopy(spec["buyer_addenda"][0]))
        with self.assertRaisesRegex(base.EvidenceError, "exactly one"):
            guard.evaluate(spec, fixtures.team_ready())

    def test_explicit_no_bid_stays_no_bid_without_route_rewrite(self):
        evidence = fixtures.team_ready()
        evidence["explicit_disqualifier"] = {
            "fact": "buyer cancelled solicitation",
            "source": "buyer:addendum:cancel",
        }
        result = guard.evaluate(SPEC, evidence)
        self.assertEqual(result["state"], "NO_BID")
        self.assertNotIn(guard.TEAMING_ROUTE_BLOCKER, result["blockers"])


if __name__ == "__main__":
    unittest.main()
