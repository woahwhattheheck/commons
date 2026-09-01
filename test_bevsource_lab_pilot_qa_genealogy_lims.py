#!/usr/bin/env python3
"""Binary acceptance for bevsource-lab-pilot-qa-genealogy-lims-01."""

from __future__ import annotations

from copy import deepcopy
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


class BevsourceClosednessReds(unittest.TestCase):
    def _clean(self) -> dict:
        return deepcopy(gate.build_acceptance_fixture()[0])

    def _seed(self) -> dict:
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        return journal

    def test_truth_flags_and_qa_and_empty_row_id_hold(self) -> None:
        cases = (
            ({"synthetic": False}, gate.HOLD_TRUTH_FLAG),
            ({"deidentified": False}, gate.HOLD_TRUTH_FLAG),
            ({"chemistry": "OUT_OF_SPEC"}, gate.HOLD_QA_OUT_OF_SPEC),
            ({"shelf_life": "FAIL"}, gate.HOLD_QA_OUT_OF_SPEC),
            ({"row_id": ""}, gate.HOLD_MISSING_REQUIRED_FIELD),
        )
        for patch, code in cases:
            journal = gate.empty_journal()
            row = self._clean()
            row.update(patch)
            before = deepcopy(journal)
            effect = gate.ingest_row(journal, row)
            self.assertEqual(effect["kind"], "HOLD", patch)
            self.assertEqual(effect["code"], code, patch)
            self.assertEqual(len(journal["reviews"]), 0, patch)
            self.assertEqual(len(journal["packages"]), 0, patch)
            self.assertEqual(len(journal["links"]), 0, patch)
            self.assertEqual(journal["holds"][0]["code"], code, patch)
            self.assertNotEqual(journal, before, patch)
            self.assertEqual(gate.normalize_run(row)["synthetic"], row.get("synthetic"))
            self.assertEqual(
                gate.normalize_run(row)["deidentified"], row.get("deidentified")
            )

    def test_fourth_duplicate_ingredient_is_cardinality_hold(self) -> None:
        journal = gate.empty_journal()
        row = self._clean()
        row["ingredient_lots"] = list(row["ingredient_lots"]) + [
            {"ingredient": "ACIDULANT", "lot_id": "LOT-ACD-001"}
        ]
        effect = gate.ingest_row(journal, row)
        self.assertEqual(effect["kind"], "HOLD")
        self.assertEqual(effect["code"], gate.HOLD_INGREDIENT_CARDINALITY)
        self.assertEqual(len(journal["packages"]), 0)
        self.assertEqual(len(journal["lots"]), 0)
        self.assertEqual(len(journal["reviews"]), 0)

    def test_non_mapping_top_level_rows_reject_without_mutation(self) -> None:
        for row in ("garbage", [1], 1, True):
            with self.subTest(row=row):
                journal = self._seed()
                before = deepcopy(journal)
                before_bytes = gate._canonical(journal).encode("utf-8")
                before_hash = gate.journal_hash(journal)
                try:
                    effect = gate.ingest_row(journal, row)
                except Exception as exc:  # pragma: no cover - explicit API guarantee
                    self.fail(f"{row!r} escaped ingest_row: {exc!r}")
                self.assertEqual(
                    effect,
                    {
                        "kind": "REJECT",
                        "ok": False,
                        "code": "ATOMIC_COMMIT_FAILED",
                        "row_id": "",
                    },
                )
                self.assertEqual(journal, before)
                self.assertEqual(
                    gate._canonical(journal).encode("utf-8"), before_bytes
                )
                self.assertEqual(gate.journal_hash(journal), before_hash)

    def test_conflicting_replay_rejects_on_input_digest(self) -> None:
        journal = self._seed()
        before = deepcopy(journal)
        before_hash = gate.journal_hash(journal)
        row = self._clean()
        row["microbiology"] = "POSITIVE"
        effect = gate.ingest_row(journal, row)
        self.assertEqual(effect["kind"], gate.REPLAY_CONFLICT)
        self.assertEqual(effect["code"], gate.REPLAY_CONFLICT)
        self.assertFalse(effect["ok"])
        self.assertEqual(journal, before)
        self.assertEqual(gate.journal_hash(journal), before_hash)
        self.assertEqual(journal["packages"][row["package_unit_id"]]["microbiology"], "NEGATIVE")

    def test_duplicate_identifiers_reject_without_mutation(self) -> None:
        journal = self._seed()
        before = deepcopy(journal)
        before_hash = gate.journal_hash(journal)
        probes = (
            {"run_id": "RUN-001", "row_id": "BEV-DUP-RUN"},
            {"package_unit_id": "PKG-001", "row_id": "BEV-DUP-PKG"},
            {"pilot_batch_id": "BATCH-001", "row_id": "BEV-DUP-BATCH"},
            {
                "row_id": "BEV-DUP-LOT",
                "ingredient_lots": [
                    {"ingredient": "ACIDULANT", "lot_id": "LOT-ACD-001"},
                    {"ingredient": "CONCENTRATE", "lot_id": "LOT-CON-DUP"},
                    {"ingredient": "PROCESS_WATER", "lot_id": "LOT-WTR-DUP"},
                ],
            },
        )
        for patch in probes:
            row = self._clean()
            row["row_id"] = "BEV-DUP-BASE"
            row["run_id"] = "RUN-DUP"
            row["pilot_batch_id"] = "BATCH-DUP"
            row["package_unit_id"] = "PKG-DUP"
            row["ingredient_lots"] = [
                {"ingredient": "ACIDULANT", "lot_id": "LOT-ACD-DUP"},
                {"ingredient": "CONCENTRATE", "lot_id": "LOT-CON-DUP"},
                {"ingredient": "PROCESS_WATER", "lot_id": "LOT-WTR-DUP"},
            ]
            row.update(patch)
            effect = gate.ingest_row(journal, row)
            self.assertEqual(effect["kind"], "REJECT", patch)
            self.assertEqual(effect["code"], gate.REJECT_DUPLICATE_IDENTIFIER, patch)
            self.assertFalse(effect["ok"], patch)
            self.assertEqual(journal, before, patch)
            self.assertEqual(gate.journal_hash(journal), before_hash, patch)
            self.assertEqual(journal["run_index"]["RUN-001"], "BEV-001")


if __name__ == "__main__":
    unittest.main()
