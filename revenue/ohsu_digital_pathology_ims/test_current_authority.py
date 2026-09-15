# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import current_authority
from current_authority import _evaluate_with_verifier_root, evaluate_current
from test_qualification import HEX_B, NOW, bind_manifest, qualified_payload


def _trusted_root(p):
    return p["requirements_manifest"]["completeness_attestation"]["sha256"]


class CurrentAuthorityTests(unittest.TestCase):
    def test_matching_retained_root_can_reach_internal_ready(self):
        p = qualified_payload()
        r = _evaluate_with_verifier_root(
            p, evaluated_at=NOW, trusted_completeness_sha256=_trusted_root(p)
        )
        self.assertEqual(r["decision"], "READY_FOR_INTERNAL_BID_REVIEW")
        self.assertTrue(r["current_authority"])

    def test_missing_retained_root_holds(self):
        p = qualified_payload()
        r = _evaluate_with_verifier_root(
            p, evaluated_at=NOW, trusted_completeness_sha256=None
        )
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("TRUSTED_COMPLETENESS_ROOT_MISSING_OR_INVALID", r["holds"])

    def test_mismatched_retained_root_holds(self):
        p = qualified_payload()
        r = _evaluate_with_verifier_root(
            p, evaluated_at=NOW, trusted_completeness_sha256=HEX_B
        )
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("TRUSTED_COMPLETENESS_ROOT_MISMATCH", r["holds"])

    def test_easy_one_row_full_remint_cannot_replace_retained_root(self):
        p = qualified_payload()
        retained_root = _trusted_root(p)
        p["minimum_qualifications"] = [
            {"id": "easy", "mandatory": True, "text": "Easy synthetic substitute"}
        ]
        p["evidence"] = [
            {
                "requirement_id": "easy",
                "result": "PASS",
                "reference": "artifact://easy",
                "sha256": HEX_B,
            }
        ]
        bind_manifest(p)
        self.assertNotEqual(_trusted_root(p), retained_root)
        r = _evaluate_with_verifier_root(
            p, evaluated_at=NOW, trusted_completeness_sha256=retained_root
        )
        self.assertEqual(r["decision"], "HOLD")
        self.assertIn("TRUSTED_COMPLETENESS_ROOT_MISMATCH", r["holds"])

    def test_public_current_path_owns_root_and_clock(self):
        p = qualified_payload()
        retained_root = _trusted_root(p)
        with tempfile.TemporaryDirectory() as td:
            root_path = Path(td) / "trusted_completeness.sha256"
            root_path.write_text(retained_root + "\n", encoding="utf-8")
            with mock.patch.object(current_authority, "TRUSTED_ROOT_PATH", root_path), mock.patch.object(
                current_authority, "_utc_now_string", return_value=NOW
            ):
                r = evaluate_current(p)
        self.assertEqual(r["decision"], "READY_FOR_INTERNAL_BID_REVIEW")
        self.assertEqual(r["evaluated_at"], NOW)
        self.assertEqual(r["trusted_completeness_root_sha256"], retained_root)


if __name__ == "__main__":
    unittest.main()
