from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC_SOURCES = ROOT / "revenue" / "aquatrace_ops_acceptance" / "public_sources.json"
RECEIPT = ROOT / "p" / "AT-GROK-OPS-ACCEPTANCE-01.md"

EXPECTED_HTTP_200 = {
    "identity_mfa_session": "https://pages.nist.gov/800-63-3/sp800-63b.html",
    "tenant_lab_rbac": "https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final",
    "encryption_secrets": "https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final",
    "monitoring": "https://csrc.nist.gov/pubs/sp/800/92/final",
    "backup_restore_dr": "https://csrc.nist.gov/pubs/sp/800/34/r1/final",
    "support_incident_response": "https://csrc.nist.gov/pubs/sp/800/61/r2/final",
    "accessibility": "https://www.w3.org/TR/WCAG22/",
}
EXPECTED_UNKNOWN = {"training_uat", "buyer_signoff"}


class AquaTracePublicSourceCustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = json.loads(PUBLIC_SOURCES.read_text(encoding="utf-8"))
        cls.receipt = RECEIPT.read_text(encoding="utf-8")

    def test_frozen_snapshot_records_exact_historical_observations(self) -> None:
        self.assertEqual(self.snapshot["schema"], "commons-aquatrace-ops-acceptance/v1")
        self.assertEqual(self.snapshot["measured_at"], "2026-08-31T07:34:07Z")
        by_id = {row["id"]: row for row in self.snapshot["sources"]}
        self.assertEqual(set(by_id), set(EXPECTED_HTTP_200) | EXPECTED_UNKNOWN)
        for source_id, expected_url in EXPECTED_HTTP_200.items():
            row = by_id[source_id]
            self.assertEqual(row["kind"], "CRITERIA_CITE")
            self.assertEqual(row["http_status"], 200)
            self.assertEqual(row["url"], expected_url)
            self.assertNotEqual(row["title"], "UNKNOWN")
        for source_id in EXPECTED_UNKNOWN:
            row = by_id[source_id]
            self.assertEqual(row["kind"], "UNKNOWN")
            self.assertIsNone(row["http_status"])
            self.assertEqual(row["url"], "UNKNOWN")
            self.assertEqual(row["title"], "UNKNOWN")

    def test_receipt_states_snapshot_custody_not_live_revalidation(self) -> None:
        self.assertIn(
            "Frozen `revenue/aquatrace_ops_acceptance/public_sources.json` records HTTP 200 observations",
            self.receipt,
        )
        self.assertIn("The executable battery does not revalidate those URLs", self.receipt)
        self.assertIn("not a live-network claim", self.receipt)
        self.assertNotIn("Public criteria URLs measured HTTP 200", self.receipt)


if __name__ == "__main__":
    unittest.main()
