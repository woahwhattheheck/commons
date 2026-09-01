#!/usr/bin/env python3
"""Acceptance tests for apl-fda-polymer-compliance-dossier-lims-01."""

from __future__ import annotations

import unittest
from copy import deepcopy

import apl_fda_polymer_compliance_dossier_lims as gate


class AplFdaPolymerComplianceDossierLimsTests(unittest.TestCase):
    def test_frozen_fixture_is_100_with_exact_80_20_oracle(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 100)
        self.assertEqual(
            sum(row["expected_state"] == "READY" for row in rows), 80
        )
        self.assertEqual(
            sum(row["expected_state"] == "HOLD" for row in rows), 20
        )
        counts = {
            code: sum(row["expected_hold"] == code for row in rows)
            for code in gate.HOLD_CODES
        }
        self.assertEqual(counts, gate.HOLD_COUNTS)
        self.assertEqual(
            gate.fixture_sha256(rows), gate.GOLDEN_FIXTURE_SHA256
        )

    def test_contract_is_exactly_80_ready_and_20_hold(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 100)
        self.assertEqual(result["ready"], 80)
        self.assertEqual(result["holds"], 20)
        self.assertEqual(result["accessions"], 80)
        self.assertEqual(result["work_orders"], 80)
        self.assertEqual(result["results"], 80)
        self.assertEqual(result["dossiers_staged"], 80)
        self.assertEqual(result["dossiers_released"], 0)
        self.assertEqual(result["hold_counts"], gate.HOLD_COUNTS)

    def test_every_predetermined_hold_schedules_nothing(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {
            item["row_id"]: item for item in result["hold_records"]
        }
        self.assertEqual(len(holds), 20)
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["row_id"]]
            self.assertEqual(hold["code"], row["expected_hold"])
            self.assertEqual(hold["state"], "HOLD")
            self.assertEqual(hold["accessions_created"], 0)
            self.assertEqual(hold["work_orders_created"], 0)
            self.assertEqual(hold["results_created"], 0)
            self.assertEqual(hold["dossiers_staged"], 0)
            self.assertEqual(hold["dossiers_released"], 0)

    def test_sample_lot_matrix_intended_use_lineage_stays_bound(
        self,
    ) -> None:
        rows = gate.build_acceptance_fixture()
        by_submission = {
            row["submission_id"]: row
            for row in rows
            if row["expected_state"] == "READY"
        }
        result = gate.run_gate(rows)
        self.assertEqual(len(result["accession_records"]), 80)
        for accession in result["accession_records"]:
            source = by_submission[accession["submission_id"]]
            self.assertEqual(accession["intended_use_id"], source["intended_use_id"])
            self.assertEqual(accession["lot_id"], source["lot_id"])
            self.assertEqual(
                accession["regulatory_matrix_id"], source["regulatory_matrix_id"]
            )
            self.assertEqual(
                accession["regulatory_matrix_doc_id"],
                source["regulatory_matrix_doc_id"],
            )
            self.assertEqual(accession["package_id"], source["package_id"])
            self.assertEqual(accession["container_id"], source["container_id"])
            self.assertEqual(accession["sample_id"], source["sample_id"])
            self.assertEqual(
                accession["source_sha256"],
                source["golden_hashes"]["source_sha256"],
            )

    def test_routine_nonroutine_method_instrument_and_raw_result_hashes_match(
        self,
    ) -> None:
        result = gate.run_gate()
        self.assertEqual(
            result["method_class_counts"],
            {"ROUTINE": 40, "NON_ROUTINE": 40},
        )
        work_by_id = {
            item["work_order_id"]: item
            for item in result["work_order_records"]
        }
        dossier_by_result = {
            item["result_id"]: item for item in result["dossier_records"]
        }
        for raw in result["result_records"]:
            work = work_by_id[raw["work_order_id"]]
            dossier = dossier_by_result[raw["result_id"]]
            spec = gate.METHOD_CATALOG[work["method_class"]]
            self.assertEqual(work["method"], spec["method"])
            self.assertEqual(work["method_version"], spec["version"])
            self.assertEqual(raw["unit"], spec["unit"])
            self.assertEqual(raw["qualifier"], spec["qualifier"])
            self.assertEqual(work["instrument_id"], spec["instrument"])
            self.assertEqual(raw["instrument_id"], spec["instrument"])
            self.assertEqual(
                raw["value_sha256"],
                gate.sha256_hex({"value": raw["value"]}),
            )
            self.assertEqual(
                raw["unit_sha256"],
                gate.sha256_hex({"unit": raw["unit"]}),
            )
            self.assertEqual(
                raw["qualifier_sha256"],
                gate.sha256_hex({"qualifier": raw["qualifier"]}),
            )
            self.assertEqual(
                dossier["source_sha256"], raw["source_sha256"]
            )
            self.assertEqual(
                dossier["method_sha256"], raw["method_sha256"]
            )
            self.assertEqual(
                dossier["result_sha256"], raw["result_sha256"]
            )
            self.assertEqual(
                dossier["value_sha256"], raw["value_sha256"]
            )
            self.assertEqual(
                dossier["unit_sha256"], raw["unit_sha256"]
            )
            self.assertEqual(
                dossier["qualifier_sha256"],
                raw["qualifier_sha256"],
            )
            self.assertEqual(len(dossier["dossier_sha256"]), 64)

    def test_replay_adds_zero_and_changed_payload_conflicts_atomically(
        self,
    ) -> None:
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_submission(journal, row)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(
            replay,
            {
                "added_accessions": 0,
                "added_work_orders": 0,
                "added_results": 0,
                "added_dossiers": 0,
                "added_holds": 0,
                "replay_noops": 100,
                "replay_conflicts": 0,
            },
        )
        changed = deepcopy(rows[0])
        changed["result_value"] = 999.25
        before = gate.canonical_json(journal)
        conflict = gate.ingest_submission(journal, changed)
        self.assertEqual(conflict["kind"], "REPLAY_CONFLICT")
        self.assertEqual(conflict["code"], "REPLAY_PAYLOAD_CONFLICT")
        self.assertEqual(gate.canonical_json(journal), before)

    def test_release_requires_authoritative_named_human(self) -> None:
        journal = gate.empty_journal()
        ready = gate.ingest_submission(
            journal, gate.build_acceptance_fixture()[0]
        )
        dossier_id = ready["dossier_id"]
        before = gate.canonical_json(journal)
        denied = gate.release_dossier(
            journal, dossier_id, reviewer_id="SYSTEM"
        )
        self.assertEqual(
            denied, {"ok": False, "code": "AUTONOMOUS_RELEASE_DENIED"}
        )
        self.assertEqual(gate.canonical_json(journal), before)
        unknown = gate.release_dossier(
            journal, dossier_id, reviewer_id="self-asserted-reviewer"
        )
        self.assertEqual(
            unknown, {"ok": False, "code": "UNAUTHORIZED_REVIEWER"}
        )
        self.assertEqual(gate.canonical_json(journal), before)
        released = gate.release_dossier(
            journal,
            dossier_id,
            reviewer_id="SYN-HUMAN-APL-REVIEWER-01",
        )
        self.assertTrue(released["ok"])
        self.assertEqual(released["status"], "RELEASED")
        self.assertEqual(
            journal["dossiers"][dossier_id]["released_by"]["display_name"],
            "Synthetic Named Reviewer One",
        )

    def test_invalid_and_non_synthetic_rows_fail_closed_without_mutation(
        self,
    ) -> None:
        journal = gate.empty_journal()
        baseline = gate.canonical_json(journal)
        for malformed in ("garbage", [1], 1, True, None):
            with self.subTest(malformed=repr(malformed)):
                result = gate.ingest_submission(journal, malformed)  # type: ignore[arg-type]
                self.assertEqual(result["kind"], "REJECT")
                self.assertEqual(result["code"], "REJECT_INVALID_INPUT")
                self.assertEqual(gate.canonical_json(journal), baseline)
        non_synthetic = deepcopy(gate.build_acceptance_fixture()[0])
        non_synthetic["synthetic"] = False
        held = gate.ingest_submission(journal, non_synthetic)
        self.assertEqual(held["kind"], "HOLD")
        self.assertEqual(held["code"], "HOLD_TRUTH_BOUNDARY")
        self.assertEqual(len(journal["accessions"]), 0)
        self.assertEqual(len(journal["dossiers"]), 0)

    def test_source_is_synthetic_read_only_and_no_live_side_effects(
        self,
    ) -> None:
        adapter = gate.SyntheticReadOnlySubmissionAdapter(
            gate.build_acceptance_fixture()
        )
        self.assertEqual(adapter.mode, "SYNTHETIC_READ_ONLY")
        self.assertFalse(adapter.live)
        self.assertEqual(adapter.writes, 0)
        with self.assertRaises(RuntimeError):
            adapter.write({"row_id": "nope"})
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SYNTHETIC_READ_ONLY")
        self.assertEqual(result["source_writes"], 0)
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["automatic_releases"], 0)
        self.assertEqual(result["pre_sale_transport"], "NONE")
        self.assertEqual(result["cash_usd"], 0)
        self.assertEqual(result["truth_gate"], "HOLD / BUILD-AND-VERIFY")

    def test_repeated_runs_and_frozen_hashes_are_identical(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(
            first["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256
        )
        self.assertEqual(
            first["manifest_sha256"], gate.GOLDEN_MANIFEST_SHA256
        )
        self.assertEqual(first["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(
            first["fixture_sha256"], second["fixture_sha256"]
        )
        self.assertEqual(
            first["manifest_sha256"], second["manifest_sha256"]
        )
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])


if __name__ == "__main__":
    unittest.main()
