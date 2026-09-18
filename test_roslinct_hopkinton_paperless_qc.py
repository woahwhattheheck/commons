#!/usr/bin/env python3
"""Binary acceptance for roslinct-hopkinton-paperless-qc-lims-01."""

from __future__ import annotations

import unittest

import roslinct_hopkinton_paperless_qc as gate


class RoslinctHopkintonPaperlessQcTests(unittest.TestCase):
    def test_acceptance_fixture_is_240_across_five_classes(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 240)
        by_class = {name: 0 for name in gate.CLASSES}
        exceptions = {name: 0 for name in ("LABEL", "TEMPERATURE", "DUPLICATE", "LATE", "OOS")}
        for row in rows:
            by_class[row["sample_class"]] += 1
            if row["exception_type"]:
                exceptions[row["exception_type"]] += 1
        self.assertEqual(by_class, {name: 48 for name in gate.CLASSES})
        self.assertEqual(exceptions, {"LABEL": 5, "TEMPERATURE": 5, "DUPLICATE": 5, "LATE": 5, "OOS": 4})

    def test_pass_contract_exact_state_counts(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(
            counts["expected"],
            {
                "input_rows": 240,
                "valid_completed": 216,
                "hold": 24,
                "accessioned": 216,
                "human_released": 216,
                "autonomous_released": 0,
                "instruments": 12,
                "contract_labs": 3,
            },
        )
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["hold_codes"], list(gate.EXPECTED_HOLD_CODES))
        self.assertEqual(
            result["hold_code_counts"],
            {
                "HOLD_DUPLICATE": 5,
                "HOLD_LABEL": 5,
                "HOLD_LATE": 5,
                "HOLD_OOS": 4,
                "HOLD_TEMPERATURE": 5,
            },
        )

    def test_seeded_holds_are_the_24_prescribed_exceptions(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 24)
        codes = sorted(item["code"] for item in result["holds"])
        self.assertEqual(codes.count("HOLD_LABEL"), 5)
        self.assertEqual(codes.count("HOLD_TEMPERATURE"), 5)
        self.assertEqual(codes.count("HOLD_DUPLICATE"), 5)
        self.assertEqual(codes.count("HOLD_LATE"), 5)
        self.assertEqual(codes.count("HOLD_OOS"), 4)
        self.assertTrue(all(item["state"] == "HOLD" for item in result["holds"]))
        self.assertTrue(all(item["testing_started"] is False for item in result["holds"]))
        label = next(item for item in result["holds"] if item["row_id"] == "RAW-44")
        temp = next(item for item in result["holds"] if item["row_id"] == "RAW-45")
        duplicate = next(item for item in result["holds"] if item["row_id"] == "RAW-46")
        late = next(item for item in result["holds"] if item["row_id"] == "RAW-47")
        oos = next(item for item in result["holds"] if item["row_id"] == "RAW-48")
        self.assertEqual(label["code"], "HOLD_LABEL")
        self.assertEqual(temp["code"], "HOLD_TEMPERATURE")
        self.assertEqual(duplicate["code"], "HOLD_DUPLICATE")
        self.assertEqual(duplicate["sample_id"], "SYN-RCT-RAW-01")
        self.assertEqual(late["code"], "HOLD_LATE")
        self.assertEqual(oos["code"], "HOLD_OOS")

    def test_valid_samples_traverse_expected_states_once(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["valid_completed"], 216)
        for item in result["accessions"]:
            self.assertEqual(item["states_seen"], list(gate.EXPECTED_STATES))
            self.assertEqual(item["state"], "RELEASED")
            self.assertTrue(item["released"])
            self.assertEqual(item["released_by"], gate.HUMAN_ACTOR)
            self.assertIsNotNone(item["custody"])
            self.assertIsNotNone(item["result"])
            self.assertIsNotNone(item["inventory"])
            self.assertIsNotNone(item["coa"])
            self.assertTrue(item["coa"]["in_spec"])
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            self.assertEqual(item["incumbent_lims"], "SIMULATED_READ_ONLY")

    def test_twelve_instruments_and_three_contract_labs_are_used(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["instruments"], list(gate.INSTRUMENTS))
        self.assertEqual(result["contract_labs"], list(gate.CONTRACT_LABS))
        internal = [item for item in result["accessions"] if item["schedule_kind"] == "INTERNAL"]
        external = [item for item in result["accessions"] if item["schedule_kind"] == "EXTERNAL"]
        self.assertEqual(len(internal), 180)
        self.assertEqual(len(external), 36)

    def test_autonomous_release_denied_then_named_human_releases_216(self) -> None:
        result = gate.run_gate()
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )
        self.assertEqual(sum(1 for item in result["human_release_effects"] if item.get("ok")), 216)
        self.assertEqual(result["human_released"], 216)
        self.assertEqual(result["autonomous_released"], 0)
        self.assertTrue(result["esignature_complete"])
        release_signs = [item for item in result["esignatures"] if item["kind"] == "QA_RELEASE"]
        self.assertEqual(len(release_signs), 216)
        self.assertTrue(all(item["part11_validated"] is False for item in result["esignatures"]))

    def test_replay_adds_zero_records_and_hashes_match(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(first["custody_sha256"], gate.GOLDEN_CUSTODY_SHA256)
        self.assertEqual(first["results_sha256"], gate.GOLDEN_RESULTS_SHA256)
        self.assertEqual(len(first["audit_sha256"]), 64)
        self.assertEqual(gate.sha256_hex(first["audit"]), first["audit_sha256"])

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 216)
        self.assertEqual(len(journal["holds"]), 24)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["accession_count"], 216)
        self.assertEqual(replay["hold_count"], 24)
        self.assertEqual(replay["replay_noops"], 216)

    def test_no_live_adapters_or_automatic_release(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["billing_writes"], 0)
        self.assertEqual(result["material_disposition"], 0)
        self.assertEqual(result["automatic_releases"], 0)
        self.assertFalse(result["autonomous_release"])
        self.assertFalse(result["part11_validated"])
        self.assertEqual(result["audit"]["adapters"]["incumbent_lims"], "SIMULATED_READ_ONLY")
        self.assertEqual(result["audit"]["adapters"]["part11"], "STYLE_ONLY_NOT_VALIDATED")
        self.assertEqual(result["audit"]["adapters"]["material_disposition"], "NOT_PERFORMED")

    def test_human_cannot_release_before_coa_or_when_held(self) -> None:
        journal = gate.empty_journal()
        raw = next(item for item in gate.build_acceptance_fixture() if item["row_id"] == "RAW-01")
        gate.ingest_row(journal, raw)
        acc_id = next(iter(journal["accessions"]))
        blocked = gate.release_report(journal, acc_id, actor_role="QA_RELEASER", actor="qa-human-01")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "REPORT_BLOCKED")
        gate.record_custody(journal, acc_id)
        gate.schedule_test(journal, acc_id, 0)
        gate.ingest_result(journal, acc_id)
        gate.record_inventory(journal, acc_id)
        gate.reconcile_coa(journal, acc_id)
        autonomous = gate.release_report(journal, acc_id, actor_role="SYSTEM", actor="bot")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        human = gate.release_report(journal, acc_id, actor_role="QA_RELEASER", actor="qa-human-01")
        self.assertTrue(human["ok"])

        journal2 = gate.empty_journal()
        hold_row = next(item for item in gate.build_acceptance_fixture() if item["row_id"] == "RAW-44")
        held = gate.ingest_row(journal2, hold_row)
        self.assertEqual(held["kind"], "HOLD")
        self.assertEqual(len(journal2["accessions"]), 0)


if __name__ == "__main__":
    unittest.main()
