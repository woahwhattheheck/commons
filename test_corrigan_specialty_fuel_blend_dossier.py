#!/usr/bin/env python3
"""Fail-closed binary acceptance for corrigan-specialty-fuel-blend-dossier-lims-01."""

from __future__ import annotations

import unittest
from collections import Counter
from decimal import Decimal

import corrigan_specialty_fuel_blend_dossier as gate


class CorriganSpecialtyFuelBlendDossierTests(unittest.TestCase):
    def test_acceptance_fixture_is_80_split_64_8_4_4(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 80)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "CLEAN"), 64)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "HOLD"), 16)
        holds = [row["expected_hold"] for row in rows if row["expected_state"] == "HOLD"]
        self.assertEqual(holds.count(gate.HOLD_FORMULA), 8)
        self.assertEqual(holds.count(gate.HOLD_MISSING_EXT), 4)
        self.assertEqual(holds.count(gate.HOLD_OOS), 4)
        self.assertEqual(len({row["order_id"] for row in rows}), 80)
        self.assertEqual(len({row["formula_id"] for row in rows if row["expected_state"] == "CLEAN"}), 8)
        for formula_id in gate.FORMULA_IDS:
            clean = [
                row
                for row in rows
                if row["formula_id"] == formula_id and row["expected_state"] == "CLEAN"
            ]
            self.assertEqual(len(clean), 8, formula_id)

    def test_pass_contract_exact_80_64_16(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.GOLDEN_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["input_rows"], 80)
        self.assertEqual(result["clean"], 64)
        self.assertEqual(result["hold"], 16)
        self.assertEqual(result["hold_formula_version_mismatch"], 8)
        self.assertEqual(result["hold_missing_external_result"], 4)
        self.assertEqual(result["hold_oos"], 4)
        self.assertEqual(result["batches"], 72)
        self.assertEqual(result["duplicate_batches"], 0)
        self.assertEqual(result["orphan_tank_movements"], 0)
        self.assertEqual(result["staged_coa"], 64)
        self.assertEqual(result["genealogy"], 64)
        self.assertEqual(result["human_disposed"], 64)
        self.assertEqual(result["autonomous_released"], 0)
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["replay_added_orders"], 0)
        self.assertEqual(Counter(result["hold_codes"]), Counter(gate.HOLD_FAMILY_COUNTS))

    def test_every_exception_receives_expected_hold_code(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_gate(rows)
        holds = {item["order_id"]: item for item in result["hold_records"]}
        self.assertEqual(len(holds), 16)
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["order_id"]]
            self.assertEqual(hold["code"], row["expected_hold"], row["order_id"])
            self.assertEqual(hold["state"], "HOLD")
        for formula_id, spec in gate.FORMULAS.items():
            mismatch_id = gate._order_id(spec["token"], 9)
            self.assertEqual(holds[mismatch_id]["code"], gate.HOLD_FORMULA, mismatch_id)
            self.assertNotIn(mismatch_id, result["genealogies"])
            self.assertFalse(any(batch["order_id"] == mismatch_id for batch in result["batch_records"].values()))
        for formula_id in gate.FORMULA_IDS[:4]:
            missing_id = gate._order_id(gate.FORMULAS[formula_id]["token"], 10)
            self.assertEqual(holds[missing_id]["code"], gate.HOLD_MISSING_EXT, missing_id)
        for formula_id in gate.FORMULA_IDS[4:]:
            oos_id = gate._order_id(gate.FORMULAS[formula_id]["token"], 10)
            self.assertEqual(holds[oos_id]["code"], gate.HOLD_OOS, oos_id)

    def test_exact_genealogy_on_every_clean_order(self) -> None:
        rows = {row["order_id"]: row for row in gate.build_acceptance_fixture()}
        result = gate.run_gate()
        self.assertEqual(len(result["genealogies"]), 64)
        hashes = [item["lineage_sha256"] for item in result["genealogies"].values()]
        self.assertEqual(len(set(hashes)), 64)
        for order_id, genealogy in result["genealogies"].items():
            src = rows[order_id]
            spec = gate.FORMULAS[src["formula_id"]]
            self.assertEqual(genealogy["order_id"], order_id)
            self.assertEqual(genealogy["formula_id"], src["formula_id"])
            self.assertEqual(genealogy["formula_version"], spec["current_version"])
            self.assertEqual(len(genealogy["lots"]), len(spec["ingredients"]))
            lot_codes = [lot["ingredient_code"] for lot in genealogy["lots"]]
            self.assertEqual(lot_codes, [item["code"] for item in spec["ingredients"]])
            self.assertEqual(sum(Decimal(lot["gallons"]) for lot in genealogy["lots"]), Decimal(src["gallons"]))
            movements = genealogy["tank_movements"]
            self.assertEqual(len(movements), len(spec["ingredients"]) + 1)
            self.assertTrue(all(item["batch_id"] == genealogy["batch_id"] for item in movements))
            self.assertEqual(movements[-1]["kind"], "BLEND_TO_FINISH")
            self.assertEqual(movements[-1]["gallons"], src["gallons"])
            self.assertEqual(movements[-1]["from_tank"], spec["blend_tank"])
            self.assertEqual(movements[-1]["to_tank"], spec["finish_tank"])
            self.assertIsNotNone(genealogy["internal_result"])
            self.assertIsNotNone(genealogy["external_packet"])
            self.assertIsNotNone(genealogy["coa"])
            self.assertEqual(genealogy["internal_result"]["assays"], genealogy["external_packet"]["assays"])
            self.assertEqual(genealogy["coa"]["assays"], genealogy["internal_result"]["assays"])
            self.assertEqual(genealogy["lineage_sha256"], gate.sha256_hex(genealogy["source"]))
            self.assertEqual(len(genealogy["lineage_sha256"]), 64)

    def test_zero_orphan_tank_movements_and_zero_duplicate_batches(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["orphan_tank_movements"], 0)
        self.assertEqual(result["orphan_movement_ids"], [])
        self.assertEqual(result["duplicate_batches"], 0)
        self.assertEqual(result["duplicate_batch_ids"], [])
        self.assertEqual(len(result["batch_ids"]), 72)
        self.assertEqual(len(set(result["batch_ids"])), 72)
        owners = [batch["order_id"] for batch in result["batch_records"].values()]
        self.assertEqual(len(owners), len(set(owners)))
        for movement in result["movements"].values():
            self.assertIn(movement["batch_id"], result["batch_records"])
            self.assertIn(movement["movement_id"], result["batch_records"][movement["batch_id"]]["movement_ids"])

    def test_coa_contents_and_rounding_are_deterministic(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(len(first["coas"]), 64)
        for coa_id, coa in first["coas"].items():
            other = second["coas"][coa_id]
            self.assertEqual(coa["assays"], other["assays"])
            spec = gate.FORMULAS[coa["formula_id"]]
            for name, bound in spec["assays"].items():
                value = coa["assays"][name]
                self.assertEqual(value, gate.qround(bound["target"], bound["places"]))
                self.assertEqual(value, gate.qround(value, bound["places"]))
                self.assertEqual(coa["places"][name], bound["places"])
                self.assertEqual(coa["units"][name], bound["unit"])
            self.assertEqual(coa["state"], "STAGED")
            self.assertFalse(coa["released"])
            self.assertEqual(coa["disposition"], "HUMAN_STAGED_ACCEPT")
            self.assertEqual(coa["disposed_by"], gate.HUMAN_RELEASER)

    def test_source_lineage_is_immutable_and_self_hashing(self) -> None:
        result = gate.run_gate()
        mutated = gate.run_gate()
        for order_id, genealogy in result["genealogies"].items():
            source = dict(genealogy["source"])
            self.assertEqual(gate.sha256_hex(source), genealogy["lineage_sha256"])
            other = mutated["genealogies"][order_id]["source"]
            self.assertEqual(source, other)
            source["formula_version"] = "MUTATED"
            self.assertNotEqual(gate.sha256_hex(source), genealogy["lineage_sha256"])

    def test_replay_is_idempotent_and_adds_zero(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        journal = gate.empty_journal()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.ingest_order(journal, row)
        replay = gate.replay_into(journal, rows)
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(len(first["audit_sha256"]), 64)
        self.assertEqual(gate.sha256_hex(first["audit"]), first["audit_sha256"])
        self.assertEqual(replay["added_orders"], 0)
        self.assertEqual(replay["added_batches"], 0)
        self.assertEqual(replay["added_movements"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["replay_noops"], 80)
        self.assertEqual(first["replay_added_orders"], 0)
        self.assertEqual(first["replay_noops"], 80)

    def test_named_human_disposition_only_autonomous_denied(self) -> None:
        result = gate.run_gate()
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )
        self.assertEqual(sum(1 for item in result["human_disposition_effects"] if item.get("ok")), 64)
        self.assertTrue(all(item.get("released") is False for item in result["human_disposition_effects"]))
        self.assertEqual({item["disposed_by"] for item in result["coas"].values()}, {gate.HUMAN_RELEASER})
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_order(journal, row)
        denied = gate.named_human_disposition(journal, "SYSTEM")
        self.assertTrue(all(item["code"] == "NAMED_HUMAN_REQUIRED" for item in denied))
        self.assertTrue(all(not item.get("ok") for item in denied))
        still = gate.named_human_disposition(journal, "AUTO")
        self.assertTrue(all(item["code"] == "NAMED_HUMAN_REQUIRED" for item in still))
        accepted = gate.named_human_disposition(journal, gate.HUMAN_RELEASER)
        self.assertEqual(sum(1 for item in accepted if item.get("ok")), 64)
        self.assertFalse(any(coa["released"] for coa in journal["coas"].values()))
        self.assertFalse(result["autonomous_release"])
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["cash_usd"], 0)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
