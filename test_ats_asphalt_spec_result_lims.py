#!/usr/bin/env python3
"""Binary acceptance for ats-asphalt-spec-result-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter

import ats_asphalt_spec_result_lims as gate


class AtsAsphaltSpecResultLimsTests(unittest.TestCase):
    def test_acceptance_fixture_is_60_across_four_asphalt_classes(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 60)
        classes = [row["service_class"] for row in rows]
        self.assertEqual(classes.count("BINDER"), 15)
        self.assertEqual(classes.count("EMULSION"), 15)
        self.assertEqual(classes.count("MIX"), 15)
        self.assertEqual(classes.count("PERFORMANCE"), 15)

    def test_pass_contract_exact_state_counts(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.GOLDEN_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["hold_code_set"], sorted(gate.HOLD_CODES))
        self.assertEqual(Counter(result["hold_codes"]), Counter({code: 2 for code in gate.HOLD_CODES}))

    def test_twelve_holds_use_exact_truth_set_codes(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 12)
        by_code = {item["code"]: [] for item in result["holds"]}
        for item in result["holds"]:
            by_code[item["code"]].append(item)
        self.assertEqual(sorted(by_code), sorted(gate.HOLD_CODES))
        for code, items in by_code.items():
            self.assertEqual(len(items), 2, code)
        missing = [item["row_id"] for item in by_code["MISSING_SPEC"]]
        self.assertEqual(sorted(missing), ["B13", "M13"])
        wrong_unit = [item["row_id"] for item in by_code["WRONG_UNIT"]]
        self.assertEqual(sorted(wrong_unit), ["B14", "M14"])
        qty = [item["row_id"] for item in by_code["INSUFFICIENT_QUANTITY"]]
        self.assertEqual(sorted(qty), ["B15", "M15"])
        dupes = [item["row_id"] for item in by_code["DUPLICATE_ID"]]
        self.assertEqual(sorted(dupes), ["E13", "P13"])
        revision = [item["row_id"] for item in by_code["METHOD_REVISION"]]
        self.assertEqual(sorted(revision), ["E14", "P14"])
        expired = [item["row_id"] for item in by_code["EXPIRED_CALIBRATION"]]
        self.assertEqual(sorted(expired), ["E15", "P15"])

    def test_binder_emulsion_mix_performance_routes_are_asphalt_specific(self) -> None:
        result = gate.run_gate()
        routes = result["routes"]
        self.assertEqual(routes["ATS-BIND-02"], "BINDER_DSR_WORKLIST")
        self.assertEqual(routes["ATS-EMUL-02"], "EMULSION_RESIDUE_WORKLIST")
        self.assertEqual(routes["ATS-MIX-02"], "MIX_IGNITION_WORKLIST")
        self.assertEqual(routes["ATS-PERF-02"], "HAMBURG_WORKLIST")
        binder = next(item for item in result["accessions"] if item["sample_id"] == "ATS-BIND-02")
        self.assertEqual(binder["method"], "AASHTO T 315")
        self.assertEqual(binder["method_revision"], "T315-22")
        self.assertEqual(binder["spec_id"], "AASHTO M 320")
        self.assertEqual(binder["spec_revision"], "M320-23")
        self.assertEqual(binder["grade"], "PG 76-22")
        self.assertEqual(binder["unit"], "kPa")
        hamburg = next(item for item in result["accessions"] if item["sample_id"] == "ATS-PERF-02")
        self.assertEqual(hamburg["method"], "AASHTO T 324")
        self.assertEqual(hamburg["method_revision"], "T324-22")
        self.assertEqual(hamburg["unit"], "mm")
        self.assertEqual(hamburg["spec_id"], "FDOT 334")

    def test_mock_results_generate_one_oos_and_one_invalid_review_hold(self) -> None:
        result = gate.run_gate()
        oos = next(item for item in result["accessions"] if item["sample_id"] == gate.OOS_SAMPLE_ID)
        invalid = next(item for item in result["accessions"] if item["sample_id"] == gate.INVALID_SAMPLE_ID)
        self.assertEqual(oos["review_hold"], "REVIEW_HOLD_OOS")
        self.assertEqual(oos["simulated_result"]["disposition"], "OOS")
        self.assertEqual(oos["simulated_result"]["rut_depth_mm_20k"], 14.8)
        self.assertFalse(oos["released"])
        self.assertEqual(invalid["review_hold"], "REVIEW_HOLD_INVALID")
        self.assertEqual(invalid["simulated_result"]["reason"], "MISSING_RTFO_CONDITIONING_EVIDENCE")
        self.assertFalse(invalid["released"])
        self.assertEqual(result["oos_review_hold"], 1)
        self.assertEqual(result["invalid_review_hold"], 1)
        self.assertEqual(result["human_released"], 46)

    def test_sample_project_method_lineage_is_preserved(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["lineage"]), 48)
        self.assertEqual(len(set(result["lineage"].values())), 48)
        for item in result["accessions"]:
            self.assertEqual(item["lineage"]["sample_id"], item["sample_id"])
            self.assertEqual(item["lineage"]["project_id"], item["project_id"])
            self.assertEqual(item["lineage"]["method"], item["method"])
            self.assertEqual(item["lineage"]["method_revision"], item["method_revision"])
            self.assertEqual(item["lineage"]["spec_revision"], item["spec_revision"])
            self.assertEqual(item["lineage"]["lineage_sha256"], result["lineage"][item["sample_id"]])
            self.assertEqual(len(item["lineage"]["lineage_sha256"]), 64)

    def test_autonomous_release_denied_then_named_human_releases_46(self) -> None:
        result = gate.run_gate()
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )
        self.assertEqual(sum(1 for item in result["human_release_effects"] if item.get("ok")), 46)
        denied = [item for item in result["human_release_effects"] if not item.get("ok")]
        self.assertEqual(len(denied), 2)
        self.assertEqual(sorted(item["code"] for item in denied), ["REVIEW_HOLD_INVALID", "REVIEW_HOLD_OOS"])
        released_by = {item["released_by"] for item in result["accessions"] if item["released"]}
        self.assertEqual(released_by, {"tanya-nash-reviewer"})

    def test_replay_adds_zero_records_and_audit_hash_is_golden(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(len(first["audit_sha256"]), 64)
        self.assertEqual(gate.sha256_hex(first["audit"]), first["audit_sha256"])

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 48)
        self.assertEqual(len(journal["holds"]), 12)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["accession_count"], 48)
        self.assertEqual(replay["hold_count"], 12)
        self.assertEqual(replay["replay_noops"], 48)

    def test_named_human_can_acknowledge_oos_but_not_invalid(self) -> None:
        journal = gate.empty_journal()
        oos_row = next(item for item in gate.build_acceptance_fixture() if item["sample_id"] == gate.OOS_SAMPLE_ID)
        invalid_row = next(item for item in gate.build_acceptance_fixture() if item["sample_id"] == gate.INVALID_SAMPLE_ID)
        gate.ingest_row(journal, oos_row)
        gate.ingest_row(journal, invalid_row)
        oos_id = journal["sample_index"][gate.OOS_SAMPLE_ID]
        inv_id = journal["sample_index"][gate.INVALID_SAMPLE_ID]
        gate.import_simulated_result(journal, oos_id)
        gate.import_simulated_result(journal, inv_id)

        blocked = gate.release_report(journal, oos_id, actor_role="RELEASER", actor="tanya-nash-reviewer")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "REVIEW_HOLD_OOS")
        acknowledged = gate.release_report(
            journal, oos_id, actor_role="RELEASER", actor="tanya-nash-reviewer", acknowledge_oos=True
        )
        self.assertTrue(acknowledged["ok"])
        still = gate.release_report(journal, inv_id, actor_role="RELEASER", actor="tanya-nash-reviewer")
        self.assertFalse(still["ok"])
        self.assertEqual(still["code"], "REVIEW_HOLD_INVALID")

    def test_no_live_adapters_or_qc_decision(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["qc_decisions"], 0)
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["billing_writes"], 0)
        self.assertFalse(result["autonomous_release"])
        self.assertEqual(result["audit"]["adapters"]["qc_decision"], "NOT_WRITTEN")
        self.assertEqual(result["audit"]["adapters"]["instrument"], "SIMULATED_READ_ONLY")
        for item in result["accessions"]:
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            self.assertFalse(item["qc_decision_live"])
            self.assertEqual(item["adapters"]["lims"], "SIMULATED_READ_ONLY")


if __name__ == "__main__":
    unittest.main()
