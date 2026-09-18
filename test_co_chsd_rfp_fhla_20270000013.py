from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest
from datetime import datetime, timezone

from opportunities.co_chsd_rfp_fhla_20270000013 import qualification as q


BUYER_SHA = "a" * 64
EVIDENCE_SHA = "b" * 64


def buyer():
    return {
        "id": "official-rfp-generation",
        "authority": "BUYER_OFFICIAL",
        "sha256": BUYER_SHA,
        "effective_at": "2026-09-09T08:00:00-06:00",
        "proposal_deadline": "2026-10-01T14:00:00-06:00",
        "solicitation_id": q.OPPORTUNITY_ID,
    }


def packet(evidence=None):
    return {
        "schema": q.PACKET_SCHEMA,
        "opportunity_id": q.OPPORTUNITY_ID,
        "buyer_sources": [buyer()],
        "qualification_evidence": evidence or [],
    }


def evidence_rows(party, gates):
    return [
        {
            "id": f"{party.lower()}-{gate}",
            "party": party,
            "gate": gate,
            "sha256": EVIDENCE_SHA,
        }
        for gate in gates
    ]


def roots(rows):
    return {row["id"]: dict(row) for row in rows}


class ChsdQualificationTests(unittest.TestCase):
    def fixed_clock(self):
        return datetime(2026, 9, 18, 0, 0, tzinfo=timezone.utc)

    def engine(self, rows=(), *, when=None):
        return q._build_engine(
            {"official-rfp-generation": buyer()},
            roots(rows),
            (lambda: when) if when is not None else self.fixed_clock,
        )

    def test_production_clock_and_caller_source_fail_closed(self):
        result = q.compile_packet(packet())
        self.assertEqual(result["state"], "HOLD_MISSING_BUYER_SOURCE")
        self.assertIsNone(result["official_buyer_source"])
        self.assertTrue(result["evaluated_at"].endswith("Z"))
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_official_source_without_owner_evidence_is_fail_closed(self):
        result = self.engine()(packet())
        self.assertEqual(result["state"], "HOLD_CERTIFICATION")
        self.assertEqual(result["commercial_posture"], "TEAMING_REQUIRED")
        self.assertIn("biztalk_certification", result["owner_prime_gaps"])

    def test_complete_source_owned_owner_evidence_reaches_owner_review_only(self):
        gates = q.PRIME_GATES + q.OWNER_REVIEW_GATES
        rows = evidence_rows("OWNER", gates)
        result = self.engine(rows)(packet(rows))
        self.assertEqual(result["state"], "PRIME_READY_FOR_OWNER_REVIEW")
        self.assertEqual(result["commercial_posture"], "PRIME_CANDIDATE")
        self.assertEqual(result["owner_prime_gaps"], [])
        self.assertEqual(result["owner_review_gaps"], [])
        self.assertFalse(result["authority"]["submit"])
        self.assertFalse(result["authority"]["sign"])
        self.assertFalse(result["authority"]["revenue"])

    def test_partner_evidence_never_implies_partnership_without_retained_agreement(self):
        partner = evidence_rows("PARTNER", q.PRIME_GATES)
        result = self.engine(partner)(packet(partner))
        self.assertEqual(result["commercial_posture"], "TEAMING_REQUIRED")
        self.assertFalse(result["trusted_teaming_agreement"])
        self.assertNotEqual(result["state"], "PRIME_READY_FOR_OWNER_REVIEW")

    def test_complete_partner_evidence_plus_agreement_is_still_teaming_review(self):
        partner = evidence_rows("PARTNER", q.PRIME_GATES + q.PARTNER_CONTROL_GATES)
        result = self.engine(partner)(packet(partner))
        self.assertEqual(result["state"], "TEAMING_REQUIRED")
        self.assertTrue(result["trusted_teaming_agreement"])
        self.assertEqual(result["partner_prime_gaps"], [])
        self.assertFalse(result["authority"]["partner_contact"])

    def test_trusted_process_time_blocks_backdating_after_deadline(self):
        rows = evidence_rows("OWNER", q.PRIME_GATES + q.OWNER_REVIEW_GATES)
        after = datetime(2026, 10, 1, 20, 0, 0, tzinfo=timezone.utc)
        result = self.engine(rows, when=after)(packet(rows))
        self.assertEqual(result["state"], "HOLD_DEADLINE")
        self.assertFalse(result["authority"]["submit"])

    def test_sha_match_cannot_relabel_trusted_buyer_deadline_or_generation(self):
        p = packet()
        p["buyer_sources"][0]["proposal_deadline"] = "2099-10-01T14:00:00-06:00"
        result = self.engine()(p)
        self.assertEqual(result["state"], "HOLD_MISSING_BUYER_SOURCE")
        self.assertIsNone(result["official_proposal_deadline"])

    def test_sha_match_cannot_relabel_evidence_party_or_gate(self):
        original = evidence_rows("PARTNER", ("biztalk_certification",))[0]
        forged = dict(original)
        forged["party"] = "OWNER"
        forged["gate"] = "price_approved"
        p = packet([forged])
        result = self.engine([original])(p)
        self.assertEqual(result["state"], "HOLD_CERTIFICATION")
        self.assertNotIn(forged["id"], result["admitted_evidence_ids"])

    def test_fake_sha_and_authority_label_do_not_enter_trusted_generation(self):
        fake = buyer()
        fake["sha256"] = "c" * 64
        p = packet()
        p["buyer_sources"] = [fake]
        result = self.engine()(p)
        self.assertEqual(result["state"], "HOLD_MISSING_BUYER_SOURCE")

    def test_discovery_authority_never_controls(self):
        discovery = buyer()
        discovery["authority"] = "DISCOVERY_MIRROR"
        p = packet()
        p["buyer_sources"] = [discovery]
        result = self.engine()(p)
        self.assertEqual(result["state"], "HOLD_MISSING_BUYER_SOURCE")

    def test_strict_json_rejects_duplicate_float_giant_int_and_depth(self):
        bad = (
            '{"x":1,"x":2}',
            '{"x":1.5}',
            '{"x":' + ("9" * 5000) + "}",
            ("[" * 80) + "0" + ("]" * 80),
        )
        for raw in bad:
            with self.subTest(prefix=raw[:20]):
                with self.assertRaises(q.QualificationError):
                    q.loads_strict(raw)

    def test_bool_is_not_evidence_gate_alias(self):
        p = packet()
        p["qualification_evidence"] = [
            {"id": "x", "party": "OWNER", "gate": True, "sha256": EVIDENCE_SHA}
        ]
        with self.assertRaises(q.QualificationError):
            self.engine()(p)

    def test_receipt_binds_full_runtime_packet_even_when_source_becomes_untrusted(self):
        one = self.engine()(packet())
        changed = packet()
        changed["buyer_sources"][0]["effective_at"] = "2026-09-10T08:00:00-06:00"
        two = self.engine()(changed)
        self.assertEqual(one["state"], "HOLD_CERTIFICATION")
        self.assertEqual(two["state"], "HOLD_MISSING_BUYER_SOURCE")
        self.assertNotEqual(one["input_digest_sha256"], two["input_digest_sha256"])
        self.assertNotEqual(one["receipt_sha256"], two["receipt_sha256"])

    def test_public_commons_backlink_authority_is_hard_false(self):
        result = self.engine()(packet())
        self.assertIs(result["authority"]["public_commons_backlink"], False)

    def test_suite_runs_under_real_python_optimized_mode(self):
        if os.environ.get("CHSD_OPT_CHILD") == "1":
            return
        env = dict(os.environ)
        env["CHSD_OPT_CHILD"] = "1"
        run = subprocess.run(
            [sys.executable, "-O", "-m", "unittest", "-v", Path(__file__).stem],
            cwd=Path(__file__).resolve().parent,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(run.returncode, 0, msg=run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
