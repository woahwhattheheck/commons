from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.procurement_response_module_library.engine import Error, compile as compile_packet
from revenue.procurement_response_module_library.materialize import materialize, verify

ROOT = Path(__file__).parent
FIX = ROOT / "fixtures" / "internal_receipts.json"


def raw(x):
    return (json.dumps(x, sort_keys=True, separators=(",", ":")) + "\n").encode()


class T(unittest.TestCase):
    def setUp(self):
        self.b = FIX.read_bytes()
        self.p = json.loads(self.b)

    def test_catalog_and_authority_false(self):
        cat, diff, rec = materialize(self.b)
        c = json.loads(cat)
        self.assertEqual("procurement-response-modules/library/v1", c["schema"])
        self.assertEqual(2, len(c["evidence"]))
        self.assertEqual(2, len(c["modules"]))
        self.assertTrue(all(v is False for v in json.loads(rec)["authority"].values()))
        cert = next(x for x in c["evidence"] if x["evidence_id"] == "ev-cert-1")
        self.assertEqual("MISSING", cert["status"])
        cyber = next(m for m in c["modules"] if m["family"] == "cybersecurity")
        self.assertEqual("PENDING", cyber["owner_status"])

    def test_restricted_supported_rejected(self):
        p = copy.deepcopy(self.p)
        p["receipts"][1]["status"] = "SUPPORTED"
        self.assertRaisesRegex(Error, "cannot be SUPPORTED", materialize, raw(p))

    def test_future_rejected(self):
        p = copy.deepcopy(self.p)
        p["receipts"][0]["observed_at"] = "2026-09-17T00:00:00Z"
        self.assertRaisesRegex(Error, "future evidence", materialize, raw(p))

    def test_duplicate_receipt(self):
        p = copy.deepcopy(self.p)
        p["receipts"].append(copy.deepcopy(p["receipts"][0]))
        self.assertRaisesRegex(Error, "duplicate receipt_id", materialize, raw(p))

    def test_verify_and_tamper(self):
        cat, diff, rec = materialize(self.b)
        self.assertTrue(verify(self.b, cat, diff, rec)["verified"])
        c = json.loads(cat)
        c["authority"] = {"submission_authorized": True}
        self.assertRaisesRegex(Error, "mismatch", verify, self.b, raw(c), diff, rec)

    def test_catalog_feeds_compiler_hold_on_missing_cert(self):
        cat, _, _ = materialize(self.b)
        sol = {
            "schema": "procurement-response-modules/solicitation/v1",
            "solicitation_id": "synthetic-public-sector-rfp",
            "source_ref": "fixture://solicitation/public-sector-demo",
            "source_sha256": "1ea1454afb68bf528cfe272cb79271ac9b5330bf83fe81c8d8de226cd56e20d7",
            "observed_at": "2026-09-16T20:00:00Z",
            "generated_at": "2026-09-16T22:40:00Z",
            "source_max_age_seconds": 86400,
            "requirements": [
                {"section_id": "section-01-corporate_capability", "family": "corporate_capability", "required_tags": ["public_sector"], "required": True},
                {"section_id": "section-03-cybersecurity", "family": "cybersecurity", "required_tags": ["public_sector"], "required": True},
            ],
        }
        o = compile_packet(cat, raw(sol))
        self.assertEqual("HOLD", o.status)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            base = [sys.executable, "-m", "revenue.procurement_response_module_library.materialize"]
            a = subprocess.run(base + ["compile", "--receipts", str(FIX), "--out-dir", d], cwd=ROOT.parents[1], capture_output=True, text=True)
            self.assertEqual(0, a.returncode, a.stderr)
            b = subprocess.run(
                base + ["verify", "--receipts", str(FIX), "--catalog", d + "/catalog.json", "--diff", d + "/diff.json", "--receipt", d + "/receipt.json"],
                cwd=ROOT.parents[1], capture_output=True, text=True,
            )
            self.assertEqual(0, b.returncode, b.stderr)
            self.assertIn('"verified": true', b.stdout)


if __name__ == "__main__":
    unittest.main()
