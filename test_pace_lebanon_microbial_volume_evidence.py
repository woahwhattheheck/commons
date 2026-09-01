#!/usr/bin/env python3
"""Binary acceptance for pace-lebanon-microbial-volume-evidence-lims-01."""

from __future__ import annotations

import unittest

import pace_lebanon_microbial_volume_evidence as gate


class PaceLebanonMicrobialVolumeEvidenceTests(unittest.TestCase):
    def test_frozen_fixture_is_120_with_exact_exception_split(self) -> None:
        rows = gate.build_acceptance_fixture()
        counts: dict[str | None, int] = {}
        for row in rows:
            counts[row["exception_type"]] = counts.get(row["exception_type"], 0) + 1
        self.assertEqual(len(rows), 120)
        self.assertEqual(
            counts,
            {
                None: 90,
                "DUPLICATE_ID": 8,
                "MISSING_METHOD_SPEC_MATRIX": 7,
                "WRONG_ROUTE": 5,
                "INCUBATION_WINDOW": 5,
                "QC_CONTROL_FAILURE": 5,
            },
        )

    def test_pass_contract_is_exact_90_ready_30_hold(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 120)
        self.assertEqual(result["ready"], 90)
        self.assertEqual(result["holds"], 30)
        self.assertEqual(result["jobs"], 90)
        self.assertEqual(result["reports_staged"], 90)
        self.assertEqual(result["reports_released"], 0)

    def test_all_hold_reasons_are_exact_and_create_no_output(self) -> None:
        result = gate.run_gate()
        self.assertEqual(
            result["hold_counts"],
            {
                "HOLD_DUPLICATE_SUBMISSION_ID": 8,
                "HOLD_MISSING_METHOD_SPEC_MATRIX": 7,
                "HOLD_ROUTE_MISMATCH": 5,
                "HOLD_INCUBATION_WINDOW": 5,
                "HOLD_QC_CONTROL_FAILURE": 5,
            },
        )
        for hold in result["hold_records"]:
            self.assertEqual(hold["state"], "HOLD")
            self.assertEqual(hold["jobs_created"], 0)
            self.assertEqual(hold["results_created"], 0)
            self.assertEqual(hold["reports_staged"], 0)
            self.assertFalse(hold["released"])

    def test_route_method_matrix_and_specification_stay_bound(self) -> None:
        result = gate.run_gate()
        self.assertEqual(
            result["route_counts"],
            {"MICROBIAL_LIMITS": 30, "STERILITY": 30, "CCIT": 30},
        )
        for submission in result["submissions"]:
            route = gate.ROUTES[submission["route"]]
            self.assertEqual(submission["method"], route["method"])
            self.assertEqual(submission["matrix"], route["matrix"])
            self.assertEqual(submission["specification"], route["specification"])
            self.assertEqual(submission["unit"], route["unit"])

    def test_incubation_timepoints_and_duration_never_shorten(self) -> None:
        result = gate.run_gate()
        rush_jobs = 0
        for job in result["job_records"]:
            route = gate.ROUTES[job["route"]]
            self.assertEqual(job["minimum_duration_hours"], route["duration_hours"])
            self.assertGreaterEqual(
                job["planned_duration_hours"], job["minimum_duration_hours"]
            )
            self.assertEqual(job["timepoints_hours"], route["timepoints_hours"])
            if job["rush"]:
                rush_jobs += 1
                self.assertEqual(
                    job["planned_duration_hours"], job["minimum_duration_hours"]
                )
        self.assertEqual(rush_jobs, 18)

    def test_count_unit_timepoint_method_and_source_hashes_are_preserved(self) -> None:
        result = gate.run_gate()
        jobs = {item["job_id"]: item for item in result["job_records"]}
        for report in result["report_records"]:
            job = jobs[report["job_id"]]
            self.assertEqual(report["source_hash"], job["result"]["source_hash"])
            self.assertEqual(report["method_hash"], job["result"]["method_hash"])
            self.assertEqual(report["result_hash"], gate.sha256_hex(job["result"]))
            self.assertIsNotNone(job["result"]["count"])
            self.assertTrue(job["result"]["unit"])
            self.assertTrue(job["result"]["timepoints_hours"])
            self.assertEqual(len(report["source_hash"]), 64)
            self.assertEqual(len(report["method_hash"]), 64)
            self.assertEqual(len(report["result_hash"]), 64)

    def test_reports_stay_staged_until_named_human_release(self) -> None:
        result = gate.run_gate()
        self.assertTrue(
            all(item["status"] == "STAGED" for item in result["report_records"])
        )
        self.assertTrue(
            all(not item["released"] for item in result["report_records"])
        )
        self.assertTrue(
            all(
                item["code"] == "AUTONOMOUS_RELEASE_DENIED"
                for item in result["autonomous_release_effects"]
            )
        )

        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        report_id = sorted(journal["reports"])[0]
        denied = gate.release_report(
            journal, report_id, actor_role="SYSTEM", actor="automation"
        )
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "AUTONOMOUS_RELEASE_DENIED")
        released = gate.release_report(
            journal,
            report_id,
            actor_role=gate.HUMAN_REVIEWER_ROLE,
            actor="named-reviewer",
        )
        self.assertTrue(released["ok"])
        self.assertEqual(journal["reports"][report_id]["status"], "RELEASED")
        self.assertEqual(
            journal["reports"][report_id]["released_by"], "named-reviewer"
        )

    def test_replay_creates_zero_records_or_reports(self) -> None:
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_row(journal, row)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(
            replay,
            {
                "added_submissions": 0,
                "added_jobs": 0,
                "added_holds": 0,
                "added_reports": 0,
                "replay_noops": 120,
            },
        )
        self.assertEqual(len(journal["submissions"]), 90)
        self.assertEqual(len(journal["jobs"]), 90)
        self.assertEqual(len(journal["holds"]), 30)
        self.assertEqual(len(journal["reports"]), 90)

    def test_repeated_runs_have_identical_manifests_and_audits(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(len(first["manifest_sha256"]), 64)
        self.assertEqual(len(first["audit_sha256"]), 64)

    def test_no_live_adapter_production_write_or_automatic_release(self) -> None:
        result = gate.run_gate()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED_READ_ONLY")
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["automatic_releases"], 0)
        self.assertFalse(result["autonomous_release"])
        self.assertEqual(result["pre_sale_transport"], "NONE")
        self.assertEqual(result["cash_usd"], 0)
        self.assertEqual(result["truth_gate"], "HOLD / BUILD-AND-VERIFY")


if __name__ == "__main__":
    unittest.main()
