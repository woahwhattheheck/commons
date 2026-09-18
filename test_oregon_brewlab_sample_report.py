#!/usr/bin/env python3
"""Binary acceptance for oregon-brewlab-sample-report-reconciliation-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter
from copy import deepcopy

import oregon_brewlab_sample_report as gate


class OregonBrewlabSampleReportTests(unittest.TestCase):
    def test_acceptance_fixture_is_120_frozen_submissions(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 120)
        holds = [row["expected_hold"] for row in rows]
        self.assertEqual(holds.count(None), 96)
        self.assertEqual(holds.count("FORM_CONTAINER_MISMATCH"), 8)
        self.assertEqual(holds.count("DUPLICATE_ID"), 6)
        self.assertEqual(holds.count("WARM_MICRO_VDK"), 5)
        self.assertEqual(holds.count("INSUFFICIENT_VOLUME"), 5)
        self.assertEqual(gate.fixture_manifest()["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)

    def test_pass_contract_expected_equals_actual(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.GOLDEN_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["ready"], 96)
        self.assertEqual(result["held"], 24)
        self.assertEqual(result["hold_code_set"], sorted(gate.HOLD_CODES))
        self.assertEqual(Counter(result["hold_codes"]), Counter(gate.HOLD_CODE_COUNTS))

    def test_twenty_four_holds_use_exact_truth_set_codes(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 24)
        by_code = {code: [] for code in gate.HOLD_CODES}
        for item in result["holds"]:
            by_code[item["code"]].append(item)
        self.assertEqual(
            sorted(item["sample_id"] for item in by_code["FORM_CONTAINER_MISMATCH"]),
            ["OBL-M-%02d" % n for n in range(1, 9)],
        )
        self.assertEqual(
            sorted(item["sample_id"] for item in by_code["DUPLICATE_ID"]),
            ["OBL-V-%03d" % n for n in range(1, 7)],
        )
        self.assertEqual(
            sorted(item["sample_id"] for item in by_code["WARM_MICRO_VDK"]),
            ["OBL-W-%02d" % n for n in range(1, 6)],
        )
        self.assertEqual(
            sorted(item["sample_id"] for item in by_code["INSUFFICIENT_VOLUME"]),
            ["OBL-U-%02d" % n for n in range(1, 6)],
        )
        self.assertTrue(all(item["ready"] is False for item in result["holds"]))

    def test_valid_rows_route_asbc_methods_and_become_ready(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["ready"], 96)
        self.assertEqual(len(set(result["job_ids"])), 96)
        first = next(item for item in result["jobs"] if item["sample_id"] == "OBL-V-001")
        self.assertEqual(first["analysis"], "ABV")
        self.assertEqual(first["method"], "ASBC Beer-4G")
        self.assertEqual(first["method_version"], "Beer-4G")
        self.assertEqual(first["unit"], "%ABV")
        self.assertEqual(first["route"], "ASBC_BEER_4G")
        self.assertEqual(first["state"], "READY")
        self.assertEqual(first["report_status"], "STAGED")
        vdk = next(item for item in result["jobs"] if item["analysis"] == "VDK")
        self.assertEqual(vdk["method"], "ASBC Beer-25B")
        self.assertEqual(vdk["unit"], "mg/L")
        micro = next(item for item in result["jobs"] if item["analysis"] == "MICRO_UBA")
        self.assertEqual(micro["method"], "ASBC Microbiological Control-2B")
        fcr = next(item for item in result["jobs"] if item["analysis"] == "FCR")
        self.assertEqual(fcr["method"], "ASBC Beer-22A")
        for item in result["jobs"]:
            self.assertEqual(item["state"], "READY")
            self.assertTrue(item["qc_signoff"])
            self.assertFalse(item["interface_live"])
            self.assertEqual(item["interface_state"], "SIMULATED")

    def test_method_version_unit_source_hashes_match_golden_catalog(self) -> None:
        result = gate.run_gate()
        catalog = gate.golden_catalog()
        self.assertEqual(catalog["catalog_sha256"], gate.GOLDEN_CATALOG_SHA256)
        self.assertEqual(result["catalog_sha256"], gate.GOLDEN_CATALOG_SHA256)
        self.assertTrue(gate.hashes_match_catalog(result))
        abv = catalog["methods"]["ABV"]
        self.assertEqual(abv["method_sha256"], gate.sha256_hex("ASBC Beer-4G"))
        self.assertEqual(abv["version_sha256"], gate.sha256_hex("Beer-4G"))
        self.assertEqual(abv["unit_sha256"], gate.sha256_hex("%ABV"))
        self.assertEqual(
            abv["source_sha256"],
            gate.sha256_hex(
                "https://oregonbrewlab.com/wp-content/uploads/2025/01/2025-OBL-Price-List.pdf"
            ),
        )
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["report_digest"], gate.GOLDEN_REPORT_DIGEST)

    def test_form_container_volume_and_cold_chain_gates(self) -> None:
        journal = gate.empty_journal()
        valid = next(item for item in gate.build_acceptance_fixture() if item["sample_id"] == "OBL-V-001")

        missing_form = deepcopy(valid)
        missing_form["sample_id"] = "OBL-LOCAL-FORM"
        missing_form["form_present"] = False
        missing_form["form_sample_name"] = ""
        missing_form["row_id"] = "LOCAL-FORM"
        self.assertEqual(gate.ingest_row(journal, missing_form)["code"], "FORM_CONTAINER_MISMATCH")

        mismatch = deepcopy(valid)
        mismatch["sample_id"] = "OBL-LOCAL-NAME"
        mismatch["form_sample_name"] = "OTHER"
        mismatch["container_label"] = "OBL-LOCAL-NAME"
        mismatch["row_id"] = "LOCAL-NAME"
        self.assertEqual(gate.ingest_row(journal, mismatch)["code"], "FORM_CONTAINER_MISMATCH")

        mason = deepcopy(valid)
        mason["sample_id"] = "OBL-LOCAL-MASON"
        mason["form_sample_name"] = "OBL-LOCAL-MASON"
        mason["container_label"] = "OBL-LOCAL-MASON"
        mason["analysis"] = "MICRO_UBA"
        mason["container_type"] = "mason_jar"
        mason["ice_pack"] = True
        mason["overnight"] = True
        mason["row_id"] = "LOCAL-MASON"
        self.assertEqual(gate.ingest_row(journal, mason)["code"], "FORM_CONTAINER_MISMATCH")

        short = deepcopy(valid)
        short["sample_id"] = "OBL-LOCAL-VOL"
        short["form_sample_name"] = "OBL-LOCAL-VOL"
        short["container_label"] = "OBL-LOCAL-VOL"
        short["volume_oz"] = 2.0
        short["row_id"] = "LOCAL-VOL"
        self.assertEqual(gate.ingest_row(journal, short)["code"], "INSUFFICIENT_VOLUME")

        warm = deepcopy(valid)
        warm["sample_id"] = "OBL-LOCAL-WARM"
        warm["form_sample_name"] = "OBL-LOCAL-WARM"
        warm["container_label"] = "OBL-LOCAL-WARM"
        warm["analysis"] = "VDK"
        warm["container_type"] = "unopened_bottle"
        warm["volume_oz"] = 12.0
        warm["ice_pack"] = False
        warm["overnight"] = True
        warm["row_id"] = "LOCAL-WARM"
        self.assertEqual(gate.ingest_row(journal, warm)["code"], "WARM_MICRO_VDK")
        self.assertEqual(len(journal["jobs"]), 0)

    def test_public_volume_thresholds(self) -> None:
        self.assertEqual(gate.min_volume_oz("ABV"), 4.0)
        self.assertEqual(gate.min_volume_oz("IBU"), 4.0)
        self.assertEqual(gate.min_volume_oz("VDK"), 12.0)
        self.assertEqual(gate.min_volume_oz("FCR"), 12.0)
        self.assertEqual(gate.min_volume_oz("VDK", additional_testing=True), 24.0)
        self.assertEqual(gate.min_volume_oz("MICRO_UBA"), 4.0)

    def test_replay_is_idempotent_and_adds_no_jobs(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["report_digest"], second["report_digest"])
        self.assertEqual(first["catalog_sha256"], second["catalog_sha256"])
        self.assertEqual(len(first["audit_sha256"]), 64)

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["jobs"]), 96)
        self.assertEqual(len(journal["holds"]), 24)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_job_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["job_count"], 96)
        self.assertEqual(replay["hold_count"], 24)
        self.assertEqual(replay["replay_noops"], 96)

    def test_reports_stay_staged_until_named_human_release(self) -> None:
        journal = gate.empty_journal()
        row = next(item for item in gate.build_acceptance_fixture() if item["sample_id"] == "OBL-V-001")
        gate.ingest_row(journal, row)
        job_id = next(iter(journal["jobs"]))
        record = journal["jobs"][job_id]
        self.assertEqual(record["state"], "READY")
        self.assertEqual(gate.report_status(record), "STAGED")
        self.assertEqual(record["report"]["status"], "STAGED")

        autonomous = gate.release_report(journal, job_id, actor_role="SYSTEM", actor="bot")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(record["released"])
        self.assertEqual(record["report_status"], "STAGED")

        unnamed = gate.release_report(journal, job_id, actor_role="RELEASER", actor="")
        self.assertEqual(unnamed["code"], "AUTONOMOUS_RELEASE_DENIED")

        human = gate.release_report(journal, job_id, actor_role="RELEASER", actor="dana-reviewer")
        self.assertTrue(human["ok"])
        self.assertEqual(record["report_status"], "RELEASED")
        self.assertEqual(record["released_by"], "dana-reviewer")
        again = gate.release_report(journal, job_id, actor_role="RELEASER", actor="dana-reviewer")
        self.assertTrue(again["ok"])
        self.assertTrue(again["duplicate"])

    def test_no_live_interfaces_or_production_writes(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertFalse(result["autonomous_certification"])
        self.assertFalse(result["autonomous_release"])
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["pre_sale_transport"], "NONE")
        self.assertEqual(result["cash_usd"], 0)
        self.assertTrue(all(item["live"] is False for item in result["notifications"]))
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )


if __name__ == "__main__":
    unittest.main()
