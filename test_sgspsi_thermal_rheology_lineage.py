#!/usr/bin/env python3
"""Binary acceptance for sgspsi-high-throughput-thermal-rheology-lineage-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter
from copy import deepcopy

import sgspsi_thermal_rheology_lineage as gate


class SgsPsiThermalRheologyLineageTests(unittest.TestCase):
    def test_acceptance_fixture_is_120_frozen_requests(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 120)
        holds = [row["expected_hold"] for row in rows]
        self.assertEqual(holds.count(None), 90)
        self.assertEqual(holds.count("MISSING_LINKAGE"), 8)
        self.assertEqual(holds.count("DUPLICATE_CONTAINER"), 6)
        self.assertEqual(holds.count("METHOD_INSTRUMENT_MISMATCH"), 6)
        self.assertEqual(holds.count("SLOT_COLLISION"), 5)
        self.assertEqual(holds.count("QC_FAILURE"), 5)
        self.assertEqual(gate.fixture_manifest()["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)

    def test_pass_contract_expected_equals_actual(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.GOLDEN_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["ready"], 90)
        self.assertEqual(result["held"], 30)
        self.assertEqual(result["hold_code_set"], sorted(gate.HOLD_CODES))
        self.assertEqual(Counter(result["hold_codes"]), Counter(gate.HOLD_PLAN))

    def test_thirty_holds_use_exact_truth_set_codes(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 30)
        by_code = {code: [] for code in gate.HOLD_CODES}
        for item in result["holds"]:
            by_code[item["code"]].append(item)
        self.assertEqual(
            [item["request_id"] for item in by_code["MISSING_LINKAGE"]],
            ["SGS-HLINK%02d" % n for n in range(1, 9)],
        )
        self.assertEqual(
            [item["request_id"] for item in by_code["DUPLICATE_CONTAINER"]],
            ["SGS-HDUP%02d" % n for n in range(1, 7)],
        )
        self.assertEqual(
            [item["request_id"] for item in by_code["METHOD_INSTRUMENT_MISMATCH"]],
            ["SGS-HMIS%02d" % n for n in range(1, 7)],
        )
        self.assertEqual(
            [item["request_id"] for item in by_code["SLOT_COLLISION"]],
            ["SGS-HSLOT%02d" % n for n in range(1, 6)],
        )
        self.assertEqual(
            [item["request_id"] for item in by_code["QC_FAILURE"]],
            ["SGS-HQC%02d" % n for n in range(1, 6)],
        )
        self.assertTrue(all(item["state"] == "HOLD" for item in result["holds"]))

    def test_one_sample_occupies_each_reserved_slot(self) -> None:
        result = gate.run_gate()
        occupancy = result["slot_occupancy"]
        self.assertEqual(len(occupancy), 90)
        self.assertEqual(len(set(occupancy)), 90)
        self.assertEqual(len(set(occupancy.values())), 90)
        for index in range(1, 91):
            slot = gate.reserved_slot_for(index)
            self.assertEqual(occupancy[slot], gate.valid_request_id(index))
        first = next(item for item in result["accessions"] if item["request_id"] == "SGS-V001")
        self.assertEqual(first["instrument"], "DSC-250")
        self.assertEqual(first["method"], "ASTM-D3418")
        self.assertEqual(first["method_version"], "D3418-21-SYN")
        self.assertEqual(first["slot"], "DSC-01")
        self.assertEqual(first["route"], "DSC250_AUTOSAMPLER")
        even = next(item for item in result["accessions"] if item["request_id"] == "SGS-V002")
        self.assertEqual(even["instrument"], "HR-20")
        self.assertEqual(even["method"], "ISO-6721-10")
        self.assertEqual(even["slot"], "HR-01")
        self.assertEqual(even["route"], "HR20_AUTOSAMPLER")

    def test_source_method_raw_unit_report_hashes_match(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["lineage_sha256"], gate.GOLDEN_LINEAGE_SHA256)
        self.assertEqual(result["report_digest"], gate.GOLDEN_REPORT_DIGEST)
        self.assertEqual(len(result["lineage"]), 90)
        self.assertEqual(len(set(item["report_hash"] for item in result["lineage"])), 90)
        for item in result["accessions"]:
            self.assertEqual(
                item["source_hash"],
                gate.source_hash(item["requirement_id"], item["form_id"], item["payment_id"]),
            )
            self.assertEqual(
                item["method_hash"],
                gate.method_hash(item["instrument"], item["method"], item["method_version"]),
            )
            self.assertEqual(item["raw_value_hash"], gate.raw_value_hash(item["raw"]))
            self.assertEqual(item["unit_hash"], gate.unit_hash(item["instrument"]))
            self.assertEqual(item["report_hash"], gate.sha256_hex(item["report"]))
            self.assertEqual(item["report"]["state"], "STAGED")
            self.assertFalse(item["released"])

    def test_replay_is_idempotent_and_adds_no_records(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["lineage_sha256"], second["lineage_sha256"])
        self.assertEqual(first["report_digest"], second["report_digest"])

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 90)
        self.assertEqual(len(journal["holds"]), 30)
        self.assertEqual(len(journal["slots"]), 90)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["added_record_count"], 0)
        self.assertEqual(replay["accession_count"], 90)
        self.assertEqual(replay["hold_count"], 30)
        self.assertEqual(replay["slot_count"], 90)
        self.assertEqual(replay["replay_noops"], 90)

    def test_reports_stay_staged_pending_named_approval(self) -> None:
        journal = gate.empty_journal()
        row = next(item for item in gate.build_acceptance_fixture() if item["request_id"] == "SGS-V001")
        gate.ingest_row(journal, row)
        acc_id = next(iter(journal["accessions"]))
        record = journal["accessions"][acc_id]
        self.assertEqual(record["state"], "READY")
        self.assertEqual(gate.report_status(record), "STAGED_PENDING_NAMED_APPROVAL")

        autonomous = gate.release_report(journal, acc_id, actor_role="SYSTEM", actor="bot")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(record["released"])
        self.assertEqual(record["report"]["state"], "STAGED")

        human = gate.release_report(journal, acc_id, actor_role="APPROVER", actor="kyle-copeland-named")
        self.assertTrue(human["ok"])
        self.assertEqual(record["report_status"], "RELEASED")
        self.assertEqual(record["released_by"], "kyle-copeland-named")
        again = gate.release_report(journal, acc_id, actor_role="APPROVER", actor="kyle-copeland-named")
        self.assertTrue(again["ok"])
        self.assertTrue(again["duplicate"])

    def test_local_holds_match_predetermined_codes(self) -> None:
        journal = gate.empty_journal()
        valid = next(item for item in gate.build_acceptance_fixture() if item["request_id"] == "SGS-V010")
        missing = deepcopy(valid)
        missing["request_id"] = "SGS-LOCAL-LINK"
        missing["container_id"] = "CTR-LOCAL-LINK"
        missing["requirement_id"] = ""
        missing["slot"] = "DSC-99"
        self.assertEqual(gate.ingest_row(journal, missing)["code"], "MISSING_LINKAGE")

        journal = gate.empty_journal()
        gate.ingest_row(journal, valid)
        dup = deepcopy(valid)
        dup["request_id"] = "SGS-LOCAL-DUP"
        dup["row_id"] = "RLOCALDUP"
        self.assertEqual(gate.ingest_row(journal, dup)["code"], "DUPLICATE_CONTAINER")

        journal = gate.empty_journal()
        mismatch = deepcopy(valid)
        mismatch["request_id"] = "SGS-LOCAL-MIS"
        mismatch["container_id"] = "CTR-LOCAL-MIS"
        mismatch["method"] = "ASTM-D3418"
        mismatch["slot"] = "DSC-98"
        self.assertEqual(gate.ingest_row(journal, mismatch)["code"], "METHOD_INSTRUMENT_MISMATCH")

        journal = gate.empty_journal()
        first = next(item for item in gate.build_acceptance_fixture() if item["request_id"] == "SGS-V001")
        gate.ingest_row(journal, first)
        collide = deepcopy(valid)
        collide["request_id"] = "SGS-LOCAL-SLOT"
        collide["container_id"] = "CTR-LOCAL-SLOT"
        collide["instrument"] = "DSC-250"
        collide["method"] = "ASTM-D3418"
        collide["slot"] = "DSC-01"
        self.assertEqual(gate.ingest_row(journal, collide)["code"], "SLOT_COLLISION")

        journal = gate.empty_journal()
        qc = deepcopy(valid)
        qc["request_id"] = "SGS-LOCAL-QC"
        qc["container_id"] = "CTR-LOCAL-QC"
        qc["slot"] = "HR-99"
        qc["raw"]["viscosity_std_pa_s"] = 4.0
        qc["raw"]["qc_ok"] = False
        self.assertEqual(gate.ingest_row(journal, qc)["code"], "QC_FAILURE")

    def test_no_live_interfaces_or_production_writes(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertFalse(result["autonomous_certification"])
        self.assertFalse(result["autonomous_release"])
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["pre_sale_transport"], "NONE")
        self.assertEqual(result["cash_usd"], 0)
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )
        for item in result["accessions"]:
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            self.assertFalse(item["released"])


if __name__ == "__main__":
    unittest.main()
