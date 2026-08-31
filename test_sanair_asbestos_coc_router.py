#!/usr/bin/env python3
"""Binary acceptance for sanair-asbestos-coc-router-lims-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNNER_PATH = ROOT / "revenue" / "sanair_asbestos_coc_router" / "runner.py"
SPEC = importlib.util.spec_from_file_location("sanair_asbestos_coc_router_runner", RUNNER_PATH)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gate)


class SanairAsbestosCocRouterTests(unittest.TestCase):
    def test_acceptance_fixture_is_360_split_300_60(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 360)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "ROUTED"), 300)
        self.assertEqual(sum(1 for row in rows if row["expected_state"] == "HOLD"), 60)
        loaded = gate.load_fixture()
        self.assertEqual(len(loaded), 360)
        self.assertEqual(
            [row["coc_id"] for row in loaded],
            [row["coc_id"] for row in rows],
        )
        codes = [row["expected_hold_code"] for row in rows if row["expected_state"] == "HOLD"]
        for code in gate.HOLD_CODES:
            self.assertEqual(codes.count(code), 15)

    def test_pass_contract_exact_state_counts_and_hashes(self) -> None:
        result = gate.run_router()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(counts["expected"], gate.EXPECTED_COUNTS)
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(result["lineage_sha256"], gate.GOLDEN_LINEAGE_SHA256)
        self.assertEqual(result["fixture_sha256"], gate.GOLDEN_FIXTURE_SHA256)
        self.assertEqual(result["replay_audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(len(result["audit_sha256"]), 64)
        self.assertTrue(result["ok"])

    def test_every_valid_order_enters_designated_lab_once_with_parity(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_router(rows)
        self.assertEqual(result["parity_failures"], [])
        self.assertEqual(result["duplicate_routes"], 0)
        self.assertEqual(result["lab_counts"], {"RIC": 100, "CIN": 100, "BOS": 100})
        by_coc = {item["coc_id"]: item for item in result["route_records"]}
        self.assertEqual(len(by_coc), 300)
        seen_samples = []
        for row in rows:
            if row["expected_state"] != "ROUTED":
                continue
            routed = by_coc[row["coc_id"]]
            self.assertEqual(routed["lab"], row["designated_lab"])
            self.assertEqual(routed["method"], row["method"])
            self.assertTrue(gate.lab_method_capable(routed["lab"], routed["method"], routed["tat_code"]))
            self.assertEqual(routed["interface_state"], "SIMULATED")
            self.assertFalse(routed["interface_live"])
            seen_samples.append(routed["sample_id"])
        self.assertEqual(len(seen_samples), len(set(seen_samples)))

    def test_all_sixty_block_with_exact_code(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_router(rows)
        holds = {item["coc_id"]: item for item in result["hold_records"]}
        self.assertEqual(len(holds), 60)
        for row in rows:
            if row["expected_state"] != "HOLD":
                continue
            hold = holds[row["coc_id"]]
            self.assertEqual(hold["code"], row["expected_hold_code"])
            self.assertEqual(hold["state"], "HOLD")
            self.assertEqual(hold["owner_role"], "ASBESTOS_INTAKE_LEAD")
            self.assertEqual(hold["owner_desk"], "RAPID_TAT_COC_ROUTER")
            self.assertFalse(hold["released"])
        self.assertEqual(result["hold_code_counts"], {code: 15 for code in gate.HOLD_CODES})
        accounted = {item["coc_id"] for item in result["route_records"]} | set(holds)
        self.assertEqual(accounted, {row["coc_id"] for row in rows})

    def test_tat_clocks_follow_fixture_receipt_rules(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.run_router(rows)
        self.assertEqual(result["tat_clock_failures"], [])
        by_coc = {item["coc_id"]: item for item in result["route_records"]}
        for row in rows:
            if row["expected_state"] != "ROUTED":
                continue
            routed = by_coc[row["coc_id"]]
            expected = gate.tat_clock(row["received_at"], row["tat_code"])
            self.assertEqual(routed["clock_start"], row["received_at"])
            self.assertEqual(routed["clock_start"], expected["clock_start"])
            self.assertEqual(routed["due_at"], expected["due_at"])
            self.assertEqual(routed["tat_basis"], "FIXTURE_RECEIPT")
            self.assertNotEqual(routed["clock_start"], row["collected_at"])
            self.assertFalse(gate.cutoff_violated(row["received_at"], row["tat_code"]))

    def test_permissions_match_the_coc(self) -> None:
        result = gate.run_router()
        self.assertEqual(result["permission_failures"], [])
        for item in result["route_records"]:
            self.assertTrue(gate.permissions_match(item))
            self.assertEqual(item["recipient_name"], item["report_to"])
            self.assertEqual(
                item["report_permission"],
                gate.PERMISSION_BY_ROLE[item["recipient_role"]],
            )
            self.assertIn(item["amendment_channel"], {"EMAIL", "FAX"})

    def test_replay_is_idempotent_with_source_hashes_and_lineage(self) -> None:
        first = gate.run_router()
        second = gate.run_router()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["lineage_sha256"], second["lineage_sha256"])
        self.assertEqual(first["lineage_failures"], [])
        ledger = gate.empty_ledger()
        rows = gate.build_acceptance_fixture()
        for row in rows:
            gate.route_coc(ledger, row)
        self.assertEqual(len(ledger["routes"]), 300)
        self.assertEqual(len(ledger["holds"]), 60)
        replay = gate.replay_into(ledger, rows)
        self.assertEqual(replay["added_route_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["replay_noops"], 360)
        hashes = [item["source_hash"] for item in ledger["routes"].values()]
        self.assertEqual(len(hashes), len(set(hashes)))
        for item in ledger["routes"].values():
            self.assertEqual(item["lineage"][0]["hash"], item["source_hash"])
            self.assertEqual(item["lineage"][-1]["hash"], item["route_hash"])
            self.assertEqual(item["lineage_hash"], gate.sha256_hex(item["lineage"]))

    def test_named_human_only_release_no_autonomous(self) -> None:
        result = gate.run_router()
        self.assertTrue(
            all(item["code"] == "AUTONOMOUS_RELEASE_DENIED" for item in result["autonomous_release_effects"])
        )
        self.assertEqual(result["autonomous_released"], 0)
        self.assertEqual(sum(1 for item in result["human_release_effects"] if item.get("ok")), 300)
        ledger = gate.empty_ledger()
        valid = next(row for row in gate.build_acceptance_fixture() if row["expected_state"] == "ROUTED")
        routed = gate.route_coc(ledger, valid)
        rte_id = routed["route_id"]
        auto_result = gate.release_order(ledger, rte_id, "robot", "AUTOMATION")
        self.assertFalse(auto_result["ok"])
        self.assertEqual(auto_result["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(ledger["routes"][rte_id]["released"])
        other_result = gate.release_order(ledger, rte_id, "someone", "INTAKE")
        self.assertFalse(other_result["ok"])
        self.assertEqual(other_result["code"], "HOLD_NAMED_HUMAN_REQUIRED")
        human = gate.release_order(
            ledger,
            rte_id,
            gate.HUMAN_RELEASER,
            gate.HUMAN_ROLE,
        )
        self.assertTrue(human["ok"])
        self.assertTrue(ledger["routes"][rte_id]["released"])
        hold_row = next(row for row in gate.build_acceptance_fixture() if row["expected_state"] == "HOLD")
        held = gate.route_coc(ledger, hold_row)
        self.assertEqual(held["kind"], "HOLD")
        self.assertFalse(held.get("released", False))

    def test_no_live_adapters_or_sample_action(self) -> None:
        result = gate.run_router()
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertEqual(result["production_writes"], 0)
        self.assertEqual(result["live_sample_actions"], 0)
        self.assertEqual(result["live_reports"], 0)
        self.assertEqual(result["billing_writes"], 0)
        self.assertEqual(result["cash_usd"], 0)
        self.assertEqual(result["truth_gate"], "HOLD / BUILD-AND-VERIFY")
        self.assertEqual(result["adapters"]["coc"], "SIMULATED_READONLY")
        self.assertEqual(result["adapters"]["lims"], "SIMULATED_READONLY")


if __name__ == "__main__":
    unittest.main()
