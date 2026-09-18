from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
MODULE_PATH = ROOT / "revenue" / "mcc_1017_27_ai_workspace" / "qualification.py"
STATE_PATH = ROOT / "revenue" / "mcc_1017_27_ai_workspace" / "state.json"

spec = importlib.util.spec_from_file_location("mcc_1017_27_qualification", MODULE_PATH)
assert spec and spec.loader
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


def load_state():
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def controlling_state():
    state = load_state()
    state["buyer_authority"] = {
        "package_complete": True,
        "documents": [
            {
                "name": name,
                "sha256": f"{index + 1:064x}",
                "authority": "controlling",
                "source_kind": "buyer_or_buyer_portal",
                "source_url": f"https://buyer.example/{index}",
                "captured_at_utc": "2026-09-18T01:30:00Z",
            }
            for index, name in enumerate(q.REQUIRED_PACKAGE_FILES)
        ],
        "addenda": [],
        "q_and_a": [],
        "controlling_dates": {
            "questions_due_utc": "2026-09-25T22:00:00Z",
            "proposal_due_utc": "2026-10-05T21:00:00Z",
        },
    }
    return state


class PursuitTests(unittest.TestCase):
    NOW = dt.datetime(2026, 9, 18, 1, 30, tzinfo=dt.timezone.utc)

    def test_current_repository_state_holds_for_missing_buyer_package(self):
        compiled = q.compile_pursuit(load_state(), now_utc=self.NOW)
        self.assertEqual(compiled["decision"], "HOLD_BUYER_PACKAGE")
        self.assertFalse(compiled["buyer_package_complete"])
        self.assertEqual(compiled["missing_required_package_files"], list(q.REQUIRED_PACKAGE_FILES))
        self.assertTrue(all(value is False for value in compiled["external_authority"].values()))

    def test_secondary_discovery_cannot_be_promoted_to_controlling(self):
        state = load_state()
        state["secondary_discovery"]["sources"][0]["authority"] = "controlling"
        with self.assertRaisesRegex(q.PursuitError, "secondary discovery"):
            q.compile_pursuit(state, now_utc=self.NOW)

    def test_declared_complete_package_requires_all_three_indexed_files(self):
        state = controlling_state()
        state["buyer_authority"]["documents"].pop()
        with self.assertRaisesRegex(q.PursuitError, "missing"):
            q.compile_pursuit(state, now_utc=self.NOW)

    def test_complete_package_without_prime_evidence_stays_hold(self):
        compiled = q.compile_pursuit(controlling_state(), now_utc=self.NOW)
        self.assertEqual(compiled["decision"], "HOLD_PRIME_QUALIFICATION")
        self.assertFalse(compiled["prime_qualification"]["minimum_years_gate_satisfied"])
        self.assertFalse(compiled["prime_qualification"]["minimum_reference_gate_satisfied"])

    def test_partner_marketing_does_not_mint_prime_qualification(self):
        state = controlling_state()
        state["partner_candidates"][0]["state"] = "VERY_STRONG_PUBLIC_FIT"
        compiled = q.compile_pursuit(state, now_utc=self.NOW)
        self.assertEqual(compiled["decision"], "HOLD_PRIME_QUALIFICATION")
        self.assertFalse(compiled["partner_public_fit_is_qualification"])

    def test_verified_prime_evidence_only_reaches_owner_decision_not_external_authority(self):
        state = controlling_state()
        state["prime_qualification"] = {
            "verified_relevant_experience_years": 5,
            "verified_higher_education_references": [
                {
                    "institution": f"University {index}",
                    "verified_higher_education": True,
                    "evidence_sha256": f"{index + 11:064x}",
                }
                for index in range(3)
            ],
        }
        compiled = q.compile_pursuit(state, now_utc=self.NOW)
        self.assertEqual(compiled["decision"], "READY_FOR_OWNER_PRIME_DECISION")
        self.assertTrue(compiled["prime_qualification"]["minimum_years_gate_satisfied"])
        self.assertTrue(compiled["prime_qualification"]["minimum_reference_gate_satisfied"])
        self.assertTrue(all(value is False for value in compiled["external_authority"].values()))

    def test_any_external_authority_bit_is_rejected(self):
        for key in q.EXTERNAL_AUTHORITY_KEYS:
            state = load_state()
            state["external_authority"][key] = True
            with self.subTest(key=key), self.assertRaisesRegex(q.PursuitError, "must remain false"):
                q.compile_pursuit(state, now_utc=self.NOW)

    def test_expired_controlling_deadline_holds_even_with_prime_evidence(self):
        state = controlling_state()
        state["prime_qualification"] = {
            "verified_relevant_experience_years": 9,
            "verified_higher_education_references": [
                {
                    "institution": f"College {index}",
                    "verified_higher_education": True,
                    "evidence_sha256": f"{index + 21:064x}",
                }
                for index in range(3)
            ],
        }
        compiled = q.compile_pursuit(
            state,
            now_utc=dt.datetime(2026, 10, 5, 21, 0, tzinfo=dt.timezone.utc),
        )
        self.assertEqual(compiled["decision"], "HOLD_PROPOSAL_DEADLINE_PASSED")

    def test_receipt_is_order_independent_for_semantically_identical_state(self):
        state = load_state()
        compiled_a = q.compile_pursuit(state, now_utc=self.NOW)
        reordered = dict(reversed(list(copy.deepcopy(state).items())))
        compiled_b = q.compile_pursuit(reordered, now_utc=self.NOW)
        self.assertEqual(compiled_a["semantic_receipt_sha256"], compiled_b["semantic_receipt_sha256"])


if __name__ == "__main__":
    unittest.main()
