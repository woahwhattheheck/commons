#!/usr/bin/env python3
"""Exact non-actuating canary for the cure-fold first-target choice."""

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
CHOICE = ROOT / "ground" / "owner_walls" / "cure-fold-first-target-20260830-01.json"
RECEIPT = ROOT / "p" / "demon-cure-fold-first-target-20260830-01.md"
NBITS = 0x17023AD4
TARGET_INT = 213572157266439505242940871974495870228360734370168832
TARGET_BE = "000000000000000000023ad40000000000000000000000000000000000000000"
TARGET_LE = "0000000000000000000000000000000000000000d43a02000000000000000000"
TARGET_LE_SHA256 = "be16de28c0358774add1605a2c5e8aa1fe2c6ea3ed98eaedc8ce377ab467e9e0"


class CureFoldFirstTargetTests(unittest.TestCase):
    def setUp(self):
        self.choice = json.loads(CHOICE.read_text(encoding="utf-8"))

    def test_compact_bits_reference_vector(self):
        exponent = NBITS >> 24
        mantissa = NBITS & 0xFFFFFF
        target = mantissa << (8 * (exponent - 3))
        self.assertEqual(target, TARGET_INT)
        self.assertEqual(target.to_bytes(32, "big").hex(), TARGET_BE)
        little = target.to_bytes(32, "little")
        self.assertEqual(little.hex(), TARGET_LE)
        self.assertEqual(len(little), 32)
        self.assertEqual(target.bit_length(), 178)
        self.assertEqual(256 - target.bit_length(), 78)
        self.assertEqual(hashlib.sha256(little).hexdigest(), TARGET_LE_SHA256)
        self.assertNotEqual(little, bytes.fromhex("ff" * 32))

    def test_choice_binds_target_to_same_job(self):
        self.assertEqual(self.choice["state"], "CHOICE_ONLY")
        self.assertEqual(self.choice["rule"], "SAME_JOB_LIVE_STRATUM_TARGET")
        self.assertTrue(self.choice["binding"]["never_mix_target_and_header_jobs"])
        self.assertFalse(self.choice["binding"]["hard_code_live_target"])
        vector = self.choice["reference_vector"]
        self.assertEqual(vector["nbits_hex"], "0x17023ad4")
        self.assertEqual(vector["target_be_hex"], TARGET_BE)
        self.assertEqual(vector["cli_target32_le_hex"], TARGET_LE)

    def test_existing_header_tool_emits_little_endian_target(self):
        source = (ROOT / "host" / "muhl_fold_header_add.py").read_text(encoding="utf-8")
        self.assertIn('target_int.to_bytes(PACKED_TARGET32, "little")', source)
        self.assertIn('nbits = struct.unpack("<I", prefix76[72:76])[0]', source)
        self.assertIn("target_int = mant << (8 * (exp - 3))", source)

    def test_shared_wall_surfaces_name_the_choice(self):
        directives = (ROOT / "DIRECTIVES.md").read_text(encoding="utf-8")
        unfinished = (ROOT / "muhl" / "docs" / "UNFINISHED.md").read_text(encoding="utf-8")
        self.assertIn("cure-fold first target — **PICKED:** `SAME_JOB_LIVE_STRATUM_TARGET`", directives)
        self.assertIn("### 13. Cure fold first target — PICKED", unfinished)
        self.assertIn("same live Stratum job/header", unfinished)

    def test_no_actuation_claim(self):
        for value in self.choice["boundary"].values():
            if isinstance(value, bool) and value not in (
                self.choice["boundary"]["no_auth"],
                self.choice["boundary"]["no_gate"],
            ):
                self.assertFalse(value)
        self.assertTrue(self.choice["boundary"]["no_auth"])
        self.assertTrue(self.choice["boundary"]["no_gate"])
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("No live target, run, write, pulse, fire, submission, or profit is claimed.", receipt)


if __name__ == "__main__":
    unittest.main()
