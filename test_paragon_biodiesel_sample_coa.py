#!/usr/bin/env python3
"""Binary acceptance for paragon-biodiesel-sample-coa-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter

import paragon_biodiesel_sample_coa as gate


class ParagonBiodieselSampleCoaTests(unittest.TestCase):
    def test_acceptance_fixture_is_120_frozen_rows(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 120)
        sample_ids = [row["sample_id"] for row in rows]
        self.assertEqual([row["row_id"] for row in rows[:100]], [f"R{i:03d}" for i in range(1, 101)])
        self.assertEqual(sample_ids[:100], [f"PBD-V{i:03d}" for i in range(1, 101)])
        self.assertEqual([item for item in sample_ids if item.startswith("PBD-C")], [f"PBD-C{i:02d}" for i in range(1, 6)])
        self.assertEqual([item for item in sample_ids if item.startswith("PBD-S")], [f"PBD-S{i:02d}" for i in range(1, 6)])
        self.assertEqual(sample_ids[110:115], [f"PBD-V{i:03d}" for i in range(1, 6)])
        self.assertEqual(sorted(sample_ids[115:]), sorted(gate.OOS_CASES))

    def test_pass_contract_exact_counts_and_signed_hashes(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.GOLDEN_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["hold_code_set"], sorted(gate.HOLD_CODES))
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["golden_set_sha256"], gate.GOLDEN_SET_SHA256)
        self.assertEqual(len(result["audit_sha256"]), 64)
        self.assertEqual(len(result["golden_set_sha256"]), 64)

    def test_twenty_exceptions_use_expected_hold_codes(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 20)
        counts = Counter(item["code"] for item in result["holds"])
        self.assertEqual(counts["HOLD_INCOMPLETE_COC"], 5)
        self.assertEqual(counts["HOLD_INCOMPLETE_SDS"], 5)
        self.assertEqual(counts["HOLD_DUPLICATE_ID"], 5)
        self.assertEqual(counts["HOLD_OOS"], 5)
        coc = sorted(item["row_id"] for item in result["holds"] if item["code"] == "HOLD_INCOMPLETE_COC")
        sds = sorted(item["row_id"] for item in result["holds"] if item["code"] == "HOLD_INCOMPLETE_SDS")
        dupes = sorted(item["row_id"] for item in result["holds"] if item["code"] == "HOLD_DUPLICATE_ID")
        oos = sorted(item["sample_id"] for item in result["holds"] if item["code"] == "HOLD_OOS")
        self.assertEqual(coc, ["C01", "C02", "C03", "C04", "C05"])
        self.assertEqual(sds, ["S01", "S02", "S03", "S04", "S05"])
        self.assertEqual(dupes, ["D01", "D02", "D03", "D04", "D05"])
        self.assertEqual(oos, sorted(gate.OOS_CASES))

    def test_one_hundred_valid_accession_exactly_once(self) -> None:
        result = gate.run_gate()
        valid = [item for item in result["accessions"] if item["sample_id"].startswith("PBD-V")]
        self.assertEqual(len(valid), 100)
        self.assertEqual(len({item["sample_id"] for item in valid}), 100)
        self.assertEqual(len({item["accession_id"] for item in valid}), 100)
        self.assertEqual(result["duplicate_accessions"], 0)
        self.assertEqual(len(set(result["accession_ids"])), 105)
        for item in valid:
            self.assertEqual(item["route"], "B6_B20_D7467_PANEL")
            self.assertEqual(item["spec_id"], "ASTM D7467")
            self.assertEqual(item["methods"], list(gate.PANEL))
            self.assertEqual(item["result_state"], "IN_SPEC")
            self.assertTrue(item["released"])
            self.assertEqual(item["released_by"], gate.HUMAN_ACTOR)
            self.assertEqual(item["coa"]["status"], "RELEASED")

    def test_values_units_qualifiers_report_fields_match_golden_set(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["golden_set"]), 100)
        self.assertEqual(gate.sha256_hex(result["golden_set"]), gate.GOLDEN_SET_SHA256)
        first = next(item for item in result["golden_set"] if item["sample_id"] == "PBD-V001")
        analytes = {row["analyte"]: row for row in first["values"]}
        self.assertEqual(analytes["fame"]["unit"], "% vol")
        self.assertEqual(analytes["flash_point"]["unit"], "deg_C")
        self.assertEqual(analytes["viscosity_40c"]["unit"], "mm2_s")
        self.assertEqual(analytes["sulfur"]["unit"], "mg_kg")
        self.assertEqual(analytes["acid_number"]["unit"], "mg_KOH_g")
        self.assertEqual(analytes["water_sediment"]["unit"], "% vol")
        self.assertEqual(analytes["oxidation_stability"]["unit"], "h")
        for row in first["values"]:
            self.assertEqual(row["qualifier"], "")
            self.assertGreater(row["value"], 0)
        self.assertEqual(first["report_fields"]["product"], "B6-B20 biodiesel blend")
        self.assertEqual(first["report_fields"]["spec_id"], "ASTM D7467")
        self.assertEqual(first["report_fields"]["spec_revision"], "D7467-23")
        self.assertEqual(len(first["source_sha256"]), 64)
        self.assertEqual(result["source_hashes"]["PBD-V001"], first["source_sha256"])

    def test_oos_rows_hold_after_results_and_do_not_release(self) -> None:
        result = gate.run_gate()
        for sample_id, case in gate.OOS_CASES.items():
            item = next(rec for rec in result["accessions"] if rec["sample_id"] == sample_id)
            self.assertEqual(item["review_hold"], "HOLD_OOS")
            self.assertEqual(item["coa_status"], "HOLD_OOS")
            self.assertFalse(item["released"])
            self.assertIsNone(item["coa"])
            hit = next(row for row in item["results"] if row["method_id"] == case["method"])
            self.assertEqual(hit["qualifier"], "OOS")
            self.assertEqual(hit["value"], case["value"])

    def test_autonomous_release_denied_named_human_required(self) -> None:
        result = gate.run_gate()
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )
        self.assertEqual(sum(1 for item in result["human_release_effects"] if item.get("ok")), 100)
        denied = [item for item in result["human_release_effects"] if not item.get("ok")]
        self.assertEqual(len(denied), 5)
        self.assertEqual({item["code"] for item in denied}, {"HOLD_OOS"})
        released_by = {item["released_by"] for item in result["accessions"] if item["released"]}
        self.assertEqual(released_by, {gate.HUMAN_ACTOR})
        journal = gate.empty_journal()
        gate.ingest_row(journal, gate.build_acceptance_fixture()[0])
        acc_id = next(iter(journal["accessions"]))
        gate.import_simulated_results(journal, acc_id)
        blank = gate.release_coa(journal, acc_id, actor_role="RELEASER", actor="")
        self.assertFalse(blank["ok"])
        self.assertEqual(blank["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(journal["accessions"][acc_id]["released"])

    def test_replay_is_idempotent_and_adds_zero_accessions(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["golden_set_sha256"], second["golden_set_sha256"])
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(gate.sha256_hex(first["audit"]), first["audit_sha256"])
        self.assertEqual(gate.sha256_hex(first["golden_set"]), first["golden_set_sha256"])

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 105)
        self.assertEqual(len(journal["holds"]), 15)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["accession_count"], 105)
        self.assertEqual(replay["hold_count"], 15)
        self.assertEqual(replay["replay_noops"], 105)

    def test_b6_b20_panel_methods_are_d7467_specific(self) -> None:
        result = gate.run_gate()
        wine = next(item for item in result["accessions"] if item["sample_id"] == "PBD-V002")
        self.assertEqual(wine["blend_grade"], "B10")
        self.assertEqual(wine["lane"], "B6-B20")
        self.assertEqual(
            wine["methods"],
            ["D7371", "D93", "D445", "D5453", "D664", "D2709", "EN15751"],
        )
        fame = next(row for row in wine["results"] if row["analyte"] == "fame")
        self.assertGreaterEqual(fame["value"], 6.0)
        self.assertLessEqual(fame["value"], 20.0)

    def test_no_live_adapters_production_writes_or_outreach(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["qc_decisions"], 0)
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["billing_writes"], 0)
        self.assertEqual(result["outreach"], 0)
        self.assertFalse(result["autonomous_certification"])
        self.assertFalse(result["autonomous_release"])
        self.assertEqual(result["audit"]["adapters"]["production_write"], "NOT_SENT")
        self.assertEqual(result["audit"]["adapters"]["outreach"], "NOT_SENT")
        for item in result["accessions"]:
            self.assertEqual(item["interface_state"], "SIMULATED")
            self.assertFalse(item["interface_live"])
            self.assertEqual(item["adapters"]["instrument"], "SIMULATED_READ_ONLY")


if __name__ == "__main__":
    unittest.main()
