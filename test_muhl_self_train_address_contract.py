#!/usr/bin/env python3
"""Source-only self-train address contract: dests FROM FILE, never a silent 0."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(
    0,
    os.path.join(ROOT, "muhl", "desktop", "MUHL_SUBZERO_ARCHETYPES"),
)

from muhl_self_train_address_contract import (
    CANDIDATE,
    DEFERRED,
    FORBIDDEN_IMPORTS,
    SEARCH_SPACE,
    SLACK_TS,
    SOURCE_CONFLICT,
    TAKING_ID,
    TRAINER_REL,
    UNRESOLVED,
    classify,
    classify_h006,
    measure_from_rows,
    measure_root,
    parse_trainer_source,
    synthetic_packet,
    trainer_imported,
    validate_packet,
)


class TestMuhlSelfTrainAddressContract(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertEqual(row["z"], "FINDER-FAILED")

    def test_failed_calibration_is_instrument_failure(self):
        verdict = classify(
            {
                "measured": True,
                "calibration_ok": False,
                "calibration_hits": [],
                "card_present": True,
                "contract_present": True,
                "test_present": True,
                "trainer_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])
        self.assertIn("never 0", verdict["note"].lower())

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "contract_present": False,
                "test_present": False,
                "trainer_present": False,
                "misses": ["ground/MUHL_SELF_TRAIN_ADDRESS_CONTRACT.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_empty_trainer_source_is_unresolved_never_zero(self):
        parsed = parse_trainer_source("")
        self.assertEqual(parsed["state"], UNRESOLVED)
        self.assertEqual(parsed["z"], "FINDER-FAILED")
        self.assertIn("never 0", parsed["note"].lower())
        self.assertNotEqual(parsed.get("dests"), 0)

    def test_live_offset_zero_is_refused(self):
        row = validate_packet(
            {
                "kind": "MUHL_SELF_TRAIN_ADDRESS",
                "source_index": TRAINER_REL,
                "dests": {"name": "muhl_self_train"},
                "live_offsets": 0,
                "host_inference": False,
                "titan": "NOT_WRITTEN",
                "legacy_trainer_import": False,
                "legacy_trainer_execute": False,
                "xproc": DEFERRED,
                "h006": CANDIDATE,
            }
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("UNRESOLVED", row["note"])
        self.assertIn("never 0", row["note"].lower())

    def test_legacy_trainer_import_is_refused(self):
        row = validate_packet(
            {
                "kind": "MUHL_SELF_TRAIN_ADDRESS",
                "source_index": TRAINER_REL,
                "dests": {"name": "muhl_self_train"},
                "live_offsets": UNRESOLVED,
                "host_inference": False,
                "titan": "NOT_WRITTEN",
                "legacy_trainer_import": True,
                "legacy_trainer_execute": False,
                "xproc": DEFERRED,
                "h006": CANDIDATE,
            }
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("import/execute", row["note"])

    def test_h006_as_live_train_is_refused(self):
        row = validate_packet(
            {
                "kind": "MUHL_SELF_TRAIN_ADDRESS",
                "source_index": TRAINER_REL,
                "dests": {"name": "muhl_self_train"},
                "live_offsets": UNRESOLVED,
                "host_inference": False,
                "titan": "NOT_WRITTEN",
                "legacy_trainer_import": False,
                "legacy_trainer_execute": False,
                "xproc": DEFERRED,
                "h006": "INTEGRATED",
            }
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("candidate", row["note"].lower())

    def test_taking_kind_is_carrier_only(self):
        row = validate_packet({"kind": "TAKING"})
        self.assertEqual(row["state"], "CARRIER_ONLY")
        self.assertEqual(row["z"], "FINDER-UNVERIFIED")

    def test_parses_named_dests_from_file(self):
        path = os.path.join(ROOT, TRAINER_REL)
        with open(path, encoding="utf-8") as handle:
            parsed = parse_trainer_source(handle.read())
        self.assertTrue(parsed["ok"], parsed)
        dests = parsed["dests"]
        self.assertEqual(dests["name"], "muhl_self_train")
        self.assertEqual(dests["reservoir_input"], 40_022_599_232)
        self.assertEqual(dests["intake_header"], 24)
        self.assertEqual(dests["intake_capacity"], 50 * (1 << 30))
        self.assertEqual(dests["weight_bytes"], 214)
        self.assertEqual(dests["nw"], 107)
        self.assertEqual(dests["nf"], 9)
        self.assertEqual(dests["h"], 8)
        self.assertEqual(dests["ncls"], 3)
        self.assertEqual(dests["ptr_bits"], 30)
        self.assertEqual(dests["file_marker"], "MUHLFILE")
        self.assertEqual(dests["receiver"], "muhl_reservoir")
        self.assertEqual(dests["write_ptr_rel"], 0)
        self.assertEqual(dests["size_rel"], 8)
        self.assertEqual(dests["capacity_rel"], 16)
        self.assertEqual(dests["data_start_rel"], 24)
        self.assertEqual(parsed["live_offsets"]["intake_off"], UNRESOLVED)
        self.assertEqual(parsed["live_offsets"]["weights_off"], UNRESOLVED)
        self.assertEqual(parsed["live_offsets"]["circuit_off"], UNRESOLVED)
        conflict_ids = {item["id"] for item in parsed["conflicts"]}
        self.assertIn("intake_capacity_comment", conflict_ids)
        self.assertIn("ptr_bits_vs_capacity", conflict_ids)
        for item in parsed["conflicts"]:
            self.assertEqual(item["state"], SOURCE_CONFLICT)
            self.assertIn("UNRESOLVED", item["note"])

    def test_synthetic_packet_matches_source(self):
        path = os.path.join(ROOT, TRAINER_REL)
        with open(path, encoding="utf-8") as handle:
            parsed = parse_trainer_source(handle.read())
        packet = synthetic_packet(parsed)
        verdict = validate_packet(packet, parsed=parsed)
        self.assertEqual(verdict["state"], "SYNTHETIC_OK", verdict)

    def test_does_not_import_legacy_trainer(self):
        self.assertFalse(trainer_imported())
        for name in FORBIDDEN_IMPORTS:
            self.assertNotIn(name, sys.modules)

    def test_live_tree_has_the_leftover(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["card_present"])
        self.assertTrue(row["contract_present"])
        self.assertTrue(row["test_present"])
        self.assertTrue(row["trainer_present"])
        self.assertTrue(row["parsed_ok"])
        self.assertEqual(row["dests"]["reservoir_input"], 40_022_599_232)
        self.assertEqual(row["live_offsets"]["intake_off"], UNRESOLVED)
        self.assertEqual(row["xproc"], DEFERRED)
        self.assertIn(row["h006"]["state"], (CANDIDATE, UNRESOLVED))
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(SLACK_TS, "1787648830.269449")
        self.assertEqual(TAKING_ID, "muhl-self-train-address-contract-20260825-01")
        self.assertFalse(row["legacy_import"])
        self.assertIn(os.path.join("ground", "EXECUTE.md"), SEARCH_SPACE)
        verdict = classify(row)
        self.assertEqual(verdict["state"], "INTEGRATED", verdict)

    def test_h006_missing_is_unresolved_not_zero(self):
        missing = classify_h006(os.path.join(ROOT, "does-not-exist"))
        if missing["state"] == UNRESOLVED:
            self.assertEqual(missing.get("z"), "FINDER-UNVERIFIED")
            self.assertIn("never 0", missing["note"].lower())
            self.assertNotEqual(missing.get("paths"), 0)


if __name__ == "__main__":
    unittest.main()
