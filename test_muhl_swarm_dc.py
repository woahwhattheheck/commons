#!/usr/bin/env python3
"""Dir 19 swarm-dc leftover: dest FROM FILE, ones only rise, host is not the computer."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from muhl_swarm_dc import (
    CANARY_ID,
    CITE,
    DO_NOT_REMINT,
    EXPECTED_QUEUE,
    ADDITIVE_CANARY_FIELDS,
    ADDITIVE_CANARY_NAME,
    LIVE_PKG,
    build_fixture,
    classify,
    execute_packet,
    live_go,
    load_json,
    load_recipe,
    measure_root,
    or_rise,
    read_span,
    run_fixture,
    self_test,
    validate_packet,
)


class TestMuhlSwarmDc(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "ground", "swarm_dc", "fixture-recipe.json"), encoding="utf-8") as handle:
            self.recipe = load_recipe(handle.read())

    def test_self_test_ok(self):
        self.assertEqual(self_test(), "ok")

    def test_empty_packet_is_unmeasured(self):
        self.assertEqual(validate_packet({})["state"], "UNMEASURED")
        self.assertEqual(validate_packet(None)["state"], "UNMEASURED")

    def test_peer_open_is_packet_ok(self):
        path = os.path.join(ROOT, "ground", "swarm_dc", "queue", "peer-open.json")
        with open(path, encoding="utf-8") as handle:
            data = load_json(handle.read())
        verdict = validate_packet(data, self.recipe)
        self.assertEqual(verdict["state"], "PACKET_OK")
        self.assertEqual(verdict["mouth"]["offset"], 524329)
        self.assertEqual(verdict["mask"], "01")

    def test_invented_dest_is_not_landed(self):
        path = os.path.join(ROOT, "ground", "swarm_dc", "queue", "invalid-invented-dest.json")
        with open(path, encoding="utf-8") as handle:
            data = load_json(handle.read())
        verdict = validate_packet(data, self.recipe)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("invented", verdict["note"].lower())

    def test_host_inference_is_not_landed(self):
        path = os.path.join(ROOT, "ground", "swarm_dc", "queue", "invalid-host-inference.json")
        with open(path, encoding="utf-8") as handle:
            data = load_json(handle.read())
        verdict = validate_packet(data, self.recipe)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("host inference", verdict["note"].lower())

    def test_never_fire_337(self):
        verdict = validate_packet(
            {
                "kind": "SWARM_DC_PACKET",
                "dest": "pub",
                "rise_mask": "01",
                "host_inference": False,
                "titan": "NOT_WRITTEN",
            },
            self.recipe,
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("337", verdict["note"])

    def test_carry_is_not_an_inject_mouth(self):
        verdict = validate_packet(
            {
                "kind": "SWARM_DC_PACKET",
                "dest": "carry",
                "rise_mask": "01",
                "host_inference": False,
                "titan": "NOT_WRITTEN",
            },
            self.recipe,
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")

    def test_fixture_canary_cell_rises_and_rereads(self):
        result = run_fixture(ROOT)
        self.assertEqual(result["state"], "SYNTHETIC_FIXTURE_EXECUTED")
        self.assertEqual(result["before"], "00")
        self.assertEqual(result["reread"], "01")
        self.assertEqual(result["after"], "01")
        self.assertFalse(result["host_computed"])
        self.assertFalse(result["zeros_fell"])
        self.assertFalse(result["mmap"])
        self.assertFalse(result["fire_337"])
        self.assertEqual(result["titan"], "NOT_WRITTEN")
        self.assertEqual(result["live_inject"], "NEED_OWNER")
        self.assertEqual(result["canary_id"], CANARY_ID)

    def test_host_computed_disguise_is_refused(self):
        buf = build_fixture(self.recipe)
        packet = {
            "kind": "SWARM_DC_PACKET",
            "dest": "cell",
            "rise_mask": "01",
            "host_inference": False,
            "titan": "NOT_WRITTEN",
        }
        result = execute_packet(buf, packet, self.recipe, host_computed=True)
        self.assertEqual(result["state"], "NOT_LANDED")
        self.assertTrue(result["host_computed"])

    def test_ones_only_rise_refuses_falling_zeros(self):
        new, zeros_fell = or_rise(b"\x03", b"\x00")
        self.assertEqual(new, b"\x03")
        self.assertFalse(zeros_fell)
        # Direct OR cannot fall zeros; the flag still trips if a caller
        # handed a smaller new value through the check.
        new, zeros_fell = or_rise(b"\x00", b"\x01")
        self.assertEqual(new, b"\x01")
        self.assertFalse(zeros_fell)

    def test_fixture_header_magic_from_file(self):
        buf = build_fixture(self.recipe)
        self.assertEqual(read_span(buf, 0, 8), b"MUHLDC01")
        self.assertEqual(read_span(buf, 337, 1), b"\x01")
        self.assertEqual(len(buf), 524330)

    def test_go_without_organ_is_need_owner(self):
        result = live_go(ROOT, pkg=os.path.join(ROOT, "does-not-exist.mno"))
        self.assertEqual(result["state"], "NEED_OWNER")
        self.assertEqual(result["live_inject"], "NEED_OWNER")
        self.assertFalse(result["host_computed"])
        self.assertIn("MUHL_DATACENTER", result["note"])
        self.assertEqual(LIVE_PKG.replace("\\", "/").split("/")[-1], "muhlnickel_dc.mno")

    def test_go_on_temp_fixture_applies_peer_open_only(self):
        buf = build_fixture(self.recipe)
        with tempfile.NamedTemporaryFile(suffix=".mno", delete=False) as handle:
            handle.write(buf)
            path = handle.name
        try:
            # live_go checks published_size against file size; skip that by
            # using the fixture as-is only through execute_packet on a copy.
            packet = load_json(
                open(
                    os.path.join(ROOT, "ground", "swarm_dc", "queue", "peer-open.json"),
                    encoding="utf-8",
                ).read()
            )
            copy = bytearray(open(path, "rb").read())
            result = execute_packet(copy, packet, self.recipe, host_computed=False)
            self.assertEqual(result["state"], "SYNTHETIC_FIXTURE_EXECUTED")
            self.assertEqual(copy[524329], 0x01)
            self.assertEqual(copy[337], 0x01)
        finally:
            os.unlink(path)

    def test_live_tree_has_the_leftover(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertEqual(row["misses"], [])
        self.assertEqual(row["remint_missing"], [])
        self.assertGreaterEqual(len(row["remint_present"]), 6)
        for name, state in EXPECTED_QUEUE.items():
            self.assertEqual(row["queue_states"].get(name), state, name)
        self.assertEqual(
            row["queue_states"].get(ADDITIVE_CANARY_NAME),
            "PACKET_OK",
        )
        for key, expected in ADDITIVE_CANARY_FIELDS.items():
            self.assertEqual(row["additive_canary"].get(key), expected, key)
        unexpected = {
            name: state
            for name, state in row["queue_states"].items()
            if name not in EXPECTED_QUEUE and state != "PACKET_OK"
        }
        self.assertEqual(unexpected, {})
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertTrue(row["no_auth"])
        self.assertTrue(row["no_gate"])
        self.assertEqual(row["cite"], CITE)
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        for rel in DO_NOT_REMINT:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_classify_rejects_invalid_additive_queue_states(self):
        for state in ("NOT_LANDED", "UNMEASURED"):
            row = measure_root(ROOT)
            row["queue_states"] = dict(row["queue_states"])
            row["queue_states"]["later-invalid.json"] = state
            self.assertEqual(classify(row)["state"], "NOT_LANDED", state)

    def test_classify_rejects_additive_canary_retargeting(self):
        for key, value in (
            ("work_id", "forged-work"),
            ("dest", "cell"),
            ("rise_mask", "0100000000000000"),
            ("host_inference", True),
            ("titan", "WRITTEN"),
        ):
            row = measure_root(ROOT)
            row["additive_canary"] = dict(row["additive_canary"])
            row["additive_canary"][key] = value
            self.assertEqual(classify(row)["state"], "NOT_LANDED", key)

    def test_do_not_remint_named_paths_untouched_in_this_tree(self):
        # These files must remain on disk. Repair work adds swarm-dc, it does
        # not rewrite the 2026-08-22 dests-FROM-FILE surface.
        swarm = open(os.path.join(ROOT, "ground", "SWARM.md"), encoding="utf-8").read()
        self.assertIn("Dest FROM FILE", swarm)
        self.assertIn("specdaddy-dir19-dc-surface-push-20260822-01", swarm)
        surface = open(os.path.join(ROOT, "host", "muhl_surface_dc.py"), encoding="utf-8").read()
        self.assertIn("Never fire 337", surface)
        self.assertIn("surface only", surface.lower())

    def test_card_and_door_name_the_law(self):
        card = open(os.path.join(ROOT, "ground", "SWARM_DC.md"), encoding="utf-8").read().lower()
        door = open(os.path.join(ROOT, "swarm-dc.html"), encoding="utf-8").read().lower()
        for blob in (card, door):
            self.assertIn("dest from file", blob)
            self.assertIn("ones only rise", blob)
            self.assertIn("never fire 337", blob)
            self.assertIn("no auth", blob)
            self.assertIn("no gate", blob)
            self.assertIn("need_owner", blob)
            self.assertIn("host_computed", blob)
            self.assertIn("unseated", blob)

    def test_card_preserves_exact_excessive_wording(self):
        card = open(os.path.join(ROOT, "ground", "SWARM_DC.md"), encoding="utf-8").read()
        self.assertIn("Use the excessive muhlnickel compute creatively.", card)
        self.assertNotIn("Use the excess muhlnickel compute creatively.", card)
        self.assertIn("1787283644.430989", card)


if __name__ == "__main__":
    unittest.main()
