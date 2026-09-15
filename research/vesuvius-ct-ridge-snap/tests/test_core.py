from __future__ import annotations

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
    apply_review_candidate,
    assert_disjoint_regions,
    audit_surface,
    build_bundle_bytes,
    build_receipt,
    canonical_json_bytes,
    deterministic_npz_bytes,
    load_calibration,
    load_inputs,
    sha256_file,
    validate_manifest,
    verify_bundle_bytes,
    verify_receipt,
)


def synthetic_sheet(offset: int = 2, *, flat: bool = False, random: bool = False) -> tuple[np.ndarray, np.ndarray]:
    shape = (17, 17, 17)
    labels = np.zeros(shape, dtype=np.uint8)
    labels[7, 3:14, 3:14] = 1
    if flat:
        ct = np.ones(shape, dtype=np.float32)
    elif random:
        ct = np.random.default_rng(12345).normal(0.0, 1.0, size=shape).astype(np.float32)
    else:
        z = np.arange(shape[0], dtype=np.float32)[:, None, None]
        ct = np.exp(-0.5 * ((z - (7 + offset)) / 0.65) ** 2)
        ct = np.broadcast_to(ct, shape).copy().astype(np.float32)
        yy, xx = np.mgrid[:shape[1], :shape[2]]
        ct += (0.002 * yy + 0.001 * xx)[None, :, :].astype(np.float32)
    return ct, labels


class AuditTests(unittest.TestCase):
    def test_known_offset_recovers_and_beats_noop(self):
        ct, labels = synthetic_sheet(offset=2)
        result = audit_surface(ct, labels, AuditConfig(min_global_review_fraction=0.2))
        self.assertEqual(result["summary"]["decision"], "REVIEW")
        self.assertGreater(result["summary"]["accepted_fraction"], 0.60)
        accepted = result["proposed_offset"][result["accepted"]]
        self.assertTrue(np.allclose(np.median(accepted), 2.0))
        self.assertLess(float(np.mean(np.abs(accepted - 2.0))), 0.1)
        self.assertGreater(2.0, float(np.mean(np.abs(accepted - 2.0))))

    def test_flat_signal_abstains(self):
        ct, labels = synthetic_sheet(flat=True)
        result = audit_surface(ct, labels)
        self.assertEqual(result["summary"]["decision"], "ABSTAIN")
        self.assertEqual(result["summary"]["accepted_points"], 0)

    def test_random_signal_does_not_global_review(self):
        ct, labels = synthetic_sheet(random=True)
        result = audit_surface(ct, labels, AuditConfig(min_global_review_fraction=0.60, min_consensus=0.90))
        self.assertEqual(result["summary"]["decision"], "ABSTAIN")

    def test_repeated_audit_is_bitwise_stable(self):
        ct, labels = synthetic_sheet(offset=1)
        a = audit_surface(ct, labels)
        b = audit_surface(ct, labels)
        for key in ("normals", "proposed_offset", "confidence", "preliminary", "accepted"):
            self.assertEqual(np.asarray(a[key]).tobytes(), np.asarray(b[key]).tobytes())
        self.assertEqual(canonical_json_bytes(a["summary"]), canonical_json_bytes(b["summary"]))

    def test_candidate_application_is_opt_in(self):
        ct, labels = synthetic_sheet(offset=2)
        audit = audit_surface(ct, labels, AuditConfig(min_global_review_fraction=0.2))
        default, meta0 = apply_review_candidate(labels, audit)
        moved, meta1 = apply_review_candidate(labels, audit, enabled=True)
        self.assertTrue(np.array_equal(default, labels.astype(bool)))
        self.assertFalse(meta0["enabled"])
        self.assertTrue(meta1["enabled"])
        self.assertGreater(meta1["moved"], 0)
        self.assertFalse(np.array_equal(moved, labels.astype(bool)))
        self.assertFalse(meta1["topology_preserved_claim"])

    def test_nonfinite_ct_rejected(self):
        ct, labels = synthetic_sheet(offset=1)
        ct[0, 0, 0] = np.nan
        with self.assertRaises(ContractError):
            audit_surface(ct, labels)

    def test_nonbinary_labels_rejected(self):
        ct, labels = synthetic_sheet(offset=1)
        labels[0, 0, 0] = 2
        with self.assertRaises(ContractError):
            audit_surface(ct, labels)


class ContractTests(unittest.TestCase):
    def test_overlap_guard_rejects_and_touching_boxes_pass(self):
        with self.assertRaises(ContractError):
            assert_disjoint_regions([[[0, 5], [0, 5], [0, 5]]], [[[4, 8], [0, 5], [0, 5]]])
        assert_disjoint_regions([[[0, 5], [0, 5], [0, 5]]], [[[5, 8], [0, 5], [0, 5]]])

    def test_manifest_exact_schema(self):
        d = "0" * 64
        m = {
            "format": "vesuvius-ct-ridge-snap/v1",
            "ct": {"kind": "npy", "path": "ct.npy", "sha256": d},
            "labels": {"kind": "npy", "path": "labels.npy", "sha256": d},
            "train_regions": [],
            "eval_regions": [],
        }
        self.assertEqual(validate_manifest(m)["format"], m["format"])
        bad = dict(m, extra=True)
        with self.assertRaises(ContractError):
            validate_manifest(bad)

    def test_load_inputs_binds_exact_bytes(self):
        ct, labels = synthetic_sheet(offset=1)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            np.save(root / "ct.npy", ct, allow_pickle=False)
            np.save(root / "labels.npy", labels, allow_pickle=False)
            m = {
                "format": "vesuvius-ct-ridge-snap/v1",
                "ct": {"kind": "npy", "path": "ct.npy", "sha256": sha256_file(root / "ct.npy")},
                "labels": {"kind": "npy", "path": "labels.npy", "sha256": sha256_file(root / "labels.npy")},
                "train_regions": [],
                "eval_regions": [],
            }
            got_ct, got_labels, digests = load_inputs(m, root)
            self.assertEqual(got_ct.shape, ct.shape)
            self.assertTrue(np.array_equal(got_labels, labels.astype(bool)))
            self.assertEqual(digests["ct_sha256"], m["ct"]["sha256"])
            with open(root / "ct.npy", "ab") as fh:
                fh.write(b"x")
            with self.assertRaises(ContractError):
                load_inputs(m, root)

    def test_path_traversal_rejected(self):
        d = "0" * 64
        m = {
            "format": "vesuvius-ct-ridge-snap/v1",
            "ct": {"kind": "npy", "path": "../ct.npy", "sha256": d},
            "labels": {"kind": "npy", "path": "labels.npy", "sha256": d},
            "train_regions": [],
            "eval_regions": [],
        }
        with self.assertRaises(ContractError):
            validate_manifest(m)


class ReceiptBundleTests(unittest.TestCase):
    def setUp(self):
        self.calibration = load_calibration(ROOT / "real_derived_calibration.json")
        d = "1" * 64
        self.manifest = {
            "format": "vesuvius-ct-ridge-snap/v1",
            "ct": {"kind": "npy", "path": "ct.npy", "sha256": d},
            "labels": {"kind": "npy", "path": "labels.npy", "sha256": d},
            "train_regions": [],
            "eval_regions": [],
        }
        ct, labels = synthetic_sheet(offset=2)
        self.audit = audit_surface(ct, labels, AuditConfig(min_global_review_fraction=0.2))

    def test_calibration_is_conservative_and_exact(self):
        self.assertEqual(self.calibration["sample_count"], 30)
        self.assertEqual(self.calibration["local_review_flags"], 3)
        self.assertEqual(self.calibration["default_decision"], "ABSTAIN")
        self.assertAlmostEqual(self.calibration["median_signed_offset_vox"], 0.0077)

    def test_receipt_tamper_rejected(self):
        receipt = build_receipt(
            manifest=self.manifest,
            input_digests={"ct_sha256": "1" * 64, "labels_sha256": "1" * 64},
            audit=self.audit,
            calibration=self.calibration,
            artifacts={"report.json": "2" * 64},
        )
        self.assertTrue(verify_receipt(receipt))
        receipt["authority"] = "AUTO_CORRECT"
        self.assertFalse(verify_receipt(receipt))

    def test_deterministic_npz_is_byte_stable(self):
        a = deterministic_npz_bytes({"x": np.arange(5), "y": np.eye(2)})
        b = deterministic_npz_bytes({"y": np.eye(2), "x": np.arange(5)})
        self.assertEqual(a, b)

    def test_bundle_is_deterministic_and_exact(self):
        files = {"report.json": b"{}\n", "metrics.csv": b"a,b\n1,2\n"}
        a, ma = build_bundle_bytes(files)
        b, mb = build_bundle_bytes(dict(reversed(list(files.items()))))
        self.assertEqual(a, b)
        self.assertEqual(ma, mb)
        self.assertEqual(verify_bundle_bytes(a), ma)

    def test_bundle_extra_member_rejected(self):
        bundle, _ = build_bundle_bytes({"report.json": b"{}\n"})
        import io, zipfile
        source = io.BytesIO(bundle)
        out = io.BytesIO()
        with zipfile.ZipFile(source, "r") as zin, zipfile.ZipFile(out, "w") as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))
            zout.writestr("evil.txt", b"x")
        with self.assertRaises(ContractError):
            verify_bundle_bytes(out.getvalue())

    def test_strict_json_rejects_nan(self):
        with self.assertRaises(ContractError):
            canonical_json_bytes({"x": float("nan")})


if __name__ == "__main__":
    unittest.main()
