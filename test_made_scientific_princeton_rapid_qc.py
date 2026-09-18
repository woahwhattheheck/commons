#!/usr/bin/env python3
"""Binary acceptance for made-scientific-princeton-rapid-qc-lims-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNNER_PATH = ROOT / "revenue" / "made_scientific_princeton_rapid_qc" / "runner.py"
SPEC = importlib.util.spec_from_file_location("made_scientific_princeton_rapid_qc_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


EXPECTED = {
    "batches": 200,
    "samples": 2400,
    "failures": 40,
    "oos": 10,
    "duplicate": 10,
    "late": 10,
    "interface_failure": 10,
    "specified_holds": 40,
    "valid_reconciled": 2360,
    "four_endpoint_reconciled": 2400,
    "duplicate_samples": 0,
    "orphans": 0,
    "released_without_named_qa": 0,
    "released_after_named_qa": 2360,
    "failure_hold": 40,
    "replay_changed_records": 0,
}


class MadeScientificPrincetonRapidQcTests(unittest.TestCase):
    def test_acceptance_fixture_is_200_batches_2400_samples(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 2400)
        batches = {row["batch_id"] for row in rows}
        self.assertEqual(len(batches), 200)
        self.assertEqual(sum(1 for row in rows if row["exception"]), 40)
        self.assertEqual(sum(1 for row in rows if row["exception_kind"] == "OOS"), 10)
        self.assertEqual(sum(1 for row in rows if row["exception_kind"] == "DUPLICATE"), 10)
        self.assertEqual(sum(1 for row in rows if row["exception_kind"] == "LATE"), 10)
        self.assertEqual(sum(1 for row in rows if row["exception_kind"] == "INTERFACE_FAILURE"), 10)
        self.assertTrue(all(sum(1 for row in rows if row["batch_id"] == batch_id) == 12 for batch_id in batches))

    def test_pass_contract_exact_200_2400_40_counts(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], EXPECTED)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])

    def test_valid_states_reconcile_across_four_simulated_endpoints(self) -> None:
        result = gate.run_gate()
        self.assertTrue(result["reconcile"]["reconciled"])
        self.assertEqual(result["reconcile"]["mismatches"], 0)
        self.assertEqual(result["reconcile"]["orphans"], 0)
        self.assertEqual(result["counts"]["four_endpoint_reconciled"], 2400)
        self.assertEqual(result["counts"]["valid_reconciled"], 2360)
        by_endpoint = {
            name: {payload["sample_id"]: payload for payload in result["endpoints"][name]}
            for name in gate.ENDPOINTS
        }
        for item in result["samples"]:
            states = {by_endpoint[name][item["sample_id"]]["state"] for name in gate.ENDPOINTS}
            self.assertEqual(states, {item["state"]})
            for name in gate.ENDPOINTS:
                payload = by_endpoint[name][item["sample_id"]]
                self.assertFalse(payload["live"])
                self.assertEqual(payload["interface"], gate.ENDPOINT_INTERFACES[name])

    def test_all_40_failures_enter_specified_hold_deviation(self) -> None:
        result = gate.run_gate()
        failures = [item for item in result["samples"] if item["exception"]]
        self.assertEqual(len(failures), 40)
        self.assertEqual(len(result["holds"]), 40)
        holds = {item["sample_id"]: item for item in result["holds"]}
        for item in failures:
            hold = holds[item["sample_id"]]
            self.assertTrue(hold["specified"])
            self.assertEqual(hold["hold"], item["hold"])
            self.assertEqual(hold["deviation"], item["deviation"])
            self.assertEqual(hold["kind"], item["exception_kind"])
            self.assertEqual(item["state"], "HOLD")
            self.assertFalse(item["released"])
        self.assertEqual(
            {item["hold"] for item in failures},
            {"HOLD_OOS", "HOLD_DUPLICATE", "HOLD_LATE", "HOLD_INTERFACE"},
        )
        self.assertEqual(
            {item["deviation"] for item in failures},
            {"DEV_OOS_POTENCY", "DEV_DUPLICATE_ACCESSION", "DEV_LATE_RAPID_QC", "DEV_INTERFACE_ENDPOINT"},
        )

    def test_zero_duplicates_zero_orphans(self) -> None:
        result = gate.run_gate()
        sample_ids = [item["sample_id"] for item in result["samples"]]
        result_ids = [item["result_id"] for item in result["samples"]]
        self.assertEqual(len(sample_ids), len(set(sample_ids)))
        self.assertEqual(len(result_ids), len(set(result_ids)))
        self.assertEqual(result["counts"]["duplicate_samples"], 0)
        self.assertEqual(result["counts"]["orphans"], 0)
        self.assertEqual(len(result["rejected_twins"]), 10)
        twin_ids = {item["twin_attempt_id"] for item in result["rejected_twins"]}
        self.assertTrue(twin_ids.isdisjoint(sample_ids))
        self.assertTrue(all(not item["kept"] for item in result["rejected_twins"]))

    def test_canonical_payload_hashes_match_golden(self) -> None:
        result = gate.run_gate()
        fixture = gate.load_fixture()
        self.assertEqual(result["labvantage_bundle_sha256"], fixture["golden_labvantage_bundle_sha256"])
        self.assertEqual(result["mes_bundle_sha256"], fixture["golden_mes_bundle_sha256"])
        self.assertEqual(result["qms_bundle_sha256"], fixture["golden_qms_bundle_sha256"])
        self.assertEqual(result["erp_bundle_sha256"], fixture["golden_erp_bundle_sha256"])
        self.assertEqual(result["audit_sha256"], fixture["golden_audit_sha256"])
        for name in gate.ENDPOINTS:
            payloads = result["endpoints"][name]
            self.assertEqual(len(payloads), 2400)
            for payload in payloads:
                body = {key: value for key, value in payload.items() if key != "payload_sha256"}
                self.assertEqual(payload["payload_sha256"], gate.sha256_hex(body))

    def test_replay_of_entire_corpus_changes_nothing(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["audit_sha256"], gate.load_fixture()["golden_audit_sha256"])
        self.assertEqual(len(first["audit_sha256"]), 64)
        self.assertEqual(gate.sha256_hex(first["audit"]), first["audit_sha256"])
        self.assertEqual(first["counts"]["replay_changed_records"], 0)
        self.assertEqual(first["replay"]["changed_records"], 0)
        self.assertEqual(first["replay"]["replay_noops"], 2400)
        self.assertEqual(first["labvantage_bundle_sha256"], second["labvantage_bundle_sha256"])
        self.assertEqual(first["mes_bundle_sha256"], second["mes_bundle_sha256"])
        self.assertEqual(first["qms_bundle_sha256"], second["qms_bundle_sha256"])
        self.assertEqual(first["erp_bundle_sha256"], second["erp_bundle_sha256"])

    def test_no_automatic_release_named_human_required(self) -> None:
        result = gate.run_gate()
        self.assertTrue(
            all(item["code"] == "RELEASE_BLOCKED_AUTONOMOUS" for item in result["autonomous_release_effects"])
        )
        self.assertEqual(result["counts"]["released_without_named_qa"], 0)
        self.assertFalse(result["automatic_release"])
        self.assertEqual(sum(1 for item in result["named_qa_release_effects"] if item.get("ok")), 2360)
        blocked = [item for item in result["named_qa_release_effects"] if not item.get("ok")]
        self.assertEqual(len(blocked), 40)
        self.assertTrue(all(item["code"] == "RELEASE_BLOCKED_OPEN_HOLD" for item in blocked))
        self.assertEqual(result["counts"]["released_after_named_qa"], 2360)
        self.assertEqual(result["counts"]["failure_hold"], 40)

    def test_named_qa_cannot_release_before_import_or_on_hold(self) -> None:
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        clean = next(item for item in rows if not item["exception"])
        held = next(item for item in rows if item["exception"])
        missing = gate.release_sample(journal, clean["sample_id"], actor_role="NAMED_QA", actor="qa-named-princeton-1")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["code"], "UNKNOWN_SAMPLE")

        gate.import_rows(journal, [clean, held])
        autonomous = gate.release_sample(journal, clean["sample_id"], actor_role="SYSTEM", actor="autonomous")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "RELEASE_BLOCKED_AUTONOMOUS")
        self.assertFalse(journal["samples"][clean["sample_id"]]["released"])

        named = gate.release_sample(journal, clean["sample_id"], actor_role="NAMED_QA", actor="qa-named-princeton-1")
        self.assertTrue(named["ok"])
        still = gate.release_sample(journal, held["sample_id"], actor_role="NAMED_QA", actor="qa-named-princeton-1")
        self.assertFalse(still["ok"])
        self.assertEqual(still["code"], "RELEASE_BLOCKED_OPEN_HOLD")

    def test_no_live_adapters_or_production_writes(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["phi_records"], 0)
        self.assertEqual(result["billing_writes"], 0)
        self.assertEqual(result["disposition_writes"], 0)
        self.assertEqual(result["cash_usd"], 0)
        self.assertEqual(result["audit"]["adapters"]["labvantage"], "SIMULATED_READONLY")
        self.assertEqual(result["audit"]["adapters"]["autolomate_mes"], "SIMULATED_READONLY")
        self.assertEqual(result["audit"]["adapters"]["veeva_qms"], "SIMULATED_READONLY")
        self.assertEqual(result["audit"]["adapters"]["netsuite_erp"], "SIMULATED_READONLY")


if __name__ == "__main__":
    unittest.main()
