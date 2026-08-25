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
    ABSOLUTE,
    BLOCKED,
    CANDIDATE,
    DEFERRED,
    FORBIDDEN_IMPORTS,
    LAST_SAFE_START,
    MAX_POINTER,
    RELATIVE,
    REQUIRED_BITS,
    SEARCH_SPACE,
    SLACK_TS,
    SOURCE_CONFLICT,
    STEPS_BEFORE_WRAP,
    TAKING_ID,
    TRAINER_REL,
    UNRESOLVED,
    bind_address_facts,
    canonical_conflict_hash,
    classify,
    classify_h006,
    measure_from_rows,
    measure_root,
    parse_trainer_source,
    payload_digest,
    pointer_space,
    registry_header_disagreement,
    synthetic_packet,
    trainer_imported,
    validate_canonical_record,
    validate_packet,
)

CANONICAL_50GIB_30BIT = (
    "d5acf732c3bd72a10e42630654ec5b5cef43a5e11b8dcab7396fcf6f4ec33165"
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
        digest = canonical_conflict_hash(
            ptr_bits=30,
            capacity=50 * (1 << 30),
            stride=2,
            address_mode=RELATIVE,
            data_start=24,
        )
        self.assertEqual(digest, CANONICAL_50GIB_30BIT)
        self.assertEqual(dests["stride"], 2)
        self.assertEqual(dests["address_mode"], RELATIVE)
        for item in parsed["conflicts"]:
            self.assertEqual(item["state"], SOURCE_CONFLICT)
            self.assertIn("UNRESOLVED", item["note"])
            self.assertIn("BLOCKED", item["note"])
            self.assertEqual(item["max_pointer"], 1_073_741_823)
            self.assertEqual(item["last_safe_start"], 1_073_741_822)
            self.assertEqual(item["steps_before_wrap"], 536_870_912)
            self.assertEqual(item["required_bits"], 36)
        pointer = next(
            item
            for item in parsed["conflicts"]
            if item["id"] == "ptr_bits_vs_capacity"
        )
        self.assertEqual(pointer["canonical_hash"], digest)
        self.assertEqual(pointer["max_pointer"], MAX_POINTER)
        self.assertEqual(pointer["last_safe_start"], LAST_SAFE_START)
        self.assertEqual(pointer["steps_before_wrap"], STEPS_BEFORE_WRAP)
        self.assertEqual(pointer["required_bits"], REQUIRED_BITS)

    def test_synthetic_packet_matches_source(self):
        path = os.path.join(ROOT, TRAINER_REL)
        with open(path, encoding="utf-8") as handle:
            parsed = parse_trainer_source(handle.read())
        packet = synthetic_packet(parsed)
        verdict = validate_packet(packet, parsed=parsed)
        self.assertEqual(verdict["state"], BLOCKED, verdict)
        self.assertEqual(verdict["max_pointer"], 1_073_741_823)
        self.assertEqual(verdict["last_safe_start"], 1_073_741_822)
        self.assertEqual(verdict["steps_before_wrap"], 536_870_912)
        self.assertEqual(verdict["required_bits"], 36)
        self.assertEqual(
            verdict["canonical_hash"],
            CANONICAL_50GIB_30BIT,
        )
        self.assertEqual(verdict["stride"], 2)
        self.assertEqual(verdict["address_mode"], RELATIVE)
        self.assertEqual(verdict["data_start"], 24)
        self.assertIn("fail-closed", verdict["note"])
        self.assertEqual(packet["live_offsets"], UNRESOLVED)

    def test_source_space_conflict_is_fail_closed_blocked(self):
        parsed = parse_trainer_source(
            "NAME = 'muhl_self_train'\n"
            "INTAKE_CAPACITY = 50 * (1 << 30)  # 1 GB\n"
            "PTR_BITS = 30\n"
            "STRIDE = 2\n"
            "ADDRESS_MODE = 'RELATIVE'\n"
            "INTAKE_HEADER = 24\n"
        )
        packet = synthetic_packet(parsed)
        verdict = validate_packet(packet, parsed=parsed)
        self.assertEqual(verdict["state"], BLOCKED, verdict)
        self.assertEqual(verdict["max_pointer"], MAX_POINTER)
        self.assertEqual(verdict["last_safe_start"], LAST_SAFE_START)
        self.assertEqual(verdict["steps_before_wrap"], STEPS_BEFORE_WRAP)
        self.assertEqual(verdict["required_bits"], REQUIRED_BITS)
        self.assertTrue(verdict["canonical_hash"])
        self.assertEqual(packet["live_offsets"], UNRESOLVED)
        classified = classify(
            measure_from_rows(
                {
                    "card_present": True,
                    "contract_present": True,
                    "test_present": True,
                    "trainer_present": True,
                    "parsed_ok": True,
                    "calibration_ok": True,
                    "conflicts": parsed["conflicts"],
                    "live_offsets": parsed["live_offsets"],
                    "dests": parsed["dests"],
                    "packet_ok": False,
                    "posting_open": True,
                    "no_auth": True,
                    "no_gate": True,
                    "found_phrases": [],
                }
            )
        )
        self.assertEqual(classified["state"], BLOCKED, classified)
        self.assertEqual(classified["max_pointer"], 1_073_741_823)

    def test_matching_source_space_stays_synthetic_ok(self):
        parsed = parse_trainer_source(
            "NAME = 'muhl_self_train'\n"
            "RESERVOIR_INPUT = 1\n"
            "INTAKE_HEADER = 24\n"
            "INTAKE_CAPACITY = 1 << 30\n"
            "WEIGHT_BYTES = 214\n"
            "NW = 107\n"
            "NF = 9\n"
            "H = 8\n"
            "NCLS = 3\n"
            "PTR_BITS = 30\n"
            "STRIDE = 2\n"
            "ADDRESS_MODE = 'RELATIVE'\n"
            "FILE_MARKER = 'MUHLFILE'\n"
            "build(receiver='muhl_reservoir')\n"
        )
        self.assertTrue(parsed["ok"], parsed)
        self.assertEqual(parsed["conflicts"], [])
        packet = synthetic_packet(parsed)
        verdict = validate_packet(packet, parsed=parsed)
        self.assertEqual(verdict["state"], "SYNTHETIC_OK", verdict)
        self.assertEqual(parsed["live_offsets"]["intake_off"], UNRESOLVED)

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
        self.assertEqual(verdict["state"], BLOCKED, verdict)
        self.assertEqual(verdict["max_pointer"], 1_073_741_823)
        self.assertEqual(verdict["last_safe_start"], 1_073_741_822)
        self.assertEqual(verdict["steps_before_wrap"], 536_870_912)
        self.assertEqual(verdict["required_bits"], 36)
        self.assertIn("fail-closed", verdict["note"])
        self.assertEqual(row["live_offsets"]["intake_off"], UNRESOLVED)

    def test_h006_missing_is_unresolved_not_zero(self):
        missing = classify_h006(os.path.join(ROOT, "does-not-exist"))
        if missing["state"] == UNRESOLVED:
            self.assertEqual(missing.get("z"), "FINDER-UNVERIFIED")
            self.assertIn("never 0", missing["note"].lower())
            self.assertNotEqual(missing.get("paths"), 0)

    def test_missing_address_facts_are_unresolved_not_named_defaults(self):
        bound = bind_address_facts({"name": "muhl_self_train"})
        self.assertEqual(bound["status"], UNRESOLVED)
        self.assertEqual(bound["max_pointer"], UNRESOLVED)
        self.assertEqual(bound["last_safe_start"], UNRESOLVED)
        self.assertEqual(bound["steps_before_wrap"], UNRESOLVED)
        self.assertEqual(bound["required_bits"], UNRESOLVED)
        self.assertEqual(bound["stride"], UNRESOLVED)
        self.assertEqual(bound["address_mode"], UNRESOLVED)
        self.assertEqual(bound["data_start"], UNRESOLVED)
        self.assertNotEqual(bound["max_pointer"], MAX_POINTER)
        self.assertIn("missing_or_malformed_ptr_bits", bound["reasons"])
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
                "h006": CANDIDATE,
            }
        )
        self.assertEqual(row["state"], UNRESOLVED)
        self.assertEqual(row["max_pointer"], UNRESOLVED)
        self.assertIn("no named-default", row["note"].lower())

    def test_malformed_header_does_not_substitute_layout(self):
        parsed = parse_trainer_source(
            "NAME = 'muhl_self_train'\n"
            "INTAKE_HEADER = 25\n"
            "INTAKE_CAPACITY = 1 << 30\n"
            "PTR_BITS = 30\n"
        )
        dests = parsed["dests"]
        self.assertEqual(dests["write_ptr_rel"], UNRESOLVED)
        self.assertEqual(dests["size_rel"], UNRESOLVED)
        self.assertEqual(dests["capacity_rel"], UNRESOLVED)
        self.assertEqual(dests["data_start_rel"], 25)

    def test_relative_one_gib_is_ok_absolute_base_unresolved(self):
        relative = parse_trainer_source(
            "NAME = 'muhl_self_train'\n"
            "RESERVOIR_INPUT = 1\n"
            "INTAKE_HEADER = 24\n"
            "INTAKE_CAPACITY = 1 << 30\n"
            "WEIGHT_BYTES = 214\n"
            "NW = 107\n"
            "NF = 9\n"
            "H = 8\n"
            "NCLS = 3\n"
            "PTR_BITS = 30\n"
            "STRIDE = 2\n"
            "ADDRESS_MODE = 'RELATIVE'\n"
            "FILE_MARKER = 'MUHLFILE'\n"
            "build(receiver='muhl_reservoir')\n"
        )
        verdict = validate_packet(synthetic_packet(relative), parsed=relative)
        self.assertEqual(verdict["state"], "SYNTHETIC_OK", verdict)
        self.assertEqual(verdict["address_mode"], RELATIVE)
        absolute = dict(relative["dests"])
        absolute["address_mode"] = ABSOLUTE
        bound = bind_address_facts(absolute)
        self.assertEqual(bound["status"], UNRESOLVED)
        self.assertEqual(bound["absolute_base"], UNRESOLVED)
        self.assertIn("missing_or_malformed_absolute_base", bound["reasons"])
        packet = synthetic_packet({"ok": True, "dests": absolute})
        row = validate_packet(packet)
        self.assertEqual(row["state"], UNRESOLVED, row)

    def test_absolute_base_overflow_is_blocked(self):
        dests = {
            "name": "muhl_self_train",
            "reservoir_input": 1,
            "intake_header": 24,
            "intake_capacity": 1 << 30,
            "weight_bytes": 214,
            "nw": 107,
            "nf": 9,
            "h": 8,
            "ncls": 3,
            "ptr_bits": 30,
            "stride": 2,
            "address_mode": ABSOLUTE,
            "absolute_base": 40_022_599_232,
            "file_marker": "MUHLFILE",
            "receiver": "muhl_reservoir",
            "write_ptr_rel": 0,
            "size_rel": 8,
            "capacity_rel": 16,
            "data_start_rel": 24,
        }
        bound = bind_address_facts(dests)
        self.assertEqual(bound["status"], BLOCKED)
        self.assertIn("absolute_base_overflow", bound["reasons"])
        packet = synthetic_packet({"ok": True, "dests": dests})
        self.assertEqual(packet["live_offsets"], UNRESOLVED)
        row = validate_packet(packet)
        self.assertEqual(row["state"], BLOCKED, row)

    def test_registry_header_disagreement_is_blocked(self):
        dests = {
            "intake_header": 24,
            "intake_capacity": 1 << 30,
            "ptr_bits": 30,
            "stride": 2,
            "address_mode": RELATIVE,
            "data_start_rel": 24,
        }
        disagree = registry_header_disagreement(
            dests,
            {
                "offset": 0,
                "header_len": 32,
                "capacity": 1 << 30,
                "data_start": 32,
            },
        )
        self.assertIsNotNone(disagree)
        self.assertEqual(disagree["state"], SOURCE_CONFLICT)
        bound = bind_address_facts(
            dests,
            registry={
                "offset": 0,
                "header_len": 32,
                "capacity": 1 << 30,
                "data_start": 32,
            },
        )
        self.assertEqual(bound["status"], BLOCKED)
        self.assertIn("registry_header_disagreement", bound["reasons"])
        missing = registry_header_disagreement(dests, None)
        self.assertEqual(missing["state"], UNRESOLVED)

    def test_tampered_and_resigned_records_are_rejected(self):
        dests = {
            "ptr_bits": 30,
            "intake_capacity": 50 * (1 << 30),
            "stride": 2,
            "address_mode": RELATIVE,
            "data_start_rel": 24,
        }
        honest = bind_address_facts(dests)
        tampered = dict(honest["canonical_payload"])
        tampered["max_pointer"] = 1
        flipped = validate_canonical_record(
            {
                "canonical_payload": tampered,
                "canonical_hash": honest["canonical_hash"],
            },
            dests=dests,
        )
        self.assertEqual(flipped["state"], "NOT_LANDED")
        self.assertIn("tampered", flipped["note"].lower())
        resigned = validate_canonical_record(
            {
                "canonical_payload": tampered,
                "canonical_hash": payload_digest(tampered),
            },
            dests=dests,
        )
        self.assertEqual(resigned["state"], "NOT_LANDED")
        self.assertTrue(
            "re-signed" in resigned["note"].lower()
            or "tampered" in resigned["note"].lower()
        )
        packet = {
            "kind": "MUHL_SELF_TRAIN_ADDRESS",
            "source_index": TRAINER_REL,
            "dests": dests,
            "live_offsets": UNRESOLVED,
            "host_inference": False,
            "titan": "NOT_WRITTEN",
            "legacy_trainer_import": False,
            "legacy_trainer_execute": False,
            "xproc": DEFERRED,
            "h006": CANDIDATE,
            "canonical_payload": tampered,
            "canonical_hash": payload_digest(tampered),
        }
        row = validate_packet(packet)
        self.assertEqual(row["state"], "NOT_LANDED", row)

    def test_non_divisor_stride_uses_full_stride_and_modular_cycle(self):
        space = pointer_space(
            ptr_bits=8,
            capacity=256,
            stride=3,
            address_mode=RELATIVE,
        )
        self.assertEqual(space["max_pointer"], 255)
        self.assertEqual(space["last_safe_start"], 253)
        self.assertNotEqual(space["last_safe_start"], 254)
        self.assertEqual(space["steps_before_wrap"], 256)
        self.assertNotEqual(space["steps_before_wrap"], 256 // 3)
        shared = pointer_space(ptr_bits=8, capacity=256, stride=6)
        self.assertEqual(shared["last_safe_start"], 250)
        self.assertEqual(shared["steps_before_wrap"], 128)
        self.assertNotEqual(shared["steps_before_wrap"], 256 // 6)
        two_byte = pointer_space(ptr_bits=30, capacity=50 * (1 << 30), stride=2)
        self.assertEqual(two_byte["last_safe_start"], LAST_SAFE_START)
        self.assertEqual(two_byte["steps_before_wrap"], STEPS_BEFORE_WRAP)
        dests = {
            "ptr_bits": 8,
            "intake_capacity": 256,
            "stride": 3,
            "address_mode": RELATIVE,
            "data_start_rel": 24,
        }
        bound = bind_address_facts(dests)
        self.assertEqual(bound["last_safe_start"], 253)
        self.assertEqual(bound["steps_before_wrap"], 256)
        packet = synthetic_packet({"ok": True, "dests": dests})
        verdict = validate_packet(packet)
        self.assertEqual(verdict["last_safe_start"], 253, verdict)
        self.assertEqual(verdict["steps_before_wrap"], 256, verdict)

    def test_absolute_non_divisor_keeps_full_stride_and_modular_cycle(self):
        dests = {
            "name": "muhl_self_train",
            "reservoir_input": 1,
            "intake_header": 24,
            "intake_capacity": 256,
            "weight_bytes": 214,
            "nw": 107,
            "nf": 9,
            "h": 8,
            "ncls": 3,
            "ptr_bits": 8,
            "stride": 3,
            "address_mode": ABSOLUTE,
            "absolute_base": 10,
            "file_marker": "MUHLFILE",
            "receiver": "muhl_reservoir",
            "write_ptr_rel": 0,
            "size_rel": 8,
            "capacity_rel": 16,
            "data_start_rel": 24,
        }
        space = pointer_space(
            ptr_bits=8,
            capacity=256,
            stride=3,
            address_mode=ABSOLUTE,
            absolute_base=10,
        )
        self.assertEqual(space["last_safe_start"], 253)
        self.assertNotEqual(space["last_safe_start"], 254)
        self.assertEqual(space["steps_before_wrap"], 256)
        self.assertNotEqual(space["steps_before_wrap"], 256 // 3)
        bound = bind_address_facts(dests)
        self.assertEqual(bound["status"], BLOCKED)
        self.assertIn("absolute_base_overflow", bound["reasons"])
        self.assertEqual(bound["last_safe_start"], 253)
        self.assertEqual(bound["steps_before_wrap"], 256)
        self.assertEqual(bound["absolute_base"], 10)
        packet = synthetic_packet({"ok": True, "dests": dests})
        row = validate_packet(packet)
        self.assertEqual(row["state"], BLOCKED, row)
        self.assertEqual(row["last_safe_start"], 253)
        self.assertEqual(row["steps_before_wrap"], 256)
        zero_base = dict(dests)
        zero_base["absolute_base"] = 0
        aligned = bind_address_facts(zero_base)
        self.assertEqual(aligned["last_safe_start"], 253)
        self.assertEqual(aligned["steps_before_wrap"], 256)
        self.assertEqual(aligned["absolute_base"], 0)


if __name__ == "__main__":
    unittest.main()
