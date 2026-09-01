#!/usr/bin/env python3
"""Binary acceptance for bevsource-lab-pilot-qa-genealogy-lims-01."""

from __future__ import annotations

import unittest

import bevsource_lab_pilot_qa_genealogy_lims as gate


class BevsourceLabPilotQaGenealogyTests(unittest.TestCase):
    def test_frozen_fixture_is_60_with_exact_exception_split(self) -> None:
        rows = gate.build_acceptance_fixture()
        counts: dict[str | None, int] = {}
        for row in rows:
            counts[row["exception_type"]] = counts.get(row["exception_type"], 0) + 1
        self.assertEqual(len(rows), 60)
        self.assertEqual(
            counts,
            {
                None: 45,
                "WRONG_FORMULA_VERSION": 5,
                "MISSING_INGREDIENT_LOT": 4,
                "FAILED_LINER_CHECK": 3,
                "POSITIVE_MICROBIOLOGY": 3,
            },
        )

    def test_pass_contract_is_exact_45_release_review_15_hold(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 60)
        self.assertEqual(result["release_review"], 45)
        self.assertEqual(result["holds"], 15)
        self.assertEqual(result["packages"], 45)
        self.assertEqual(result["batches"], 45)
        self.assertEqual(result["lots"], 135)
        self.assertEqual(result["packages_released"], 0)

    def test_all_hold_reasons_are_exact_and_create_no_output(self) -> None:
        result = gate.run_gate()
        self.assertEqual(
            result["hold_counts"],
            {
                "HOLD_WRONG_FORMULA_VERSION": 5,
                "HOLD_MISSING_INGREDIENT_LOT": 4,
                "HOLD_FAILED_LINER_CHECK": 3,
                "HOLD_POSITIVE_MICROBIOLOGY": 3,
            },
        )
        for hold in result["hold_records"]:
            self.assertEqual(hold["state"], "HOLD")
            self.assertEqual(hold["packages_created"], 0)
            self.assertEqual(hold["links_created"], 0)
            self.assertEqual(hold["reviews_created"], 0)
            self.assertFalse(hold["released"])

    def test_every_package_traces_to_one_formula_and_every_lot(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["traces"]), 45)
        for trace in result["traces"]:
            self.assertTrue(trace["ok"])
            self.assertEqual(
                trace["formula_ids"],
                [f"{gate.CURRENT_FORMULA_ID}@{gate.CURRENT_FORMULA_VERSION}"],
            )
            self.assertEqual(trace["lot_ids"], trace["expected_lots"])
            self.assertEqual(trace["batch_ids"], [trace["expected_batch"]])
            self.assertEqual(len(trace["formula_ids"]), 1)
            self.assertEqual(len(trace["lot_ids"]), 3)
        for package in result["package_records"]:
            self.assertEqual(package["formula_id"], gate.CURRENT_FORMULA_ID)
            self.assertEqual(package["formula_version"], gate.CURRENT_FORMULA_VERSION)
            self.assertEqual(set(package["ingredients"]), set(gate.REQUIRED_INGREDIENTS))
            self.assertEqual(len(package["lot_ids"]), 3)
            self.assertEqual(len(package["lineage_hash"]), 64)

    def test_genealogy_has_zero_orphan_or_duplicate_links(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["orphans"], 0)
        self.assertEqual(result["duplicates"], 0)
        self.assertEqual(result["integrity"]["orphans"], 0)
        self.assertEqual(result["integrity"]["duplicates"], 0)
        roles = {item["role"] for item in result["link_records"]}
        self.assertEqual(roles, set(gate.LINK_ROLES))

    def test_replay_hashes_are_identical_and_add_nothing(self) -> None:
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_row(journal, row)
        first = gate.journal_hash(journal)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(
            replay,
            {
                "added_packages": 0,
                "added_reviews": 0,
                "added_holds": 0,
                "added_links": 0,
                "replay_noops": 60,
                "hash_identical": True,
            },
        )
        self.assertEqual(gate.journal_hash(journal), first)
        first_run = gate.run_gate()
        second_run = gate.run_gate()
        self.assertEqual(first_run["manifest_sha256"], second_run["manifest_sha256"])
        self.assertEqual(first_run["audit_sha256"], second_run["audit_sha256"])
        self.assertEqual(first_run["journal_sha256"], second_run["journal_sha256"])
        self.assertEqual(len(first_run["manifest_sha256"]), 64)
        self.assertEqual(len(first_run["audit_sha256"]), 64)

    def test_named_human_release_only(self) -> None:
        result = gate.run_gate()
        self.assertTrue(
            all(item["state"] == "RELEASE_REVIEW" for item in result["reviews"])
        )
        self.assertTrue(all(not item["released"] for item in result["reviews"]))
        self.assertTrue(
            all(
                item["code"] == "AUTONOMOUS_RELEASE_DENIED"
                for item in result["autonomous_release_effects"]
            )
        )
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        package_id = sorted(journal["packages"])[0]
        denied = gate.release_package(
            journal, package_id, actor_role="SYSTEM", actor="automation"
        )
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "AUTONOMOUS_RELEASE_DENIED")
        released = gate.release_package(
            journal,
            package_id,
            actor_role=gate.HUMAN_REVIEWER_ROLE,
            actor="named-reviewer",
        )
        self.assertTrue(released["ok"])
        self.assertEqual(journal["packages"][package_id]["state"], "RELEASED")
        self.assertEqual(
            journal["packages"][package_id]["released_by"], "named-reviewer"
        )

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
