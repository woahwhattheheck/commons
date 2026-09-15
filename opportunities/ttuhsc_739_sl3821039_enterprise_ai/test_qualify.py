from __future__ import annotations

import inspect
import unittest
from copy import deepcopy
from pathlib import Path

from revenue.pursuit_evidence_bridge.bridge import BridgeError, compile_bridge, load_json

from opportunities.ttuhsc_739_sl3821039_enterprise_ai import qualify


HERE = Path(__file__).resolve().parent
SOURCE_ROOT = "3d2af64d5c4c9547e3c35f7095606e0be16c6628d78dfc1de7a9c8d1eb20d729"
MANIFEST_ROOT = "3b199b5ceb4e8f1d7a5a72a46267d57d7333c8c2acc2b97f2ac8d738cf4713f3"


class TTUHSCBridgeGateTests(unittest.TestCase):
    def test_current_generation_is_literal_hold(self) -> None:
        result = qualify.evaluate_current()
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["deadline_utc"], "2026-09-21T21:30:00Z")
        self.assertIn("FIRST_PARTY_PACKET_BYTES_NOT_RETAINED", result["reason_codes"])
        self.assertIn("BUYER_ADDENDA_GENERATION_NOT_RETAINED", result["reason_codes"])
        self.assertIn("VAULT_ROOTS_NOT_PINNED", result["reason_codes"])
        self.assertFalse(result["external_submission_authorized"])
        self.assertTrue(result["authority"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

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
        changed["observed_at_utc"] = "2026-09-14T03:50:01Z"
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
