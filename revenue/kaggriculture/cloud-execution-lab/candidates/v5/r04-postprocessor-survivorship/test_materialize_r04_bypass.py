# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import materialize_r04_bypass as m

EXACT_CONFIG = b'''{
  "consumer": "frozen",
  "seed": true,
  "funding": true,
  "terminal_route": false,
  "committed": true,
  "budget_seconds": 1.0,
  "reserve_seconds": 0.01,
  "terminal_history": false,
  "redundant_hire": true,
  "fourth_quadrant": false,
  "market_pressure": true,
  "committed_seed_retry": false,
  "operating_stock": true,
  "idle_fertilizer": true,
  "crop_release": true,
  "early_capital": true,
  "town_procurement": true
}
'''


class R04BypassSurvivorshipTest(unittest.TestCase):
    def baseline(self):
        return {
            "TITAN-CONFIG.json": EXACT_CONFIG,
            "main.py": b"print('retained')\n",
            "reference/x.txt": b"x\n",
        }

    def test_exact_config_identity_and_aggregate_change(self):
        self.assertEqual(m.digest(EXACT_CONFIG), m.BASELINE_CONFIG_SHA256)
        baseline = self.baseline()
        treatment = m.treatment_members(baseline)
        self.assertEqual(
            [name for name, body in baseline.items() if body != treatment[name]],
            ["TITAN-CONFIG.json"],
        )
        self.assertEqual(m.digest(treatment["TITAN-CONFIG.json"]), m.TREATMENT_CONFIG_SHA256)
        config = json.loads(treatment["TITAN-CONFIG.json"])
        for key, (_before, after) in m.CHANGES.items():
            self.assertEqual(config[key], after)
        self.assertEqual(treatment["main.py"], baseline["main.py"])
        self.assertEqual(treatment["reference/x.txt"], baseline["reference/x.txt"])

    def test_wrong_shared_flag_is_rejected(self):
        baseline = self.baseline()
        baseline["TITAN-CONFIG.json"] = EXACT_CONFIG.replace(
            b'"early_capital": true', b'"early_capital": false'
        )
        with self.assertRaisesRegex(ValueError, "exact production-recovery config"):
            m.treatment_members(baseline)

    def test_wrong_consumer_is_rejected(self):
        baseline = self.baseline()
        baseline["TITAN-CONFIG.json"] = EXACT_CONFIG.replace(
            b'"consumer": "frozen"', b'"consumer": "parent"'
        )
        with self.assertRaisesRegex(ValueError, "exact production-recovery config"):
            m.treatment_members(baseline)

    def test_receipt_binds_full_aggregate_and_only_config_member(self):
        baseline = self.baseline()
        treatment = m.treatment_members(baseline)
        packed = m.archive_bytes(treatment)
        receipt = m.receipt_for(baseline, treatment, packed)
        self.assertEqual(receipt["changed_members"], ["TITAN-CONFIG.json"])
        self.assertEqual(receipt["baseline_config_sha256"], m.BASELINE_CONFIG_SHA256)
        self.assertEqual(receipt["treatment"]["config_sha256"], m.TREATMENT_CONFIG_SHA256)
        self.assertEqual(receipt["treatment"]["archive_sha256"], m.digest(packed))
        self.assertEqual(set(receipt["treatment"]["config_changes"]), set(m.CHANGES))
        self.assertEqual(receipt["semantic_topology"]["status"], "AUTHENTICATED")
        self.assertEqual(receipt["native_economics_status"], "PENDING_BASE_PRODUCTION_PANEL")
        self.assertTrue(receipt["kaggle_submission_hold"])

    def test_archive_bytes_are_deterministic_and_canonical(self):
        treatment = m.treatment_members(self.baseline())
        first = m.archive_bytes(treatment)
        second = m.archive_bytes(treatment)
        self.assertEqual(first, second)
        self.assertEqual(m.parse_archive_bytes(first, m.digest(first)), treatment)

    def test_parser_rejects_nonregular_member(self):
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w:gz") as archive:
            info = tarfile.TarInfo("bad-link")
            info.type = tarfile.SYMTYPE
            info.linkname = "TITAN-CONFIG.json"
            archive.addfile(info)
        payload = raw.getvalue()
        with self.assertRaisesRegex(ValueError, "Noncanonical archive member"):
            m.parse_archive_bytes(payload, m.digest(payload))

    def test_parser_rejects_wrong_identity(self):
        payload = m.archive_bytes(self.baseline())
        with self.assertRaisesRegex(ValueError, "Archive identity mismatch"):
            m.parse_archive_bytes(payload, "0" * 64)

    def test_semantic_topology_accepts_bound_fixture(self):
        members = {
            "runtime.py": b"alpha\nrequired-one\nrequired-two\n",
            "controller.py": b"controller-anchor\n",
        }
        expected = {name: m.digest(body) for name, body in members.items()}
        anchors = {
            "runtime.py": (b"required-one", b"required-two"),
            "controller.py": (b"controller-anchor",),
        }
        m.verify_semantic_topology(members, expected, anchors)

    def test_semantic_topology_rejects_missing_anchor_even_with_bound_hash(self):
        members = {"runtime.py": b"alpha\n"}
        expected = {"runtime.py": m.digest(members["runtime.py"])}
        with self.assertRaisesRegex(ValueError, "topology anchor mismatch"):
            m.verify_semantic_topology(
                members, expected, {"runtime.py": (b"required-anchor",)}
            )

    def test_publish_pair_success_is_exact(self):
        packed = b"complete archive bytes"
        receipt = {"schema": "test", "archive_sha256": m.digest(packed)}
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "treatment.tar.gz"
            receipt_path = Path(td) / "treatment.json"
            m.publish_pair(out, receipt_path, packed, receipt)
            self.assertEqual(out.read_bytes(), packed)
            self.assertEqual(receipt_path.read_bytes(), m._receipt_bytes(receipt))

    def test_receipt_collision_never_publishes_archive(self):
        packed = b"complete archive bytes"
        receipt = {"schema": "test"}
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "treatment.tar.gz"
            receipt_path = Path(td) / "treatment.json"
            receipt_path.write_bytes(b"hostile")
            with self.assertRaises(FileExistsError):
                m.publish_pair(out, receipt_path, packed, receipt)
            self.assertFalse(out.exists())
            self.assertEqual(receipt_path.read_bytes(), b"hostile")

    def test_archive_collision_rolls_back_owned_receipt(self):
        packed = b"complete archive bytes"
        receipt = {"schema": "test"}
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "treatment.tar.gz"
            receipt_path = Path(td) / "treatment.json"
            out.write_bytes(b"hostile")
            with self.assertRaises(FileExistsError):
                m.publish_pair(out, receipt_path, packed, receipt)
            self.assertEqual(out.read_bytes(), b"hostile")
            self.assertFalse(receipt_path.exists())


if __name__ == "__main__":
    unittest.main()
