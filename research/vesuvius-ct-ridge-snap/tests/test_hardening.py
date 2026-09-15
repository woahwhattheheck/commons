from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import (  # noqa: E402
    AuditConfig,
    ContractError,
    audit_surface,
    build_receipt,
    canonical_json_bytes,
    load_calibration,
    sha256_tree,
    verify_receipt,
)


def _fixture():
    shape = (17, 17, 17)
    labels = np.zeros(shape, dtype=np.uint8)
    labels[7, 3:14, 3:14] = 1
    z = np.arange(shape[0], dtype=np.float32)[:, None, None]
    ct = np.broadcast_to(np.exp(-0.5 * ((z - 9.0) / 0.65) ** 2), shape).copy()
    return ct, labels


class HardeningTests(unittest.TestCase):
    def _receipt(self):
        ct, labels = _fixture()
        audit = audit_surface(ct, labels, AuditConfig(min_global_review_fraction=0.2))
        calibration = load_calibration(ROOT / "real_derived_calibration.json")
        d = "1" * 64
        manifest = {
            "format": "vesuvius-ct-ridge-snap/v1",
            "ct": {"kind": "npy", "path": "ct.npy", "sha256": d},
            "labels": {"kind": "npy", "path": "labels.npy", "sha256": d},
            "train_regions": [],
            "eval_regions": [],
        }
        return build_receipt(
            manifest=manifest,
            input_digests={"ct_sha256": d, "labels_sha256": d},
            audit=audit,
            calibration=calibration,
            artifacts={"report.json": "2" * 64},
        )

    @staticmethod
    def _remint(receipt):
        body = dict(receipt)
        body.pop("receipt_sha256", None)
        receipt["receipt_sha256"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()

    def test_zarr_root_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target"
            target.mkdir()
            (target / "zarr.json").write_text("{}", encoding="utf-8")
            link = root / "link.zarr"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(ContractError):
                sha256_tree(link)

    def test_receipt_decision_cannot_be_self_reminted(self):
        receipt = self._receipt()
        receipt["audit_summary"]["decision"] = (
            "ABSTAIN" if receipt["audit_summary"]["decision"] == "REVIEW" else "REVIEW"
        )
        self._remint(receipt)
        self.assertFalse(verify_receipt(receipt))

    def test_receipt_offset_bounds_cannot_be_self_reminted(self):
        receipt = self._receipt()
        receipt["audit_summary"]["median_accepted_offset"] = 99.0
        receipt["audit_summary"]["max_abs_accepted_offset"] = 99.0
        self._remint(receipt)
        self.assertFalse(verify_receipt(receipt))


if __name__ == "__main__":
    unittest.main()
