#!/usr/bin/env python3
"""Binary acceptance for eagletrax-split-sample-preflight-lims-01."""

from __future__ import annotations

import unittest
from copy import deepcopy

import eagletrax_split_sample_preflight as gate


class EagleTraxSplitSamplePreflightTests(unittest.TestCase):
    def test_acceptance_fixture_is_240_split_200_40(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 240)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "ACCESSION"), 200)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "HOLD"), 40)
        codes = [row["expected_hold_code"] for row in rows if row["expected_state"] == "HOLD"]
        self.assertEqual(
            {code: codes.count(code) for code in gate.HOLD_CODES},
            gate.HOLD_CODE_COUNTS,
        )

    def test_pass_contract_exact_parents_children_and_holds(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 240)
        self.assertEqual(result["accessioned_parents"], 200)
        self.assertEqual(result["held"], 40)
        self.assertEqual(result["hold_code_counts"], gate.HOLD_CODE_COUNTS)
        self.assertEqual(result["accessioned_children"], gate.expected_child_count())
        self.assertEqual(len(set(result["parent_ids"])), 200)
        self.assertEqual(len(set(result["child_ids"])), result["accessioned_children"])
        self.assertEqual(result["released_reports"], 0)
        self.assertEqual(result["blocked_reports"], 200)
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["production_writes"], 0)
        self.assertFalse(result["autonomous_release"])

    def test_every_valid_parent_has_exact_expected_children(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        by_request = {item["request_id"]: item for item in result["accessions"]}
        children = {}
        for child in result["children"]:
            children.setdefault(child["request_id"], []).append(child["discipline"])
        for row in rows:
            if row["expected_state"] != "ACCESSION":
                self.assertNotIn(row["request_id"], by_request)
                continue
            parent = by_request[row["request_id"]]
            self.assertEqual(parent["expected_children"], row["expected_children"])
            self.assertEqual(sorted(children[row["request_id"]]), sorted(row["expected_children"]))
            self.assertEqual(parent["parent_id"], gate.parent_accession_id(row["request_id"]))
            for discipline in row["expected_children"]:
                child_id = parent["child_ids"][discipline]
                self.assertEqual(child_id, gate.child_accession_id(row["request_id"], discipline))
                child = next(item for item in result["children"] if item["child_id"] == child_id)
                self.assertEqual(child["aliquot_of"], parent["parent_id"])
                self.assertEqual(child["parent_id"], parent["parent_id"])
                self.assertEqual(child["discipline"], discipline)

    def test_all_forty_holds_keep_exact_predetermined_codes(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {item["request_id"]: item for item in result["holds"]}
        self.assertEqual(len(holds), 40)
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["request_id"]]
            self.assertEqual(hold["code"], row["expected_hold_code"])
            self.assertEqual(hold["state"], "HOLD")
            self.assertFalse(hold["interface_live"])
        accessioned = {item["request_id"] for item in result["accessions"]}
        self.assertTrue(accessioned.isdisjoint(holds))
        self.assertEqual(accessioned | set(holds), {row["request_id"] for row in rows})

    def test_results_never_attach_to_the_wrong_child(self) -> None:
        journal = gate.empty_journal()
        rows = [row for row in gate.build_acceptance_fixture() if row["kind"] == "CHEM_AND_MICRO"][:2]
        for row in rows:
            gate.ingest_row(journal, row)
        first, second = rows
        first_parent = gate.parent_accession_id(first["request_id"])
        first_chem = gate.child_accession_id(first["request_id"], "CHEM")
        first_micro = gate.child_accession_id(first["request_id"], "MICRO")
        second_chem = gate.child_accession_id(second["request_id"], "CHEM")

        self.assertEqual(
            gate.attach_result(
                journal,
                target_id=first_parent,
                discipline="CHEM",
                result={"potency_pct": 99.1},
                request_id=first["request_id"],
            )["code"],
            "WRONG_CHILD",
        )
        self.assertEqual(
            gate.attach_result(
                journal,
                target_id=first_micro,
                discipline="CHEM",
                result={"potency_pct": 99.1},
                request_id=first["request_id"],
            )["code"],
            "WRONG_CHILD",
        )
        self.assertEqual(
            gate.attach_result(
                journal,
                target_id=first_chem,
                discipline="MICRO",
                result={"sterility": "NG"},
                request_id=first["request_id"],
            )["code"],
            "WRONG_CHILD",
        )
        self.assertEqual(
            gate.attach_result(
                journal,
                target_id=second_chem,
                discipline="CHEM",
                result={"potency_pct": 99.1},
                request_id=first["request_id"],
            )["code"],
            "WRONG_CHILD",
        )
        self.assertIsNone(journal["children"][first_chem]["result"])
        self.assertIsNone(journal["children"][first_micro]["result"])
        self.assertIsNone(journal["children"][second_chem]["result"])

        ok = gate.attach_result(
            journal,
            target_id=first_chem,
            discipline="CHEM",
            result={"potency_pct": 99.1},
            request_id=first["request_id"],
        )
        self.assertTrue(ok["ok"])
        self.assertEqual(journal["children"][first_chem]["result"]["potency_pct"], 99.1)
        replay = gate.attach_result(
            journal,
            target_id=first_chem,
            discipline="CHEM",
            result={"potency_pct": 99.1},
            request_id=first["request_id"],
        )
        self.assertTrue(replay["duplicate"])
        swapped = gate.attach_result(
            journal,
            target_id=first_chem,
            discipline="CHEM",
            result={"potency_pct": 12.0},
            request_id=first["request_id"],
        )
        self.assertFalse(swapped["ok"])
        self.assertEqual(journal["children"][first_chem]["result"]["potency_pct"], 99.1)

    def test_retries_are_idempotent(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(len(first["audit_sha256"]), 64)

        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_row(journal, row)
        self.assertEqual(len(journal["accessions"]), 200)
        self.assertEqual(len(journal["holds"]), 40)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(replay["added_parent_count"], 0)
        self.assertEqual(replay["added_child_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["parent_count"], 200)
        self.assertEqual(replay["hold_count"], 40)
        self.assertEqual(replay["replay_noops"], 240)

    def test_every_source_record_and_field_is_traceable(self) -> None:
        result = gate.run_gate()
        for parent in result["accessions"]:
            prov = parent["provenance"]
            self.assertEqual(len(prov["request_hash"]), 64)
            self.assertEqual(len(prov["form_hash"]), 64)
            self.assertTrue(prov["fields"]["form.sample_id"]["hash"])
            self.assertTrue(prov["container_hashes"])
            self.assertEqual(parent["interface_state"], "SIMULATED")
            if "CHEM" in parent["tests"]:
                self.assertTrue(parent["workbook_bound"])
                self.assertTrue(parent["workbook"]["formula_id"])
            self.assertTrue(parent["handling_bound"])
        for child in result["children"]:
            self.assertEqual(len(child["provenance"]["child_hash"]), 64)
            self.assertEqual(len(child["provenance"]["source_hashes"]["form"]), 64)
        for hold in result["holds"]:
            self.assertEqual(len(hold["provenance"]["request_hash"]), 64)
            self.assertTrue(hold["provenance"]["fields"])

    def test_release_requires_named_human_review(self) -> None:
        journal = gate.empty_journal()
        row = next(item for item in gate.build_acceptance_fixture() if item["kind"] == "CHEM_AND_MICRO")
        gate.ingest_row(journal, row)
        parent_id = gate.parent_accession_id(row["request_id"])
        parent = journal["accessions"][parent_id]
        self.assertEqual(gate.report_status(parent, journal), "BLOCKED_MISSING_RESULT")

        denied = gate.release_report(journal, parent_id, actor_role=gate.HUMAN_ROLE, actor=gate.HUMAN_RELEASER)
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "REPORT_BLOCKED")

        for discipline in row["expected_children"]:
            gate.attach_result(
                journal,
                target_id=gate.child_accession_id(row["request_id"], discipline),
                discipline=discipline,
                result={"value": discipline, "units": "synthetic"},
                request_id=row["request_id"],
            )
        self.assertEqual(parent["report_status"], "BLOCKED_MISSING_QC")
        gate.qc_signoff(journal, parent_id)
        self.assertEqual(parent["report_status"], "READY_FOR_HUMAN_RELEASE")

        autonomous = gate.release_report(journal, parent_id, actor_role="SYSTEM", actor="bot")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        unnamed = gate.release_report(journal, parent_id, actor_role=gate.HUMAN_ROLE, actor="")
        self.assertEqual(unnamed["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(parent["released"])

        human = gate.release_report(journal, parent_id, actor_role=gate.HUMAN_ROLE, actor=gate.HUMAN_RELEASER)
        self.assertTrue(human["ok"])
        self.assertEqual(parent["report_status"], "RELEASED")
        self.assertEqual(parent["released_by"], gate.HUMAN_RELEASER)

    def test_public_split_workbook_handling_and_six_month_rules(self) -> None:
        valid = next(item for item in gate.build_acceptance_fixture() if item["kind"] == "CHEM_AND_MICRO")
        self.assertEqual(len({item["container_id"] for item in valid["containers"]}), 2)
        self.assertTrue(gate.classify_submission(valid)["ok"])

        unsplit = deepcopy(valid)
        unsplit["last_submission_at"] = "2026-06-15"
        shared = unsplit["containers"][0]["container_id"]
        unsplit["containers"][1]["container_id"] = shared
        self.assertEqual(gate.classify_submission(unsplit)["code"], "UNSPLIT_CONTAINER")

        no_book = deepcopy(valid)
        no_book["workbook"] = {"present": False, "formula_id": "", "batch_record_id": ""}
        self.assertEqual(gate.classify_submission(no_book)["code"], "ABSENT_WORKBOOK")

        no_handling = deepcopy(valid)
        no_handling["handling"] = {"present": False}
        self.assertEqual(gate.classify_submission(no_handling)["code"], "MISSING_HANDLING")

        stale = deepcopy(valid)
        stale["last_submission_at"] = "2025-08-01"
        self.assertEqual(gate.classify_submission(stale)["code"], "STALE_CLIENT")
        self.assertTrue(gate._is_stale("2026-02-28"))
        self.assertFalse(gate._is_stale("2026-03-01"))

        mismatch = deepcopy(valid)
        mismatch["containers"][0]["sample_id"] = "OTHER"
        self.assertEqual(gate.classify_submission(mismatch)["code"], "FORM_CONTAINER_MISMATCH")

        short = deepcopy(valid)
        for container in short["containers"]:
            container["volume_ml"] = 1
        self.assertEqual(gate.classify_submission(short)["code"], "INSUFFICIENT_CONTAINER")

    def test_simulated_adapter_refuses_production_writes(self) -> None:
        result = gate.run_gate()
        self.assertTrue(result["adapter"]["read_only"])
        self.assertFalse(result["adapter"]["interface_live"])
        self.assertEqual(result["adapter_write_attempt"]["code"], "PRODUCTION_WRITE_DENIED")
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )
        adapter = gate.SimulatedEagleTraxAdapter()
        denied = adapter.write({"accession": "live"})
        self.assertEqual(denied["code"], "PRODUCTION_WRITE_DENIED")
        self.assertEqual(adapter.snapshot()["production_writes"], 0)


if __name__ == "__main__":
    unittest.main()
