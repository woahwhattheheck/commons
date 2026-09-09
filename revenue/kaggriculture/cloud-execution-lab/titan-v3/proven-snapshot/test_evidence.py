# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import unittest

from support import fixture, install_ledger, restore


class EvidenceBindingTests(unittest.TestCase):
    def _document(self, fx, name: str) -> dict:
        pin = next(item for item in fx.pin.evidence_ledgers if item.name == name)
        return json.loads((fx.root / pin.path).read_text())

    def _repin(self, fx, name: str, document: dict):
        payload = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()
        return install_ledger(fx, name, payload)

    def test_receipt_derives_complete_cells_and_discloses_negative_pair(self):
        fx = fixture(self)
        receipt = restore.materialize(fx.root, pin=fx.pin, run_smoke=False)
        evidence = receipt["evidence_scope"]
        self.assertEqual(evidence["status"], "BOUND_CONTROL_ONLY")
        self.assertEqual(evidence["development"]["candidate"]["W"], 2)
        self.assertEqual(evidence["held_out"]["candidate"]["W"], 1)
        self.assertEqual(evidence["held_out"]["candidate"]["L"], 1)
        self.assertEqual(evidence["held_out"]["paired"]["mean_own_cash_delta"], 0.5)
        self.assertEqual(evidence["held_out"]["paired"]["negative_cells"], 1)
        self.assertFalse(evidence["strength_boundary"]["uniform_non_regression"])
        self.assertEqual(
            evidence["strength_boundary"]["promotion"],
            "FULL_CURRENT_MATCHED_PANEL_REQUIRED",
        )

    def test_raw_ledger_hash_drift_fails_before_semantic_use(self):
        fx = fixture(self)
        pin = next(item for item in fx.pin.evidence_ledgers if item.name == "development")
        path = fx.root / pin.path
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(restore.SnapshotError, "byte count drift"):
            restore.materialize(fx.root, pin=fx.pin, run_smoke=False)

    def test_rejects_duplicate_json_keys_even_when_rehashed(self):
        fx = fixture(self)
        pin = install_ledger(fx, "development", b'{"games":[],"games":[]}')
        with self.assertRaisesRegex(restore.SnapshotError, "duplicate JSON key"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)

    def test_source_identity_mismatch_fails_after_rehash(self):
        fx = fixture(self)
        document = self._document(fx, "development")
        document["freeze"]["files"]["scheduler.py"] = "0" * 64
        pin = self._repin(fx, "development", document)
        with self.assertRaisesRegex(restore.SnapshotError, "source identity mismatch"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)

    def test_missing_cell_fails_after_rehash(self):
        fx = fixture(self)
        document = self._document(fx, "development")
        document["games"].pop()
        document["summary"]["W_T_L_first"]["candidate"]["W"] -= 1
        document["summary"]["W_T_L_first"]["candidate"]["games"] -= 1
        pin = self._repin(fx, "development", document)
        with self.assertRaisesRegex(restore.SnapshotError, "missing required cells"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)

    def test_duplicate_cell_fails_after_rehash(self):
        fx = fixture(self)
        document = self._document(fx, "development")
        document["games"].append(dict(document["games"][0]))
        document["summary"]["W_T_L_first"]["candidate"]["W"] += 1
        document["summary"]["W_T_L_first"]["candidate"]["games"] += 1
        pin = self._repin(fx, "development", document)
        with self.assertRaisesRegex(restore.SnapshotError, "duplicate cell"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)

    def test_bool_seat_is_not_accepted_as_integer(self):
        fx = fixture(self)
        document = self._document(fx, "development")
        document["games"][0]["candidate_seat"] = False
        pin = self._repin(fx, "development", document)
        with self.assertRaisesRegex(restore.SnapshotError, "must be an integer"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)

    def test_summary_lie_fails_after_rehash(self):
        fx = fixture(self)
        document = self._document(fx, "development")
        document["summary"]["W_T_L_first"]["candidate"]["W"] = 1
        pin = self._repin(fx, "development", document)
        with self.assertRaisesRegex(restore.SnapshotError, "summary mismatch"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)

    def test_paired_cash_lie_fails_after_rehash(self):
        fx = fixture(self)
        document = self._document(fx, "held_out")
        document["summary"]["paired_outcomes"][0]["own_cash_delta"] += 1
        pin = self._repin(fx, "held_out", document)
        with self.assertRaisesRegex(restore.SnapshotError, "paired outcome mismatch"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)

    def test_incomplete_game_fails_after_rehash(self):
        fx = fixture(self)
        document = self._document(fx, "held_out")
        document["games"][0]["status"] = "error"
        document["games"][0]["failure"] = "synthetic"
        pin = self._repin(fx, "held_out", document)
        with self.assertRaisesRegex(restore.SnapshotError, "cell is not complete"):
            restore.materialize(fx.root, pin=pin, run_smoke=False)


if __name__ == "__main__":
    unittest.main()
