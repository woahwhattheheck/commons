from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from datetime import datetime, timezone

from opportunities.co_hcpf_hospital_portal_rfp26_233 import qualification as q


SOURCE_SHA = "a" * 64
EVIDENCE_SHA = "b" * 64


def source_set():
    return {
        "id": "hcpf-rfp26-233-generation-3",
        "authority": "BUYER_SOURCE_SET",
        "sha256": SOURCE_SHA,
        "effective_at": "2026-09-09T12:00:00-06:00",
        "solicitation_id": "RFP-UHAA-2026000233-3",
        "proposal_deadline": "2026-09-21T15:00:00-06:00",
        "inquiry_deadline": "2026-08-18T11:00:00-06:00",
        "submission_route": "HCPF_BOX",
        "pricing_generation": "RFP26-233 Appendix F Pricing Worksheet v3",
        "annual_cap_usd": 438202,
        "funded_sfys": 5,
        "five_year_cap_usd": 2191010,
    }


def evidence(party, gate, suffix=None):
    return {
        "id": suffix or f"{party.lower()}-{gate}",
        "party": party,
        "gate": gate,
        "sha256": EVIDENCE_SHA,
    }


def packet(rows=None):
    return {
        "schema": q.PACKET_SCHEMA,
        "pursuit_id": q.PURSUIT_ID,
        "buyer_source_sets": [source_set()],
        "qualification_evidence": rows or [],
    }


def roots(rows):
    return {row["id"]: dict(row) for row in rows}


class HcpfHospitalPortalQualificationTests(unittest.TestCase):
    def fixed_clock(self):
        return datetime(2026, 9, 18, 1, 0, tzinfo=timezone.utc)

    def engine(self, rows=(), *, when=None, sources=None):
        source_rows = sources or [source_set()]
        return q._build_engine(
            {row["id"]: dict(row) for row in source_rows},
            roots(rows),
            (lambda: when) if when is not None else self.fixed_clock,
        )

    def all_owner_rows(self):
        gates = q.TEAM_GATES + q.PERSONNEL_GATES + q.OWNER_CONTROL_GATES
        return [evidence("OWNER", gate) for gate in gates]

    def test_production_is_source_hold_and_all_external_authority_false(self):
        result = q.compile_packet(packet())
        self.assertEqual(result["state"], "HOLD_MISSING_BUYER_SOURCE")
        self.assertEqual(result["commercial_posture"], "RESEARCH_HOLD")
        self.assertIsNone(result["official_source_set"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_source_without_qualification_evidence_stays_qualification_hold(self):
        result = self.engine()(packet())
        self.assertEqual(result["state"], "HOLD_EXPERIENCE_REFERENCES")
        self.assertEqual(result["commercial_posture"], "QUALIFICATION_HOLD")
        self.assertIn("organizational_experience", result["team_gaps"])

    def test_all_owner_evidence_reaches_owner_review_but_cannot_submit(self):
        rows = self.all_owner_rows()
        result = self.engine(rows)(packet(rows))
        self.assertEqual(result["state"], "RESPONSE_READY_FOR_OWNER_REVIEW")
        self.assertEqual(result["commercial_posture"], "PRIME_CANDIDATE")
        self.assertEqual(result["partner_required_gates"], [])
        self.assertFalse(result["authority"]["submit"])
        self.assertFalse(result["authority"]["sign"])
        self.assertFalse(result["authority"]["box_upload"])
        self.assertFalse(result["authority"]["revenue"])

    def test_partner_can_supply_individual_and_team_evidence_but_needs_agreement(self):
        owner_rows = [
            evidence("OWNER", gate)
            for gate in (
                "colorado_vss_legal",
                "price_approved",
                "signatory_authorized",
            )
        ]
        partner_rows = [
            evidence("PARTNER", gate)
            for gate in (q.TEAM_GATES + q.PERSONNEL_GATES)
        ]
        rows = owner_rows + partner_rows
        result = self.engine(rows)(packet(rows))
        self.assertEqual(result["state"], "TEAMING_REQUIRED")
        self.assertEqual(result["commercial_posture"], "TEAMING_REQUIRED")
        self.assertIn("project_lead_qualifications", result["partner_required_gates"])
        self.assertFalse(result["trusted_teaming_agreement"])

        agreement = evidence("OWNER", "teaming_agreement")
        rows2 = rows + [agreement]
        result2 = self.engine(rows2)(packet(rows2))
        self.assertEqual(result2["state"], "RESPONSE_READY_FOR_OWNER_REVIEW")
        self.assertEqual(result2["commercial_posture"], "PRIME_TEAM_CANDIDATE")
        self.assertTrue(result2["trusted_teaming_agreement"])
        self.assertFalse(result2["authority"]["partner_contact"])

    def test_partner_cannot_self_mint_owner_control_gates(self):
        for gate in q.OWNER_CONTROL_GATES:
            with self.subTest(gate=gate):
                row = evidence("PARTNER", gate)
                with self.assertRaisesRegex(q.QualificationError, "owner-controlled"):
                    self.engine()(packet([row]))

    def test_same_sha_cannot_relabel_deadline_route_price_or_solicitation(self):
        mutations = {
            "proposal_deadline": "2099-09-21T15:00:00-06:00",
            "submission_route": "ATTACKER_ROUTE",
            "pricing_generation": "attacker-pricing",
            "annual_cap_usd": 1,
            "solicitation_id": "FORGED-RFP",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                p = packet()
                p["buyer_source_sets"][0][field] = value
                if field == "annual_cap_usd":
                    p["buyer_source_sets"][0]["five_year_cap_usd"] = 5
                result = self.engine()(p)
                self.assertEqual(result["state"], "HOLD_MISSING_BUYER_SOURCE")
                self.assertIsNone(result["official_source_set"])

    def test_equal_effective_trusted_source_generations_fail_ambiguous(self):
        second = source_set()
        second["id"] = "hcpf-rfp26-233-generation-3b"
        second["sha256"] = "c" * 64
        engine = self.engine(sources=[source_set(), second])
        p = packet()
        p["buyer_source_sets"].append(second)
        with self.assertRaisesRegex(q.QualificationError, "ambiguous current official buyer generation"):
            engine(p)

    def test_deadline_uses_trusted_process_time(self):
        rows = self.all_owner_rows()
        after = datetime(2026, 9, 21, 21, 0, 0, tzinfo=timezone.utc)
        result = self.engine(rows, when=after)(packet(rows))
        self.assertEqual(result["state"], "HOLD_DEADLINE")
        self.assertFalse(result["authority"]["submit"])

    def test_receipt_binds_full_runtime_packet(self):
        first = self.engine()(packet())
        changed = packet()
        changed["buyer_source_sets"][0]["submission_route"] = "OTHER"
        second = self.engine()(changed)
        self.assertNotEqual(first["input_digest_sha256"], second["input_digest_sha256"])
        self.assertNotEqual(first["receipt_sha256"], second["receipt_sha256"])

    def test_strict_ingress_rejects_duplicate_float_giant_int_depth_and_direct_size(self):
        raw_bad = (
            '{"x":1,"x":2}',
            '{"x":1.5}',
            '{"x":' + ("9" * 5000) + "}",
            ("[" * 80) + "0" + ("]" * 80),
        )
        for raw in raw_bad:
            with self.subTest(prefix=raw[:20]):
                with self.assertRaises(q.QualificationError):
                    q.loads_strict(raw)
        p = packet()
        p["buyer_source_sets"][0]["submission_route"] = "X" * (q.MAX_JSON_BYTES + 1)
        with self.assertRaisesRegex(q.QualificationError, "string-byte limit"):
            self.engine()(p)

    def test_bool_does_not_alias_integer_pricing(self):
        p = packet()
        p["buyer_source_sets"][0]["annual_cap_usd"] = True
        p["buyer_source_sets"][0]["five_year_cap_usd"] = 5
        with self.assertRaisesRegex(q.QualificationError, "positive safe integer"):
            self.engine()(p)

    def test_production_api_ignores_ordinary_post_import_rebind(self):
        direct_input = packet()
        raw_input = json.dumps(direct_input, separators=(",", ":"))
        originals = {
            "_PRODUCTION_ENGINE": q._PRODUCTION_ENGINE,
            "loads_strict": q.loads_strict,
            "_validate_tree": q._validate_tree,
            "canonical_bytes": q.canonical_bytes,
            "PACKET_SCHEMA": q.PACKET_SCHEMA,
            "PURSUIT_ID": q.PURSUIT_ID,
            "MAX_JSON_BYTES": q.MAX_JSON_BYTES,
            "datetime": q.datetime,
        }
        try:
            q._PRODUCTION_ENGINE = lambda payload: {
                "state": "PWNED",
                "authority": {"revenue": True},
            }
            q.loads_strict = lambda raw: {"schema": "pwned"}
            q._validate_tree = lambda value: None
            q.canonical_bytes = lambda value: b"pwned"
            q.PACKET_SCHEMA = "attacker-schema"
            q.PURSUIT_ID = "attacker-pursuit"
            q.MAX_JSON_BYTES = 1
            q.datetime = object
            for result in (
                q.compile_packet(direct_input),
                q.compile_json(raw_input),
            ):
                self.assertEqual(result["state"], "HOLD_MISSING_BUYER_SOURCE")
                self.assertEqual(result["commercial_posture"], "RESEARCH_HOLD")
                self.assertTrue(all(value is False for value in result["authority"].values()))
        finally:
            for name, value in originals.items():
                setattr(q, name, value)

    def test_public_commons_backlink_is_always_false(self):
        result = self.engine()(packet())
        self.assertIs(result["authority"]["public_commons_backlink"], False)

    def test_suite_runs_under_real_python_optimized_mode(self):
        if os.environ.get("HCPF_OPT_CHILD") == "1":
            return
        env = dict(os.environ)
        env["HCPF_OPT_CHILD"] = "1"
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
