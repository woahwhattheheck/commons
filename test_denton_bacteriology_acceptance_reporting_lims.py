#!/usr/bin/env python3
"""Binary acceptance for denton-bacteriology-acceptance-reporting-lims-01."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import denton_bacteriology_acceptance_reporting_lims as gate


class DentonBacteriologyAcceptanceTests(unittest.TestCase):
    def test_frozen_fixture_is_200_with_exact_exception_split(self) -> None:
        rows = gate.build_acceptance_fixture()
        counts: dict[str | None, int] = {}
        for row in rows:
            counts[row["exception_type"]] = counts.get(row["exception_type"], 0) + 1
        self.assertEqual(len(rows), 200)
        self.assertEqual(
            counts,
            {
                None: 160,
                "MISSING_ACCOUNT_PWS": 8,
                "ABSENT_CUSTODY": 8,
                "EXPIRED_BOTTLE": 6,
                "TEMPERATURE_HOLD_TIME": 8,
                "DUPLICATE_SAMPLE_ID": 5,
                "MISMATCHED_REPORT_FORM": 5,
            },
        )

    def test_pass_contract_is_exact_160_accessioned_40_hold(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 200)
        self.assertEqual(result["accessioned"], 160)
        self.assertEqual(result["holds"], 40)
        self.assertEqual(result["worksheets"], 160)
        self.assertEqual(result["reports_staged"], 160)
        self.assertEqual(result["reports_released"], 0)

    def test_all_hold_reasons_are_exact_and_create_no_output(self) -> None:
        result = gate.run_gate()
        self.assertEqual(
            result["hold_counts"],
            {
                "MISSING_ACCOUNT_PWS": 8,
                "ABSENT_CUSTODY": 8,
                "EXPIRED_BOTTLE": 6,
                "TEMPERATURE_HOLD_TIME": 8,
                "DUPLICATE_SAMPLE_ID": 5,
                "MISMATCHED_REPORT_FORM": 5,
            },
        )
        for hold in result["hold_records"]:
            self.assertEqual(hold["state"], "HOLD")
            self.assertEqual(hold["worksheets_created"], 0)
            self.assertEqual(hold["reports_created"], 0)
            self.assertFalse(hold["released"])

    def test_each_accession_has_expected_method_and_report_form(self) -> None:
        result = gate.run_gate()
        self.assertEqual(
            result["route_counts"],
            {"TCEQ_ECOLI_QUANT": 54, "TCEQ_AP": 53, "HPC": 53},
        )
        for submission in result["submissions"]:
            route = gate.ROUTES[submission["route"]]
            self.assertEqual(submission["method"], route["method"])
            self.assertEqual(submission["report_form"], route["report_form"])
            self.assertEqual(len(submission["source_hash"]), 64)

    def test_identities_never_cross_and_hashes_persist(self) -> None:
        result = gate.run_gate()
        samples = [item["sample_id"] for item in result["submissions"]]
        self.assertEqual(len(samples), len(set(samples)))
        self.assertEqual(result["unique_samples"], 160)
        self.assertEqual(result["identity_cross"], 0)
        accessioned_samples = {item["sample_id"] for item in result["submissions"]}
        for hold in result["hold_records"]:
            if hold["code"] != "DUPLICATE_SAMPLE_ID":
                self.assertNotIn(hold["sample_id"], accessioned_samples)
        reports = {item["report_id"]: item for item in result["report_records"]}
        for submission in result["submissions"]:
            report = reports[submission["report_id"]]
            self.assertEqual(report["source_hash"], submission["source_hash"])
            self.assertEqual(report["sample_id"], submission["sample_id"])

    def test_named_human_release_only(self) -> None:
        result = gate.run_gate()
        self.assertTrue(all(item["status"] == "STAGED" for item in result["report_records"]))
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
        self_asserted = gate.release_report(
            journal,
            report_id,
            actor_role=gate.HUMAN_REVIEWER_ROLE,
            actor="named-reviewer",
        )
        self.assertFalse(self_asserted["ok"])
        self.assertEqual(self_asserted["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertEqual(
            self_asserted["pre_state_hash"], self_asserted["post_state_hash"]
        )
        reviewer_id = "DENTON-QA-001"
        released = gate.release_report(
            journal,
            report_id,
            actor_role="SYSTEM",
            actor=journal["authoritative_reviewers"][reviewer_id]["display_name"],
            reviewer_id=reviewer_id,
        )
        self.assertTrue(released["ok"])
        self.assertEqual(journal["reports"][report_id]["status"], "RELEASED")
        self.assertEqual(
            journal["reports"][report_id]["released_by"],
            journal["authoritative_reviewers"][reviewer_id]["display_name"],
        )
        self.assertEqual(journal["reports"][report_id]["reviewer_id"], reviewer_id)

    def test_changed_payload_for_processed_row_is_conflict_not_replay(self) -> None:
        for field, replacement in (
            ("method", "SM-9221-PA"),
            ("bottle_expires", "2026-10-01"),
        ):
            with self.subTest(field=field):
                journal = gate.empty_journal()
                original = gate._base_row(1)
                self.assertEqual(gate.ingest_row(journal, original)["kind"], "ACCESSIONED")
                before = gate.journal_hash(journal)
                changed = dict(original)
                changed[field] = replacement
                effect = gate.ingest_row(journal, changed)
                self.assertEqual(effect["kind"], "PAYLOAD_DIGEST_CONFLICT")
                self.assertEqual(effect["pre_state_hash"], before)
                self.assertEqual(effect["post_state_hash"], before)
                self.assertEqual(gate.journal_hash(journal), before)
                self.assertEqual(len(journal["accessions"]), 1)

    def test_reused_submission_id_cannot_overwrite_lineage(self) -> None:
        journal = gate.empty_journal()
        original = gate._base_row(1)
        self.assertEqual(gate.ingest_row(journal, original)["kind"], "ACCESSIONED")
        before = gate.journal_hash(journal)
        replacement = gate._base_row(2)
        replacement["row_id"] = "DEN-201"
        replacement["submission_id"] = original["submission_id"]
        replacement["sample_id"] = "SMP-201"
        effect = gate.ingest_row(journal, replacement)
        self.assertEqual(effect["kind"], "SUBMISSION_LINEAGE_CONFLICT")
        self.assertEqual(effect["pre_state_hash"], before)
        self.assertEqual(effect["post_state_hash"], before)
        self.assertEqual(gate.journal_hash(journal), before)
        self.assertEqual(journal["submissions"][original["submission_id"]]["sample_id"], "SMP-001")
        self.assertEqual(len(journal["accessions"]), 1)
        self.assertEqual(len(journal["worksheets"]), 1)
        self.assertEqual(len(journal["reports"]), 1)

    def test_untrusted_numeric_date_and_account_inputs_hold_without_outputs(self) -> None:
        invalid_cases = (
            ("nan_temperature", "temperature_c", float("nan")),
            ("infinite_temperature", "temperature_c", float("inf")),
            ("negative_temperature", "temperature_c", -0.01),
            ("negative_hold_time", "hold_time_hours", -0.01),
            ("malformed_calendar_date", "collected_on", "2026-02-30"),
            ("noncanonical_calendar_date", "bottle_expires", "20260930"),
            ("non_scalar_account", "account_id", ["ACCT-01"]),
        )
        for name, field, replacement in invalid_cases:
            with self.subTest(name=name):
                journal = gate.empty_journal()
                row = gate._base_row(1)
                row[field] = replacement
                before = gate.journal_hash(journal)
                effect = gate.ingest_row(journal, row)
                self.assertEqual(effect["kind"], "HOLD")
                self.assertEqual(effect["pre_state_hash"], before)
                self.assertEqual(effect["post_state_hash"], gate.journal_hash(journal))
                self.assertNotEqual(effect["pre_state_hash"], effect["post_state_hash"])
                self.assertEqual(len(journal["accessions"]), 0)
                self.assertEqual(len(journal["worksheets"]), 0)
                self.assertEqual(len(journal["reports"]), 0)
                self.assertEqual(journal["holds"][0]["worksheets_created"], 0)
                self.assertEqual(journal["holds"][0]["reports_created"], 0)

    def test_ingest_rolls_back_all_state_when_staging_fails(self) -> None:
        journal = gate.empty_journal()
        before = gate.journal_hash(journal)
        with patch.object(gate, "_event", side_effect=RuntimeError("staging failure")):
            effect = gate.ingest_row(journal, gate._base_row(1))
        self.assertEqual(effect["kind"], "ROLLBACK")
        self.assertEqual(effect["code"], "ATOMIC_INGEST_FAILED")
        self.assertEqual(effect["pre_state_hash"], before)
        self.assertEqual(effect["post_state_hash"], before)
        self.assertEqual(gate.journal_hash(journal), before)
        self.assertEqual(journal["accessions"], {})
        self.assertEqual(journal["worksheets"], {})
        self.assertEqual(journal["reports"], {})
        self.assertEqual(journal["holds"], [])

    def test_replay_adds_zero_records(self) -> None:
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_row(journal, row)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(
            replay,
            {
                "added_accessions": 0,
                "added_worksheets": 0,
                "added_holds": 0,
                "added_reports": 0,
                "replay_noops": 200,
            },
        )
        self.assertEqual(len(journal["accessions"]), 160)
        self.assertEqual(len(journal["holds"]), 40)

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
