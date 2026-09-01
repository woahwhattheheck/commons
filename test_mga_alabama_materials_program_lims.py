#!/usr/bin/env python3
"""Acceptance tests for mga-alabama-materials-program-lims-01."""

from __future__ import annotations

import unittest
from copy import deepcopy

import mga_alabama_materials_program_lims as gate


class MgaAlabamaMaterialsProgramLimsTests(unittest.TestCase):
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
        self.assertEqual(result["specimens"], 80)
        self.assertEqual(result["jobs"], 80)
        self.assertEqual(result["jobs_scheduled"], 80)
        self.assertEqual(result["results"], 80)
        self.assertEqual(result["packets_staged"], 80)
        self.assertEqual(result["packets_released"], 0)
        self.assertEqual(result["hold_counts"], gate.HOLD_COUNTS)

    def test_every_predetermined_hold_schedules_nothing(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {
            item["row_id"]: item for item in result["hold_records"]
        }
        self.assertEqual(len(holds), 20)
        scheduled_specimens = {
            item["specimen_id"] for item in result["job_records"]
        }
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["row_id"]]
            self.assertEqual(hold["code"], row["expected_hold"])
            self.assertEqual(hold["state"], "HOLD")
            self.assertEqual(hold["jobs_created"], 0)
            self.assertEqual(hold["jobs_scheduled"], 0)
            self.assertEqual(hold["results_created"], 0)
            self.assertEqual(hold["packets_staged"], 0)
            self.assertEqual(hold["packets_released"], 0)
            if hold["code"] != "HOLD_DUPLICATE_SPECIMEN":
                self.assertNotIn(row["specimen_id"], scheduled_specimens)

    def test_ready_lineage_traces_specimen_method_instrument_raw_packet(
        self,
    ) -> None:
        rows = gate.build_acceptance_fixture()
        by_specimen = {
            row["specimen_id"]: row
            for row in rows
            if row["expected_state"] == "READY"
        }
        result = gate.run_gate(rows)
        self.assertEqual(len(result["specimen_records"]), 80)
        job_by_specimen = {
            item["specimen_id"]: item for item in result["job_records"]
        }
        result_by_job = {
            item["job_id"]: item for item in result["result_records"]
        }
        packet_by_specimen = {
            item["specimen_id"]: item for item in result["packet_records"]
        }
        for specimen in result["specimen_records"]:
            source = by_specimen[specimen["specimen_id"]]
            job = job_by_specimen[specimen["specimen_id"]]
            raw = result_by_job[job["job_id"]]
            packet = packet_by_specimen[specimen["specimen_id"]]
            spec = gate.METHOD_CATALOG[source["material_class"]]
            self.assertEqual(specimen["request_id"], source["request_id"])
            self.assertEqual(specimen["coupon_id"], source["coupon_id"])
            self.assertEqual(job["method"], spec["method"])
            self.assertEqual(job["method_version"], spec["version"])
            self.assertEqual(job["instrument_id"], spec["instrument_id"])
            self.assertEqual(job["fixture_id"], spec["fixture_id"])
            self.assertEqual(raw["value"], source["result_value"])
            self.assertEqual(raw["unit"], spec["unit"])
            self.assertEqual(packet["specimen_id"], specimen["specimen_id"])
            self.assertEqual(packet["method"], job["method"])
            self.assertEqual(packet["instrument_id"], job["instrument_id"])
            self.assertEqual(packet["fixture_id"], job["fixture_id"])
            self.assertEqual(packet["result_id"], raw["result_id"])
            self.assertEqual(
                packet["value_sha256"],
                gate.sha256_hex({"value": raw["value"]}),
            )
            self.assertEqual(
                packet["unit_sha256"],
                gate.sha256_hex({"unit": raw["unit"]}),
            )
            self.assertEqual(len(packet["packet_sha256"]), 64)

    def test_method_material_binding_and_raw_hashes_match(self) -> None:
        result = gate.run_gate()
        self.assertEqual(
            result["material_class_counts"],
            {
                "POLYMER": 20,
                "METAL": 20,
                "COMPOSITE": 20,
                "ELASTOMER": 20,
            },
        )
        job_by_id = {item["job_id"]: item for item in result["job_records"]}
        packet_by_result = {
            item["result_id"]: item for item in result["packet_records"]
        }
        for raw in result["result_records"]:
            job = job_by_id[raw["job_id"]]
            packet = packet_by_result[raw["result_id"]]
            self.assertEqual(raw["instrument_id"], job["instrument_id"])
            self.assertEqual(raw["fixture_id"], job["fixture_id"])
            self.assertEqual(
                raw["value_sha256"],
                gate.sha256_hex({"value": raw["value"]}),
            )
            self.assertEqual(
                raw["unit_sha256"],
                gate.sha256_hex({"unit": raw["unit"]}),
            )
            self.assertEqual(packet["source_sha256"], raw["source_sha256"])
            self.assertEqual(packet["method_sha256"], raw["method_sha256"])
            self.assertEqual(packet["result_sha256"], raw["result_sha256"])

    def test_replay_adds_zero_jobs_and_changed_payload_conflicts(
        self,
    ) -> None:
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_program(journal, row)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(
            replay,
            {
                "added_specimens": 0,
                "added_jobs": 0,
                "added_results": 0,
                "added_packets": 0,
                "added_holds": 0,
                "replay_noops": 100,
                "replay_conflicts": 0,
            },
        )
        changed = deepcopy(rows[0])
        changed["result_value"] = 999.25
        before = gate.canonical_json(journal)
        conflict = gate.ingest_program(journal, changed)
        self.assertEqual(conflict["kind"], "REPLAY_CONFLICT")
        self.assertEqual(conflict["code"], "REPLAY_PAYLOAD_CONFLICT")
        self.assertEqual(gate.canonical_json(journal), before)

    def test_release_requires_authoritative_named_human(self) -> None:
        journal = gate.empty_journal()
        ready = gate.ingest_program(
            journal, gate.build_acceptance_fixture()[0]
        )
        packet_id = ready["packet_id"]
        before = gate.canonical_json(journal)
        denied = gate.release_packet(
            journal, packet_id, reviewer_id="SYSTEM"
        )
        self.assertEqual(
            denied, {"ok": False, "code": "AUTONOMOUS_RELEASE_DENIED"}
        )
        self.assertEqual(gate.canonical_json(journal), before)
        unknown = gate.release_packet(
            journal, packet_id, reviewer_id="self-asserted-reviewer"
        )
        self.assertEqual(
            unknown, {"ok": False, "code": "UNAUTHORIZED_REVIEWER"}
        )
        self.assertEqual(gate.canonical_json(journal), before)
        released = gate.release_packet(
            journal,
            packet_id,
            reviewer_id="SYN-HUMAN-MGA-REVIEWER-01",
        )
        self.assertTrue(released["ok"])
        self.assertEqual(released["status"], "RELEASED")
        self.assertEqual(
            journal["packets"][packet_id]["released_by"]["display_name"],
            "Synthetic Named Reviewer One",
        )

    def test_invalid_and_non_synthetic_rows_fail_closed_without_mutation(
        self,
    ) -> None:
        journal = gate.empty_journal()
        baseline = gate.canonical_json(journal)
        for malformed in ("garbage", [1], 1, True, None):
            with self.subTest(malformed=repr(malformed)):
                result = gate.ingest_program(journal, malformed)  # type: ignore[arg-type]
                self.assertEqual(result["kind"], "REJECT")
                self.assertEqual(result["code"], "REJECT_INVALID_INPUT")
                self.assertEqual(gate.canonical_json(journal), baseline)
        non_synthetic = deepcopy(gate.build_acceptance_fixture()[0])
        non_synthetic["synthetic"] = False
        held = gate.ingest_program(journal, non_synthetic)
        self.assertEqual(held["kind"], "HOLD")
        self.assertEqual(held["code"], "HOLD_TRUTH_BOUNDARY")
        self.assertEqual(len(journal["jobs"]), 0)
        self.assertEqual(len(journal["packets"]), 0)

    def test_source_is_synthetic_read_only_and_no_live_side_effects(
        self,
    ) -> None:
        adapter = gate.SyntheticReadOnlyProgramAdapter(
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
