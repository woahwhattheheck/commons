#!/usr/bin/env python3
"""Fail-closed binary for AT-GROK-CMDP-EVIDENCE-01.

The runner is the product. HTML is a window, not the proof.
Fail-closed on invented fields, missing citations, submission, or
silent unknown-as-known.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import at_grok_cmdp_evidence as door

gate = door.MODULE
ROOT = Path(__file__).resolve().parent


class AtGrokCmdpEvidenceTests(unittest.TestCase):
    def test_three_families_and_child_nodes_are_cited(self) -> None:
        matrix = gate.schema_matrix()
        self.assertEqual(matrix["families"], ["MICROBIAL", "CHEMS_RADS", "CRYPTOSPORIDIUM"])
        self.assertEqual(
            matrix["child_nodes"],
            {
                "MICROBIAL": ["sampleResultMicro", "sampleResultField"],
                "CHEMS_RADS": ["sampleResultChem", "sampleResultField"],
                "CRYPTOSPORIDIUM": [
                    "sampleResultCrypto",
                    "sampleResultMeasure",
                    "sampleResultField",
                ],
            },
        )
        self.assertEqual(gate.validate_matrix(matrix), [])
        self.assertGreaterEqual(len(matrix["fields"]), 40)
        self.assertGreaterEqual(len(matrix["validations"]), 8)
        self.assertGreaterEqual(len(matrix["correction_rejection"]), 5)
        self.assertGreaterEqual(len(matrix["source_to_draft_reconciliation"]), 4)
        xml = matrix["version_effective_date"]["xml_schema"]
        self.assertEqual(xml["document_version"], "1.13")
        self.assertEqual(xml["effective_date"], "2019-12-09")
        self.assertTrue(xml["citation"]["url"].startswith("https://www.oregon.gov/"))

    def test_every_field_and_rule_has_source_url_section_and_date(self) -> None:
        matrix = gate.schema_matrix()
        for row in matrix["fields"]:
            cite = row["citation"]
            self.assertTrue(cite["url"].startswith("https://"), row["xml_element"])
            self.assertTrue(cite["page_or_section"], row["xml_element"])
            self.assertTrue(cite["version"], row["xml_element"])
            self.assertTrue(cite["effective_date"], row["xml_element"])
        for bucket in (
            matrix["validations"],
            matrix["correction_rejection"],
            matrix["source_to_draft_reconciliation"],
        ):
            for row in bucket:
                self.assertTrue(row["citation"]["url"].startswith("https://"), row.get("id"))
                self.assertTrue(row["citation"]["page_or_section"], row.get("id"))

    def test_unknowns_are_written_exactly(self) -> None:
        matrix = gate.schema_matrix()
        self.assertGreaterEqual(len(matrix["unknowns"]), 6)
        for row in matrix["unknowns"]:
            self.assertEqual(row["status"], gate.UNKNOWN)
            self.assertTrue(row["status"].startswith("UNKNOWN"))
            self.assertIn("BUYER OR VENDOR SAMPLE REQUIRED", row["status"])
        self.assertEqual(matrix["version_effective_date"]["later_than_1_13"], gate.UNKNOWN)
        analyte = next(row for row in matrix["fields"] if row["xml_element"] == "analyteCd")
        self.assertEqual(analyte["valid_values_status"], gate.UNKNOWN)
        self.assertFalse(analyte["valid_values"])

    def test_synthetic_fixtures_use_documented_fields_only(self) -> None:
        fixtures = gate.synthetic_fixtures()
        self.assertEqual(len(fixtures), 6)
        families = {row["family"] for row in fixtures}
        self.assertEqual(families, set(gate.FAMILIES))
        for row in fixtures:
            self.assertEqual(gate.validate_fixture_fields(row), [])
            for key in row.get("sample") or {}:
                self.assertIn(key, gate.ALLOWED_SAMPLE_KEYS)

    def test_pass_contract_and_golden_audit_hash(self) -> None:
        result = gate.run_evidence()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertTrue(counts["match"])
        self.assertEqual(result["drafts"], 5)
        self.assertEqual(result["holds"], 1)
        self.assertEqual(result["families_drafted"], 3)
        self.assertEqual(result["hold_codes"], ["ORIGINAL_ID_REQUIRED_RP_TG_CO"])
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["replay_audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(len(result["audit_sha256"]), 64)
        self.assertTrue(result["ok"])
        self.assertNotEqual(gate.GOLDEN_AUDIT_SHA256, "PIN_AFTER_FIRST_RUN")

    def test_invented_fields_fail_closed(self) -> None:
        failures = gate.invented_field_probe(gate.synthetic_fixtures())
        self.assertTrue(failures)
        self.assertTrue(any("invented" in item for item in failures))

    def test_missing_citations_fail_closed(self) -> None:
        failures = gate.missing_citation_probe(gate.schema_matrix())
        self.assertTrue(failures)
        blob = " ".join(failures)
        self.assertIn("citation", blob)

    def test_silent_unknown_as_known_fails_closed(self) -> None:
        failures = gate.unknown_as_known_probe(gate.schema_matrix())
        self.assertTrue(failures)
        self.assertTrue(any("unknown-as-known" in item for item in failures))
        fixtures = gate.synthetic_fixtures()
        chem = next(row for row in fixtures if row["family"] == "CHEMS_RADS")
        chem["results"][0]["analyteCd"] = "1040"
        self.assertTrue(gate.validate_fixture_fields(chem))

    def test_submission_attempts_fail_closed(self) -> None:
        refused = gate.submission_probe()
        self.assertFalse(refused["ok"])
        self.assertEqual(refused["code"], "SUBMISSION_REFUSED")
        self.assertEqual(refused["action"], "Certify and Submit to State")
        result = gate.run_evidence()
        self.assertEqual(result["live_submissions"], 0)
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["city_contacts"], 0)
        self.assertTrue(all(not item["submitted"] for item in result["draft_records"]))
        self.assertTrue(all(not item["certified"] for item in result["draft_records"]))
        self.assertTrue(all(not item["live"] for item in result["draft_records"]))

    def test_replay_adds_zero(self) -> None:
        first = gate.run_evidence()
        second = gate.run_evidence()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["replay"]["added_drafts"], 0)
        self.assertEqual(first["replay"]["added_holds"], 0)
        ledger = gate.empty_ledger()
        rows = gate.synthetic_fixtures()
        for row in rows:
            gate.ingest(ledger, row)
        replay = gate.replay_into(ledger, rows)
        self.assertEqual(replay["added_drafts"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["replay_noops"], 6)

    def test_named_human_disposition_only(self) -> None:
        result = gate.run_evidence()
        self.assertEqual(result["autonomous_release_effect"]["code"], "AUTONOMOUS_DISPOSITION_DENIED")
        self.assertEqual(result["autonomous_released"], 0)
        self.assertEqual(sum(1 for item in result["human_release_effects"] if item.get("ok")), 5)
        ledger = gate.empty_ledger()
        for row in gate.synthetic_fixtures():
            gate.ingest(ledger, row)
        draft = next(iter(ledger["drafts"].values()))
        auto = gate.dispose(draft, "robot", "AUTONOMOUS")
        self.assertFalse(auto["ok"])
        other = gate.dispose(draft, "someone", "INTAKE")
        self.assertEqual(other["code"], "HOLD_NAMED_HUMAN_REQUIRED")
        human = gate.dispose(draft, gate.HUMAN, gate.HUMAN_ROLE)
        self.assertTrue(human["ok"])
        self.assertFalse(draft["submitted"])

    def test_seivers_spelling_preserved(self) -> None:
        matrix = gate.schema_matrix()
        packed = json.dumps(matrix, ensure_ascii=True)
        self.assertIn("Seivers", packed)
        self.assertNotIn('"Sievers"', packed)
        self.assertEqual(matrix["seivers_spelling"], "Seivers")
        result = gate.run_evidence()
        self.assertEqual(result["seivers_spelling"], "Seivers")

    def test_official_command_prints_ok_true_and_audit(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "at_grok_cmdp_evidence.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ok true", proc.stdout)
        self.assertIn("audit_sha256 %s" % gate.GOLDEN_AUDIT_SHA256, proc.stdout)
        payload = json.loads(proc.stdout[proc.stdout.index("{") :])
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(payload["official_binary"], "python3 at_grok_cmdp_evidence.py")
        self.assertEqual(payload["cash_usd"], 0)
        self.assertEqual(payload["state"], gate.STATE)


if __name__ == "__main__":
    unittest.main()
