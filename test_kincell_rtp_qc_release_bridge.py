#!/usr/bin/env python3
"""Binary acceptance for kincell-rtp-qc-release-bridge-lims-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNNER_PATH = ROOT / "revenue" / "kincell_rtp_qc_release_bridge" / "runner.py"
SPEC = importlib.util.spec_from_file_location("kincell_rtp_qc_release_bridge_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class KincellRtpQcReleaseBridgeTests(unittest.TestCase):
    def test_acceptance_fixture_is_300_from_30_batches(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 300)
        batches = {row["batch_id"] for row in rows}
        self.assertEqual(len(batches), 30)
        self.assertEqual(sum(1 for row in rows if row["plan"] == "IN_PROCESS"), 120)
        self.assertEqual(sum(1 for row in rows if row["plan"] == "FINAL"), 90)
        self.assertEqual(sum(1 for row in rows if row["plan"] == "STABILITY"), 90)
        self.assertEqual(sum(1 for row in rows if row["program"] == "AUTOLOGOUS"), 150)
        self.assertEqual(sum(1 for row in rows if row["program"] == "ALLOGENEIC"), 150)

    def test_pass_contract_exact_300_30_counts(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(
            counts["expected"],
            {
                "samples": 300,
                "batches": 30,
                "exceptions": 30,
                "qms_events": 30,
                "duplicate_samples": 0,
                "duplicate_results": 0,
                "truth_set_matches": 300,
                "released_without_named_qa": 0,
                "released_after_named_qa": 270,
                "exception_hold": 30,
                "replay_changed_records": 0,
            },
        )
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])

    def test_identifiers_specs_calculations_states_timestamps_match_truth_set(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        by_id = {item["sample_id"]: item for item in result["samples"]}
        self.assertEqual(len(by_id), 300)
        for row in rows:
            actual = by_id[row["sample_id"]]
            truth = gate.truth_set_row(row)
            self.assertEqual(actual["sample_id"], truth["sample_id"])
            self.assertEqual(actual["result_id"], truth["result_id"])
            self.assertEqual(actual["batch_id"], truth["batch_id"])
            self.assertEqual(actual["spec_lo"], truth["spec_lo"])
            self.assertEqual(actual["spec_hi"], truth["spec_hi"])
            self.assertEqual(actual["spec_unit"], truth["spec_unit"])
            self.assertEqual(actual["calculated"], truth["calculated"])
            self.assertEqual(actual["timestamp"], truth["timestamp"])
            self.assertEqual(actual["state"], truth["expected_state"])

    def test_zero_duplicate_samples_and_results(self) -> None:
        result = gate.run_gate()
        sample_ids = [item["sample_id"] for item in result["samples"]]
        result_ids = [item["result_id"] for item in result["samples"]]
        self.assertEqual(len(sample_ids), len(set(sample_ids)))
        self.assertEqual(len(result_ids), len(set(result_ids)))
        self.assertEqual(result["counts"]["duplicate_samples"], 0)
        self.assertEqual(result["counts"]["duplicate_results"], 0)

    def test_every_exception_opens_expected_simulated_qms_event(self) -> None:
        result = gate.run_gate()
        exceptions = [item for item in result["samples"] if item["exception"]]
        self.assertEqual(len(exceptions), 30)
        self.assertEqual(len(result["qms_events"]), 30)
        events = {item["event_id"]: item for item in result["qms_events"]}
        for item in exceptions:
            event = events[item["qms_event_id"]]
            self.assertEqual(event["sample_id"], item["sample_id"])
            self.assertEqual(event["kind"], item["qms_kind"])
            self.assertEqual(event["exception_code"], item["exception_code"])
            self.assertTrue(event["opened"])
            self.assertFalse(event["live"])
            self.assertEqual(event["interface"], "SIMULATED_VEEVA_QMS_READONLY")

    def test_erp_and_qms_payload_hashes_match_golden(self) -> None:
        result = gate.run_gate()
        fixture = gate.load_fixture()
        self.assertEqual(result["erp_bundle_sha256"], fixture["golden_erp_bundle_sha256"])
        self.assertEqual(result["qms_bundle_sha256"], fixture["golden_qms_bundle_sha256"])
        self.assertEqual(len(result["erp_hashes"]), 30)
        self.assertEqual(len(result["qms_hashes"]), 30)
        self.assertEqual(len(set(result["erp_hashes"])), 30)
        self.assertEqual(len(set(result["qms_hashes"])), 30)
        for payload in result["erp_payloads"]:
            body = {key: value for key, value in payload.items() if key != "payload_sha256"}
            self.assertEqual(payload["payload_sha256"], gate.sha256_hex(body))
            self.assertFalse(payload["live"])
            self.assertEqual(payload["disposition"], "HOLD")
        for payload in result["qms_events"]:
            body = {key: value for key, value in payload.items() if key != "payload_sha256"}
            self.assertEqual(payload["payload_sha256"], gate.sha256_hex(body))

    def test_replay_changes_zero_records_and_audit_hash_is_identical(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["audit_sha256"], gate.load_fixture()["golden_audit_sha256"])
        self.assertEqual(len(first["audit_sha256"]), 64)
        self.assertEqual(gate.sha256_hex(first["audit"]), first["audit_sha256"])
        self.assertEqual(first["counts"]["replay_changed_records"], 0)
        self.assertEqual(first["replay"]["changed_records"], 0)
        self.assertEqual(first["replay"]["replay_noops"], 300)

    def test_release_blocked_until_named_qa_no_automatic_release(self) -> None:
        result = gate.run_gate()
        self.assertTrue(
            all(item["code"] == "RELEASE_BLOCKED_AUTONOMOUS" for item in result["autonomous_release_effects"])
        )
        self.assertEqual(result["counts"]["released_without_named_qa"], 0)
        self.assertFalse(result["automatic_release"])
        self.assertEqual(sum(1 for item in result["named_qa_release_effects"] if item.get("ok")), 270)
        blocked = [item for item in result["named_qa_release_effects"] if not item.get("ok")]
        self.assertEqual(len(blocked), 30)
        self.assertTrue(all(item["code"] == "RELEASE_BLOCKED_OPEN_QMS" for item in blocked))
        self.assertEqual(result["counts"]["released_after_named_qa"], 270)
        self.assertEqual(result["counts"]["exception_hold"], 30)

    def test_named_qa_cannot_release_before_import_or_on_exception(self) -> None:
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        clean = next(item for item in rows if not item["exception"])
        exception = next(item for item in rows if item["exception"])
        missing = gate.release_sample(journal, clean["sample_id"], actor_role="NAMED_QA", actor="qa-named-1")
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["code"], "UNKNOWN_SAMPLE")

        gate.import_rows(journal, [clean, exception])
        autonomous = gate.release_sample(journal, clean["sample_id"], actor_role="SYSTEM", actor="autonomous")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "RELEASE_BLOCKED_AUTONOMOUS")
        self.assertFalse(journal["samples"][clean["sample_id"]]["released"])

        named = gate.release_sample(journal, clean["sample_id"], actor_role="NAMED_QA", actor="qa-named-1")
        self.assertTrue(named["ok"])
        still = gate.release_sample(journal, exception["sample_id"], actor_role="NAMED_QA", actor="qa-named-1")
        self.assertFalse(still["ok"])
        self.assertEqual(still["code"], "RELEASE_BLOCKED_OPEN_QMS")

    def test_no_live_adapters_or_production_writes(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["phi_records"], 0)
        self.assertEqual(result["billing_writes"], 0)
        self.assertEqual(result["cash_usd"], 0)
        self.assertEqual(result["audit"]["adapters"]["veeva_qms"], "SIMULATED_READONLY")
        self.assertEqual(result["audit"]["adapters"]["erp"], "SIMULATED_READONLY")


if __name__ == "__main__":
    unittest.main()
