#!/usr/bin/env python3
"""Binary acceptance for lexington-mrf-diversion-gate-01."""

from __future__ import annotations

import unittest
from copy import deepcopy

import lexington_mrf_diversion_gate as gate


class LexingtonMrfDiversionGateTests(unittest.TestCase):
    def test_acceptance_fixture_row_count(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 50)

    def test_pass_contract_exact_counts(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 50)
        self.assertEqual(result["collapsed_duplicates"], 10)
        self.assertEqual(result["ignored_stale_states"], 8)
        self.assertEqual(result["unique_loads"], 40)
        self.assertEqual(
            result["counts"],
            {
                "LANDFILL_CITY": 10,
                "HOLD_HAULER": 10,
                "ACCEPT": 15,
                "HOLD_CAPACITY": 5,
            },
        )
        self.assertLessEqual(result["occupancy_accepted_t"], 100.0)
        self.assertEqual(result["occupancy_accepted_t"], 90.0)
        self.assertEqual(result["actions"], [])
        self.assertFalse(result["equipment_control"])
        self.assertFalse(result["autonomous_safety_decision"])

    def test_replay_identical_hashes(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(len(first["manifest_sha256"]), 64)

    def test_collapse_is_by_load_id(self) -> None:
        rows = gate.build_acceptance_fixture()
        unique, collapsed = gate.collapse_duplicates(rows)
        self.assertEqual(collapsed, 10)
        self.assertEqual(len(unique), 40)
        self.assertEqual(len({row["load_id"] for row in unique}), 40)

    def test_stale_notices_do_not_reroute_open_loads(self) -> None:
        rows = gate.build_acceptance_fixture()
        stale = [row for row in rows if row.get("stale_notice") and not str(row["row_id"]).startswith("DUP")]
        self.assertEqual(len(stale), 8)
        for row in stale:
            self.assertEqual(row["current_window"], "OPEN")
            receipt = gate.classify_load(row, occupancy_tons=0.0)
            self.assertEqual(receipt["disposition"], "ACCEPT")
            self.assertEqual(receipt["stale_notice_ignored"], row["stale_notice"])

        poisoned = deepcopy(rows)
        for row in poisoned:
            if row.get("stale_notice"):
                row["current_window"] = row["stale_notice"]
        bad = gate.run_gate(poisoned)
        self.assertNotEqual(bad["counts"]["LANDFILL_CITY"], 10)
        self.assertNotEqual(bad["counts"]["ACCEPT"], 15)

    def test_occupancy_cap_holds_overflow(self) -> None:
        result = gate.run_gate()
        accepted = [row for row in result["receipts"] if row["disposition"] == "ACCEPT"]
        held = [row for row in result["receipts"] if row["disposition"] == "HOLD_CAPACITY"]
        self.assertEqual(len(accepted), 15)
        self.assertEqual(len(held), 5)
        self.assertTrue(all(row["tons"] == 6.0 for row in accepted))
        self.assertTrue(all(row["tons"] == 12.0 for row in held))
        self.assertTrue(all(row["occupancy_delta_t"] == 0.0 for row in held))
        self.assertLessEqual(sum(row["occupancy_delta_t"] for row in accepted), 100.0)

    def test_city_divert_and_hauler_hold_reasons(self) -> None:
        result = gate.run_gate()
        city = [row for row in result["receipts"] if row["disposition"] == "LANDFILL_CITY"]
        hauler = [row for row in result["receipts"] if row["disposition"] == "HOLD_HAULER"]
        self.assertEqual(len(city), 10)
        self.assertEqual(len(hauler), 10)
        self.assertTrue(all(row["source"] == "CITY" for row in city))
        self.assertTrue(all(row["source"] == "HAULER" for row in hauler))
        self.assertTrue(all(row["reason"] == "city_load_in_divert_window" for row in city))
        self.assertTrue(all(row["reason"] == "outside_hauler_in_hold_window" for row in hauler))

    def test_no_actions_emitted(self) -> None:
        result = gate.run_gate()
        for receipt in result["receipts"]:
            self.assertEqual(receipt["actions"], [])


if __name__ == "__main__":
    unittest.main()
