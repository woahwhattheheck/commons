#!/usr/bin/env python3
"""Exact non-actuating canary for the cure-fold first-target choice."""

import hashlib
import json
from pathlib import Path
import unittest

from host.bitcoin_compact import compact_target, target_for_job


ROOT = Path(__file__).resolve().parent
CHOICE = ROOT / "ground" / "owner_walls" / "cure-fold-first-target-20260830-01.json"
RECEIPT = ROOT / "p" / "demon-cure-fold-first-target-20260830-01.md"
SOURCE = ROOT / "muhl" / "docs" / "MUHL_FOLD_PORT_MAP.md"
NBITS = 0x17023AD4
TARGET_INT = 213572157266439505242940871974495870228360734370168832
TARGET_BE = "000000000000000000023ad40000000000000000000000000000000000000000"
TARGET_LE = "0000000000000000000000000000000000000000d43a02000000000000000000"
TARGET_LE_SHA256 = "be16de28c0358774add1605a2c5e8aa1fe2c6ea3ed98eaedc8ce377ab467e9e0"
FALSE_BOUNDARIES = (
    "live_target_claimed",
    "live_run_executed",
    "go",
    "fire_337",
    "pulse_78",
    "titan_written",
    "block_submitted",
    "profitability_claimed",
)
TRUE_BOUNDARIES = (
    "no_commons_auth_gate_added",
    "no_commons_admission_gate_added",
)


class CureFoldFirstTargetTests(unittest.TestCase):
    def setUp(self):
        self.choice = json.loads(CHOICE.read_text(encoding="utf-8"))

    def test_compact_bits_reference_vector(self):
        target = compact_target(NBITS)
        self.assertEqual(target, TARGET_INT)
        self.assertEqual(target.to_bytes(32, "big").hex(), TARGET_BE)
        little = target.to_bytes(32, "little")
        self.assertEqual(little.hex(), TARGET_LE)
        self.assertEqual(len(little), 32)
        self.assertEqual(target.bit_length(), 178)
        self.assertEqual(256 - target.bit_length(), 78)
        self.assertEqual(hashlib.sha256(little).hexdigest(), TARGET_LE_SHA256)
        self.assertNotEqual(little, bytes.fromhex("ff" * 32))

    def test_choice_exactly_binds_target_to_same_job(self):
        self.assertEqual(self.choice["state"], "CHOICE_ONLY")
        self.assertEqual(self.choice["rule"], "SAME_JOB_LIVE_STRATUM_TARGET")
        self.assertEqual(self.choice["binding"], {
            "target_from": "valid nbits of the exact same live Stratum job/header used for the candidate run",
            "never_mix_target_and_header_jobs": True,
            "hard_code_live_target": False,
            "target_kind": "BITCOIN_NETWORK_BLOCK_TARGET_NOT_POOL_SHARE_TARGET",
            "invalid_compact_target": "FAIL_CLOSED",
        })
        self.assertEqual(self.choice["reference_vector"], {
            "source": "muhl/docs/MUHL_FOLD_PORT_MAP.md",
            "job_id": "6a72bdc000001e1c",
            "height": 961467,
            "nbits_hex": "0x17023ad4",
            "target_int_decimal": str(TARGET_INT),
            "target_be_hex": TARGET_BE,
            "cli_target32_le_hex": TARGET_LE,
            "target_bytes": 32,
            "bit_length": 178,
            "leading_zero_bits": 78,
            "cli_target32_sha256": TARGET_LE_SHA256,
        })

    def test_measured_source_contains_same_job_and_bits(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("job_id   6a72bdc000001e1c", source)
        self.assertIn("nbits 17023ad4", source)
        self.assertIn("real target from bits 0x17023ad4", source)

    def test_runtime_binds_job_nbits_to_exact_header(self):
        prefix = bytearray(76)
        prefix[72:76] = NBITS.to_bytes(4, "little")
        nbits, target = target_for_job({"nbits": "17023ad4"}, bytes(prefix))
        self.assertEqual(nbits, NBITS)
        self.assertEqual(target, TARGET_INT)
        with self.assertRaisesRegex(ValueError, "mismatch"):
            target_for_job({"nbits": "17023ad5"}, bytes(prefix))

    def test_invalid_compact_targets_fail_closed(self):
        for invalid in (0, 0x01800000, 0x23010000, -1, 0x100000000):
            with self.subTest(nbits=invalid):
                with self.assertRaises(ValueError):
                    compact_target(invalid)

    def test_existing_header_tool_emits_little_endian_target(self):
        header_source = (ROOT / "host" / "muhl_fold_header_add.py").read_text(encoding="utf-8")
        compact_source = (ROOT / "host" / "bitcoin_compact.py").read_text(encoding="utf-8")
        self.assertIn('target_int.to_bytes(PACKED_TARGET32, "little")', header_source)
        self.assertIn("target_for_job(job, prefix76)", header_source)
        self.assertIn('header_nbits = struct.unpack("<I", prefix76[72:76])[0]', compact_source)
        self.assertIn("job/header nbits mismatch", compact_source)
        self.assertIn("compact target overflows 256 bits", compact_source)

    def test_living_directive_and_harvest_boundaries(self):
        directives = (ROOT / "DIRECTIVES.md").read_text(encoding="utf-8")
        unfinished = (ROOT / "muhl" / "docs" / "UNFINISHED.md").read_text(encoding="utf-8")
        self.assertIn("header @184 yes/no — **PICKED: YES**", directives)
        self.assertIn("cure-fold first target — **PICKED:** `SAME_JOB_LIVE_STRATUM_TARGET`", directives)
        self.assertIn("feature-film organ — **INTEGRATED:**", directives)
        self.assertIn("zero walls remain", directives)
        self.assertIn("### 12. @184 host write-ban yes or no", unfinished)
        self.assertIn("### 13. Cure fold first target", unfinished)
        self.assertIn("Not thrown.", unfinished)

    def test_no_actuation_claim_is_key_exact(self):
        boundary = self.choice["boundary"]
        self.assertEqual(set(boundary), set(FALSE_BOUNDARIES) | set(TRUE_BOUNDARIES))
        for key in FALSE_BOUNDARIES:
            self.assertIs(boundary[key], False, key)
        for key in TRUE_BOUNDARIES:
            self.assertIs(boundary[key], True, key)
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("No live target, run, write, pulse, fire, submission, or profit is claimed.", receipt)
        self.assertIn("protocol-level `mining.authorize`", receipt)


if __name__ == "__main__":
    unittest.main()
