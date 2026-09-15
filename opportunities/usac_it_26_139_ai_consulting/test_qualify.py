from __future__ import annotations

import inspect
import unittest
from copy import deepcopy
from pathlib import Path

from revenue.pursuit_evidence_bridge.bridge import BridgeError, compile_bridge, load_json
from opportunities.usac_it_26_139_ai_consulting import qualify


HERE = Path(__file__).resolve().parent
SOURCE_ROOT = "36bfab21c89b94f3464b7bd06f3864eea6db0acf52ede5c3c6f6221157e49c75"
MANIFEST_ROOT = "ce47b0d480532ef8b69274899b874a8dc32cabecca8b4e464d799f22325e15d0"
SOURCE_HOLDS = {
    "BID_SHEET_BYTES_NOT_RETAINED",
    "CONFIDENTIALITY_AGREEMENT_BYTES_NOT_RETAINED",
    "CURRENT_BUYER_PAGE_GENERATION_NOT_RETAINED",
    "Q_AND_A_BYTES_NOT_RETAINED",
    "RFP_BYTES_NOT_RETAINED",
}


class USACBridgeGateTests(unittest.TestCase):
    def test_current_generation_is_literal_hold(self) -> None:
        result = qualify.evaluate_current()
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["deadline_utc"], "2026-09-30T15:00:00Z")
        self.assertTrue(SOURCE_HOLDS.issubset(set(result["reason_codes"])))
        self.assertIn("VAULT_ROOTS_NOT_PINNED", result["reason_codes"])
        self.assertFalse(result["external_submission_authorized"])
        self.assertTrue(result["authority"])
        self.assertTrue(all(value is False for value in result["authority"].values()))
        self.assertNotIn(result["status"], {"PRIME_READY", "TEAMING_READY"})

    def test_checked_in_roots_are_bound(self) -> None:
        result = qualify.evaluate_current()
        self.assertEqual(result["source_ledger"]["sha256"], SOURCE_ROOT)
        self.assertEqual(result["submission_manifest"]["sha256"], MANIFEST_ROOT)

    def test_current_wrapper_has_no_caller_clock_or_root_parameters(self) -> None:
        params = set(inspect.signature(qualify.evaluate_current).parameters)
        self.assertEqual(params, {"vault"})

    def test_runtime_vault_cannot_self_authorize_unpinned_binding(self) -> None:
        fake_vault = {"authority": {}, "registry": {}, "query": {}, "bundle": {}}
        with self.assertRaisesRegex(BridgeError, "no pinned vault roots"):
            qualify.evaluate_current(fake_vault)

    def test_source_drift_is_rejected_before_readiness(self) -> None:
        source = load_json((HERE / "source_ledger.json").read_bytes(), "source")
        manifest = load_json((HERE / "submission_manifest.json").read_bytes(), "manifest")
        changed = deepcopy(source)
        changed["observed_at_utc"] = "2026-09-14T03:40:01Z"
        with self.assertRaisesRegex(BridgeError, "source_ledger root mismatch"):
            compile_bridge(qualify.BINDING_ID, changed, manifest)

    def test_manifest_drift_is_rejected_before_readiness(self) -> None:
        source = load_json((HERE / "source_ledger.json").read_bytes(), "source")
        manifest = load_json((HERE / "submission_manifest.json").read_bytes(), "manifest")
        changed = deepcopy(manifest)
        changed["external_submission_authorized"] = True
        with self.assertRaisesRegex(BridgeError, "submission_manifest root mismatch"):
            compile_bridge(qualify.BINDING_ID, source, changed)


if __name__ == "__main__":
    unittest.main()
