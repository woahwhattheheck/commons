from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.qualification_evidence_vault import engine

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "revenue/qualification_evidence_vault/example.public-evidence.json"
SOL = ROOT / "revenue/qualification_evidence_vault/example.synthetic-solicitation.json"
AS_OF = "2026-09-16T22:45:00Z"


def public_vault():
    return json.loads(EXAMPLE.read_text())


def solicitation(requirements):
    return {
        "schema": engine.SOLICITATION_SCHEMA,
        "solicitation_id": "RFP-TEST",
        "title": "Test procurement",
        "requirements": requirements,
    }


def req(category, qualifier, *, min_count=1, max_age_days=None, partner=False, disqualify=False):
    return {
        "requirement_id": f"r-{category.lower()}-{qualifier.lower().replace('_','-')}",
        "category": category,
        "qualifier": qualifier,
        "min_count": min_count,
        "max_age_days": max_age_days,
        "partner_can_cure": partner,
        "missing_disqualifies": disqualify,
    }


def record(eid, category, qualifier, status, *, source="FIRST_PARTY_PUBLIC", visibility="PUBLIC", event_at="2026-09-01T00:00:00Z", valid_until=None):
    return {
        "evidence_id": eid,
        "category": category,
        "qualifier": qualifier,
        "status": status,
        "visibility": visibility,
        "source_kind": source,
        "source_ref": "https://example.invalid/evidence" if visibility == "PUBLIC" else "private://owner/evidence",
        "description": "Evidence description",
        "event_at": event_at,
        "valid_until": valid_until,
    }


class QualificationVaultTests(unittest.TestCase):
    def test_public_merge_receipts_satisfy_only_exact_delivery_category(self):
        packet = engine.compile_assessment(
            public_vault(),
            solicitation([req("DELIVERY_RECEIPT", "OSS_EXTERNAL_MERGE", min_count=2)]),
            AS_OF,
        )
        self.assertEqual(packet["outcome"], "PRIME_SUPPORTED")
        self.assertFalse(any(packet["authority_flags"].values()))

    def test_oss_merge_cannot_alias_to_past_performance(self):
        packet = engine.compile_assessment(
            public_vault(), solicitation([req("PAST_PERFORMANCE", "SOFTWARE")]), AS_OF
        )
        self.assertEqual(packet["outcome"], "HOLD_MISSING_EVIDENCE")
        self.assertEqual(packet["requirements"][0]["verified_evidence_ids"], [])

    def test_relabelled_github_merge_cannot_mint_past_performance(self):
        vault = {
            "schema": engine.VAULT_SCHEMA,
            "records": [
                record(
                    "fake-past-performance",
                    "PAST_PERFORMANCE",
                    "ERP",
                    "VERIFIED",
                    source="GITHUB_MERGED_PR",
                )
            ],
        }
        vault["records"][0]["source_ref"] = "https://github.com/example/example/pull/1"
        with self.assertRaises(engine.EvidenceError):
            engine.compile_assessment(vault, solicitation([req("PAST_PERFORMANCE", "ERP")]), AS_OF)

    def test_github_source_kind_requires_github_url(self):
        vault = {
            "schema": engine.VAULT_SCHEMA,
            "records": [
                record(
                    "bad-merge-url",
                    "DELIVERY_RECEIPT",
                    "OSS_EXTERNAL_MERGE",
                    "VERIFIED",
                    source="GITHUB_MERGED_PR",
                )
            ],
        }
        with self.assertRaises(engine.EvidenceError):
            engine.normalize_vault(vault, AS_OF)

    def test_payment_receipt_cannot_alias_to_delivery(self):
        vault = {"schema": engine.VAULT_SCHEMA, "records": [record("paid-1", "PAYMENT_RECEIPT", "BOUNTY", "VERIFIED", source="PROVIDER_RECEIPT")]}
        packet = engine.compile_assessment(vault, solicitation([req("DELIVERY_RECEIPT", "BOUNTY")]), AS_OF)
        self.assertEqual(packet["outcome"], "HOLD_MISSING_EVIDENCE")

    def test_owner_assertion_cannot_mint_verified_certification(self):
        vault = {"schema": engine.VAULT_SCHEMA, "records": [record("cert-1", "CERTIFICATION", "SOC2", "VERIFIED", source="OWNER_ASSERTION")]}
        with self.assertRaises(engine.EvidenceError):
            engine.compile_assessment(vault, solicitation([req("CERTIFICATION", "SOC2")]), AS_OF)

    def test_synthetic_fixture_cannot_mint_verified_support(self):
        vault = {"schema": engine.VAULT_SCHEMA, "records": [record("synthetic", "TECHNICAL_CAPABILITY", "ORACLE_EBS", "VERIFIED", source="SYNTHETIC_FIXTURE")]}
        with self.assertRaises(engine.EvidenceError):
            engine.compile_assessment(vault, solicitation([req("TECHNICAL_CAPABILITY", "ORACLE_EBS")]), AS_OF)

    def test_explicit_missing_partner_curable_is_partner_only(self):
        vault = {"schema": engine.VAULT_SCHEMA, "records": [record("ins-missing", "INSURANCE", "CGL", "MISSING")]}
        packet = engine.compile_assessment(vault, solicitation([req("INSURANCE", "CGL", partner=True)]), AS_OF)
        self.assertEqual(packet["outcome"], "PARTNER_ONLY")
        self.assertEqual(packet["requirements"][0]["result"], "PARTNER_GAP")

    def test_unknown_does_not_become_partner_gap(self):
        vault = {"schema": engine.VAULT_SCHEMA, "records": [record("ins-unknown", "INSURANCE", "CGL", "UNKNOWN")]}
        packet = engine.compile_assessment(vault, solicitation([req("INSURANCE", "CGL", partner=True)]), AS_OF)
        self.assertEqual(packet["outcome"], "HOLD_MISSING_EVIDENCE")

    def test_absence_does_not_become_partner_gap(self):
        vault = {"schema": engine.VAULT_SCHEMA, "records": []}
        packet = engine.compile_assessment(vault, solicitation([req("INSURANCE", "CGL", partner=True)]), AS_OF)
        self.assertEqual(packet["outcome"], "HOLD_MISSING_EVIDENCE")

    def test_explicit_noncurable_missing_can_disqualify(self):
        vault = {"schema": engine.VAULT_SCHEMA, "records": [record("entity-missing", "LEGAL_ENTITY", "DOMESTIC_ENTITY", "MISSING")]}
        packet = engine.compile_assessment(vault, solicitation([req("LEGAL_ENTITY", "DOMESTIC_ENTITY", disqualify=True)]), AS_OF)
        self.assertEqual(packet["outcome"], "DISQUALIFIED")

    def test_valid_until_expires_verified_record(self):
        vault = {"schema": engine.VAULT_SCHEMA, "records": [record("ins-old", "INSURANCE", "CGL", "VERIFIED", valid_until="2026-09-10T00:00:00Z")]}
        packet = engine.compile_assessment(vault, solicitation([req("INSURANCE", "CGL", partner=True)]), AS_OF)
        self.assertEqual(packet["outcome"], "PARTNER_ONLY")

    def test_requirement_freshness_marks_old_verified_owner_hold(self):
        vault = {"schema": engine.VAULT_SCHEMA, "records": [record("ref-old", "PAST_PERFORMANCE", "ERP", "VERIFIED", event_at="2025-01-01T00:00:00Z")]}
        packet = engine.compile_assessment(vault, solicitation([req("PAST_PERFORMANCE", "ERP", max_age_days=365, partner=True)]), AS_OF)
        self.assertEqual(packet["outcome"], "HOLD_MISSING_EVIDENCE")

    def test_private_redaction_strips_source_and_description(self):
        vault = {"schema": engine.VAULT_SCHEMA, "records": [record("private-1", "INSURANCE", "CGL", "OWNER_ONLY", source="OWNER_PRIVATE_DOCUMENT", visibility="PRIVATE")]}
        redacted = engine.redact_vault(vault, AS_OF)
        row = redacted["records"][0]
        self.assertEqual(row["source_kind"], "PRIVATE_REDACTED")
        self.assertIsNone(row["source_ref"])
        self.assertIsNone(row["description"])

    def test_private_document_cannot_be_public(self):
        vault = {"schema": engine.VAULT_SCHEMA, "records": [record("private-1", "INSURANCE", "CGL", "OWNER_ONLY", source="OWNER_PRIVATE_DOCUMENT", visibility="PUBLIC")]}
        with self.assertRaises(engine.EvidenceError):
            engine.normalize_vault(vault, AS_OF)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(engine.EvidenceError):
            engine.strict_loads('{"schema":"x","schema":"y"}')

    def test_bool_is_not_min_count_integer(self):
        s = solicitation([req("DELIVERY_RECEIPT", "OSS_EXTERNAL_MERGE")])
        s["requirements"][0]["min_count"] = True
        with self.assertRaises(engine.EvidenceError):
            engine.compile_assessment(public_vault(), s, AS_OF)

    def test_packet_tamper_fails_verifier(self):
        s = solicitation([req("DELIVERY_RECEIPT", "OSS_EXTERNAL_MERGE", min_count=2)])
        packet = engine.compile_assessment(public_vault(), s, AS_OF)
        self.assertTrue(engine.verify_assessment(public_vault(), s, packet))
        packet["outcome"] = "DISQUALIFIED"
        self.assertFalse(engine.verify_assessment(public_vault(), s, packet))

    def test_owner_hold_precedes_partner_gap(self):
        vault = {"schema": engine.VAULT_SCHEMA, "records": [
            record("ins-missing", "INSURANCE", "CGL", "MISSING"),
            record("cert-unknown", "CERTIFICATION", "SOC2", "UNKNOWN"),
        ]}
        s = solicitation([
            req("INSURANCE", "CGL", partner=True),
            req("CERTIFICATION", "SOC2", partner=True),
        ])
        packet = engine.compile_assessment(vault, s, AS_OF)
        self.assertEqual(packet["outcome"], "HOLD_MISSING_EVIDENCE")

    def test_cli_compile_verify_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            vault = td / "vault.json"; vault.write_text(EXAMPLE.read_text())
            sol = td / "sol.json"; sol.write_text(SOL.read_text())
            packet = td / "packet.json"; brief = td / "brief.md"
            base = [sys.executable, "-m", "revenue.qualification_evidence_vault.cli"]
            c = subprocess.run(base + ["compile", "--vault", str(vault), "--solicitation", str(sol), "--as-of", AS_OF, "--packet", str(packet), "--brief", str(brief)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(c.returncode, 0, c.stdout + c.stderr)
            self.assertIn("HOLD_MISSING_EVIDENCE", c.stdout)
            v = subprocess.run(base + ["verify", "--vault", str(vault), "--solicitation", str(sol), "--packet", str(packet), "--brief", str(brief)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(v.returncode, 0, v.stdout + v.stderr)
            self.assertIn("EXACT_QUALIFICATION_MATCH", v.stdout)
            c2 = subprocess.run(base + ["compile", "--vault", str(vault), "--solicitation", str(sol), "--as-of", AS_OF, "--packet", str(packet), "--brief", str(brief)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(c2.returncode, 2)


if __name__ == "__main__":
    unittest.main()
