#!/usr/bin/env python3
"""Binary acceptance for weck-coc-preaccession-validator-lims-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNNER_PATH = ROOT / "revenue" / "weck_coc_preaccession_validator" / "runner.py"
SPEC = importlib.util.spec_from_file_location("weck_coc_preaccession_validator_runner", RUNNER_PATH)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gate)


class WeckCocPreaccessionValidatorTests(unittest.TestCase):
    def test_acceptance_fixture_is_400_split_320_80(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 400)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "ACCESSION"), 320)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "HOLD"), 80)
        loaded = gate.load_fixture()
        self.assertEqual(len(loaded), 400)
        self.assertEqual(
            [row["coc_id"] for row in loaded],
            [row["coc_id"] for row in rows],
        )

    def test_pass_contract_exact_state_counts_and_audit_hash(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.EXPECTED_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["replay_audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(len(result["audit_sha256"]), 64)

    def test_every_exception_blocks_with_exact_coded_reason(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {item["coc_id"]: item for item in result["hold_records"]}
        self.assertEqual(len(holds), 80)
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["coc_id"]]
            self.assertEqual(hold["code"], row["expected_hold_code"])
            self.assertEqual(hold["state"], "HOLD")
            self.assertEqual(hold["owner_role"], "PROJECT_MANAGER_ASSISTANT")
            self.assertEqual(hold["owner_desk"], "COC_RECEIPT_ACK")
            self.assertFalse(hold["receipt_ack"])
        self.assertEqual(result["hold_code_counts"], {code: 8 for code in gate.HOLD_CODES})
        accounted = {item["coc_id"] for item in result["accession_records"]} | set(holds)
        self.assertEqual(accounted, {row["coc_id"] for row in rows})

    def test_valid_accessions_have_field_parity_and_unique_tests(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["parity_failures"], [])
        self.assertEqual(result["orphan_tests"], 0)
        self.assertEqual(result["duplicate_accessions"], 0)
        sample_ids = [item["sample_id"] for item in result["accession_records"]]
        self.assertEqual(len(sample_ids), len(set(sample_ids)))
        test_keys = []
        for item in result["accession_records"]:
            self.assertTrue(item["source_hash"])
            self.assertTrue(item["source_coordinate"])
            self.assertTrue(item["receipt_ack"])
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            self.assertEqual(len(item["test_map"]), 1)
            test_keys.append((item["accession_id"], item["test_map"][0]["test_code"]))
        self.assertEqual(len(test_keys), len(set(test_keys)))

    def test_coa_and_two_edd_formats_match_golden_digests(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["coa_digest"], gate.GOLDEN_COA_DIGEST)
        self.assertEqual(result["geotracker_digest"], gate.GOLDEN_GEOTRACKER_DIGEST)
        self.assertEqual(result["epa_sedd_digest"], gate.GOLDEN_EPA_SEDD_DIGEST)
        self.assertEqual(result["coa_releasable"], 320)
        self.assertEqual(result["edd_releasable"], 320)

    def test_replay_is_idempotent(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 320)
        self.assertEqual(len(journal["holds"]), 80)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["replay_noops"], 400)

    def test_no_automatic_release_named_human_required(self) -> None:
        result = gate.run_gate()
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )
        self.assertEqual(result["autonomous_released"], 0)
        self.assertEqual(sum(1 for item in result["human_release_effects"] if item.get("ok")), 320)
        journal = gate.empty_journal()
        valid = next(row for row in gate.build_acceptance_fixture() if row["expected_state"] == "ACCESSION")
        ingested = gate.ingest_row(journal, valid)
        acc_id = ingested["accession_id"]
        denied = gate.release_accession(journal, acc_id, actor="robot", actor_role="AUTOMATION")
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "HOLD_NAMED_HUMAN_REQUIRED")
        self.assertFalse(journal["accessions"][acc_id]["released"])
        before = gate.regenerate_deliverables(journal)
        self.assertEqual(before["coa_count"], 0)
        human = gate.release_accession(
            journal,
            acc_id,
            actor=gate.HUMAN_RELEASER,
            actor_role=gate.HUMAN_ROLE,
        )
        self.assertTrue(human["ok"])
        after = gate.regenerate_deliverables(journal)
        self.assertEqual(after["coa_count"], 1)
        self.assertEqual(after["geotracker_count"], 1)
        self.assertEqual(after["epa_sedd_count"], 1)

    def test_no_live_adapters_or_production_write(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["live_reports"], 0)
        self.assertEqual(result["billing_writes"], 0)
        self.assertEqual(result["phi_records"], 0)
        self.assertEqual(result["cash_usd"], 0)
        self.assertEqual(result["truth_gate"], "HOLD / BUILD-AND-VERIFY")


if __name__ == "__main__":
    unittest.main()
