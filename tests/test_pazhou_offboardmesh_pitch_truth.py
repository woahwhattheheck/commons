from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CARRIER = ROOT / "competitions" / "pazhou_overseas_offboardmesh_2026"
MODULE_PATH = CARRIER / "offboardmesh.py"
EXAMPLE_PATH = CARRIER / "example-candidate.json"
PITCH_PATH = CARRIER / "pitch_deck.md"

spec = importlib.util.spec_from_file_location("offboardmesh_pitch_truth", MODULE_PATH)
assert spec and spec.loader
offboardmesh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offboardmesh)


class OffboardMeshPitchTruthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pitch = PITCH_PATH.read_text(encoding="utf-8")
        cls.candidate = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        cls.packet = offboardmesh.compile_packet(cls.candidate)

    def test_pitch_uses_only_executable_review_state(self):
        states = {task["reviewState"] for task in self.packet["tasks"]}
        self.assertEqual(states, {"OWNER_REVIEW_REQUIRED"})
        self.assertIn("`OWNER_REVIEW_REQUIRED`", self.pitch)
        self.assertNotIn("`OWNER_REVIEW_READY`", self.pitch)
        self.assertNotIn("`OWNER_INPUT_REQUIRED`", self.pitch)
        self.assertNotIn("`OWNER_EXECUTION_REQUIRED`", self.pitch)

    def test_pitch_does_not_claim_authenticated_owner_evidence(self):
        truth = self.packet["truth"]
        self.assertFalse(truth["ownerEvidenceBound"])
        self.assertEqual(truth["evidenceProvenance"], "CALLER_ASSERTED_UNVERIFIED")
        self.assertIn("`ownerEvidenceBound:false`", self.pitch)
        self.assertIn("`CALLER_ASSERTED_UNVERIFIED`", self.pitch)
        self.assertNotIn("task-level owner evidence binding", self.pitch.lower())

    def test_pitch_keeps_execution_outside_system(self):
        self.assertTrue(all(task["executionAuthorized"] is False for task in self.packet["tasks"]))
        self.assertTrue(all(value is False for value in self.packet["authority"].values()))
        self.assertIn("human owner reviews and executes approved actions outside the system", self.pitch)
        self.assertIn("every task has `executionAuthorized:false`", self.pitch)


if __name__ == "__main__":
    unittest.main()
