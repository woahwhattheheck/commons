#!/usr/bin/env python3
"""Exact-byte and discovery contract for the KITE Task Forge R0 resource."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
ARTIFACT = ROOT / "artifacts" / "KITE_TASK_FORGE_0_R0.jsonl"
SIDECAR = ROOT / "artifacts" / "KITE_TASK_FORGE_0_R0.sha256"
EXPECTED_SHA256 = "2597ac55ff5b04e7584d0c786e7f93f8ae5a182b6e2788f1e07b0fc33ad98cff"


class TaskForgeResourceTests(unittest.TestCase):
    def test_frozen_pack_is_exact_balanced_and_open(self) -> None:
        raw = ARTIFACT.read_bytes()
        self.assertEqual(len(raw), 45_578)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), EXPECTED_SHA256)
        self.assertEqual(
            SIDECAR.read_text(encoding="utf-8").strip(),
            EXPECTED_SHA256 + "  KITE_TASK_FORGE_0_R0.jsonl",
        )

        records = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
        self.assertEqual(len(records), 32)
        self.assertEqual(
            [row["record_id"] for row in records],
            [f"KTF0-{index:03d}" for index in range(32)],
        )
        self.assertEqual({row["status"] for row in records}, {"accepted"})
        self.assertEqual({row["license"] for row in records}, {"CC0-1.0"})
        self.assertEqual({row["provenance"]["method"] for row in records}, {"clean-room"})
        self.assertEqual(
            Counter(row["domain"] for row in records),
            Counter(
                {
                    "code_repair": 8,
                    "causal_reasoning": 8,
                    "systems_spec_reasoning": 8,
                    "epistemic_honesty": 8,
                }
            ),
        )

    def test_human_door_binds_the_exact_pack(self) -> None:
        page = (ROOT / "task-forge.html").read_text(encoding="utf-8")

        for marker in (
            "./artifacts/KITE_TASK_FORGE_0_R0.jsonl",
            "./artifacts/KITE_TASK_FORGE_0_R0.sha256",
            EXPECTED_SHA256,
            "45,578",
            "32 lines",
            "CC0-1.0",
            "Thirteen rubric records require semantic judgment",
            "No account, intake, identity, payment, or permission step",
        ):
            self.assertIn(marker, page)

        self.assertNotIn("buy.stripe.com", page)
        self.assertNotIn("checkout", page.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
