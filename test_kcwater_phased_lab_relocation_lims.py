#!/usr/bin/env python3
"""Acceptance tests for kcwater-phased-lab-relocation-lims-01."""

from __future__ import annotations

import math
import unittest
from copy import deepcopy

import kcwater_phased_lab_relocation_lims as gate


class KCWaterPhasedLabRelocationLimsTests(unittest.TestCase):
    def test_frozen_fixture_has_exact_300_240_ready_60_hold_oracle(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 300)
        self.assertEqual(sum(row["expected_state"] == "READY" for row in rows), 240)
        self.assertEqual(sum(row["expected_state"] == "HOLD" for row in rows), 60)
        self.assertEqual({code: sum(row["expected_hold"] == code for row in rows) for code in gate.HOLD_CODES}, gate.HOLD_COUNTS)
        self.assertEqual(gate.fixture_sha256(rows), gate.GOLDEN_FIXTURE_SHA256)

    def test_contract_is_exactly_240_ready_and_60_hold(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 300)
        self.assertEqual(result["ready"], 240)
        self.assertEqual(result["holds"], 60)
        self.assertEqual(result["accessions"], 240)
        self.assertEqual(result["tests"], 240)
        self.assertEqual(result["results"], 240)
        self.assertEqual(result["reports_staged"], 240)
        self.assertEqual(result["reports_released"], 0)
        self.assertEqual(result["hold_counts"], gate.HOLD_COUNTS)

    def test_every_predetermined_hold_creates_no_lims_outputs(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {item["row_id"]: item for item in result["hold_records"]}
        self.assertEqual(len(holds), 60)
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["row_id"]]
            self.assertEqual(hold["code"], row["expected_hold"])
            self.assertEqual(hold["state"], "HOLD")
            self.assertEqual(hold["accessions_created"], 0)
            self.assertEqual(hold["tests_created"], 0)
            self.assertEqual(hold["results_created"], 0)
            self.assertEqual(hold["reports_staged"], 0)
            self.assertEqual(hold["reports_released"], 0)

    def test_every_valid_test_has_one_active_site_and_instrument_route(self) -> None:
        result = gate.run_gate()
        routes_by_id = {route["route_id"]: route for route in gate.ROUTE_CATALOG.values()}
        self.assertEqual(result["active_route_count"], 9)
        self.assertEqual(result["route_counts"], {"KCW-MAIN": 80, "KCW-TEMP": 80, "KCW-CONTINGENCY": 80})
        self.assertEqual(len(result["test_records"]), 240)
        for test in result["test_records"]:
            route = routes_by_id[test["route_id"]]
            self.assertTrue(route["active"])
            self.assertEqual(route["site_id"], test["site_id"])
            self.assertEqual(route["instrument_id"], test["instrument_id"])
            self.assertEqual(route["water_class"], test["water_class"])
            self.assertEqual(route["method_id"], test["method_id"])
            self.assertEqual(route["method_version"], test["method_version"])

    def test_result_never_crosses_site_and_hash_lineage_is_exact(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["hash_match_counts"], {"source": 240, "value": 240, "unit": 240, "qualifier": 240, "report": 240})
        accessions = {item["accession_id"]: item for item in result["accession_records"]}
        tests = {item["test_id"]: item for item in result["test_records"]}
        reports = {item["result_id"]: item for item in result["report_records"]}
        for raw in result["result_records"]:
            accession = accessions[raw["accession_id"]]
            test = tests[raw["test_id"]]
            report = reports[raw["result_id"]]
            self.assertEqual({accession["site_id"], test["site_id"], raw["site_id"], report["site_id"]}, {accession["site_id"]})
            self.assertEqual({test["instrument_id"], raw["instrument_id"], report["instrument_id"]}, {test["instrument_id"]})
            self.assertEqual(raw["source_sha256"], accession["source_sha256"])
            self.assertEqual(raw["source_sha256"], report["source_sha256"])
            self.assertEqual(raw["value_sha256"], gate.sha256_hex({"value": raw["value"]}))
            self.assertEqual(raw["unit_sha256"], gate.sha256_hex({"unit": raw["unit"]}))
            self.assertEqual(raw["qualifier_sha256"], gate.sha256_hex({"qualifier": raw["qualifier"]}))
            self.assertEqual(raw["result_sha256"], report["result_sha256"])

    def test_replay_adds_zero_and_changed_payload_conflicts_atomically(self) -> None:
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_submission(journal, row)
        self.assertEqual(gate.replay_into(journal, rows), {"added_accessions": 0, "added_tests": 0, "added_results": 0, "added_reports": 0, "added_holds": 0, "replay_noops": 300, "replay_conflicts": 0})
        changed = deepcopy(rows[0])
        changed["result_value"] = 999.25
        before = gate.canonical_json(journal)
        conflict = gate.ingest_submission(journal, changed)
        self.assertEqual(conflict["kind"], "REPLAY_CONFLICT")
        self.assertEqual(conflict["code"], "REPLAY_PAYLOAD_DIGEST_CONFLICT")
        self.assertEqual(gate.canonical_json(journal), before)

    def test_only_authoritative_named_human_can_release_report(self) -> None:
        journal = gate.empty_journal()
        ready = gate.ingest_submission(journal, gate.build_acceptance_fixture()[0])
        report_id = ready["report_id"]
        before = gate.canonical_json(journal)
        self.assertEqual(gate.release_report(journal, report_id, reviewer_id="SYSTEM"), {"ok": False, "code": "AUTONOMOUS_RELEASE_DENIED"})
        self.assertEqual(gate.canonical_json(journal), before)
        self.assertEqual(gate.release_report(journal, report_id, reviewer_id="unverified-human-claim"), {"ok": False, "code": "UNAUTHORIZED_REVIEWER"})
        self.assertEqual(gate.canonical_json(journal), before)
        released = gate.release_report(journal, report_id, reviewer_id="SYN-NAMED-HUMAN-JESSICA-JENSEN-01")
        self.assertTrue(released["ok"])
        self.assertFalse(released["duplicate"])
        self.assertEqual(released["status"], "RELEASED")
        self.assertEqual(released["released_by"]["display_name"], "Jessica Jensen (synthetic release authority)")

    def test_non_dict_nan_negative_and_malformed_dates_reject_without_mutation(self) -> None:
        journal = gate.empty_journal()
        baseline = gate.canonical_json(journal)
        for malformed in ("garbage", [1], 1, True, None):
            with self.subTest(malformed=repr(malformed)):
                response = gate.ingest_submission(journal, malformed)  # type: ignore[arg-type]
                self.assertEqual(response["kind"], "REJECT")
                self.assertEqual(response["code"], "REJECT_INVALID_INPUT")
                self.assertEqual(gate.canonical_json(journal), baseline)
        for field, value in (("temperature_c", math.nan), ("result_value", -0.01), ("collected_at", "2026-02-30T08:00:00Z"), ("received_at", "2026-09-01")):
            with self.subTest(field=field):
                malformed = deepcopy(gate.build_acceptance_fixture()[0])
                malformed[field] = value
                response = gate.ingest_submission(journal, malformed)
                self.assertEqual(response["kind"], "REJECT")
                self.assertEqual(response["code"], "REJECT_INVALID_INPUT")
                self.assertEqual(gate.canonical_json(journal), baseline)

    def test_synthetic_read_only_adapter_and_boundary_hold(self) -> None:
        adapter = gate.SyntheticReadOnlySubmissionAdapter(gate.build_acceptance_fixture())
        self.assertEqual(adapter.mode, "SYNTHETIC_READ_ONLY")
        self.assertFalse(adapter.live)
        self.assertEqual(adapter.writes, 0)
        with self.assertRaises(RuntimeError):
            adapter.write({"row_id": "nope"})
        journal = gate.empty_journal()
        realish = deepcopy(gate.build_acceptance_fixture()[0])
        realish["synthetic"] = False
        held = gate.ingest_submission(journal, realish)
        self.assertEqual(held["kind"], "HOLD")
        self.assertEqual(held["code"], "HOLD_TRUTH_BOUNDARY")
        self.assertEqual(len(journal["accessions"]), 0)
        self.assertEqual(len(journal["results"]), 0)

    def test_runs_and_checked_in_evidence_hashes_are_deterministic(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)
        self.assertEqual(first["manifest_sha256"], gate.GOLDEN_MANIFEST_SHA256)
        self.assertEqual(first["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(first["fixture_sha256"], second["fixture_sha256"])
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])


if __name__ == "__main__":
    unittest.main()
