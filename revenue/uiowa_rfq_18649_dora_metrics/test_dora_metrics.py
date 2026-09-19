from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dora_metrics import DataError, calculate, load_deployments

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures" / "synthetic_deployments.csv"
MISSING = ROOT / "fixtures" / "missing_evidence.csv"


class DoraMetricsTests(unittest.TestCase):
    def service(self, result, name):
        return next(item for item in result["services"] if item["service"] == name)

    def test_synthetic_expected_metrics(self):
        result = calculate(load_deployments(FIXTURE))

        ess = self.service(result, "ess-registration")
        self.assertEqual(ess["nonproduction_rows_excluded"], 1)
        self.assertEqual(ess["metrics"]["deployment_frequency"]["deployments_per_week"], 4.0)
        self.assertEqual(ess["metrics"]["change_lead_time"]["median_hours"], 6.5)
        self.assertEqual(ess["metrics"]["change_fail_rate"]["percent"], 25.0)
        self.assertEqual(ess["metrics"]["failed_deployment_recovery_time"]["median_hours"], 1.5)
        self.assertEqual(ess["metrics"]["deployment_rework_rate"]["percent"], 25.0)

        ris = self.service(result, "ris-submission")
        self.assertEqual(ris["metrics"]["deployment_frequency"]["deployments_per_week"], 3.0)
        self.assertEqual(ris["metrics"]["change_lead_time"]["status"], "measured_partial")
        self.assertEqual(ris["metrics"]["change_lead_time"]["missing_change_linkage"], 1)
        self.assertEqual(ris["metrics"]["change_lead_time"]["median_hours"], 26.5)
        self.assertAlmostEqual(ris["metrics"]["change_fail_rate"]["percent"], 16.667, places=3)
        self.assertEqual(ris["metrics"]["failed_deployment_recovery_time"]["median_hours"], 4.0)
        self.assertAlmostEqual(ris["metrics"]["deployment_rework_rate"]["percent"], 16.667, places=3)

        iam = self.service(result, "iam-signin")
        self.assertEqual(iam["metrics"]["deployment_frequency"]["deployments_per_week"], 2.5)
        self.assertEqual(iam["metrics"]["change_lead_time"]["median_hours"], 3.0)
        self.assertEqual(iam["metrics"]["change_fail_rate"]["percent"], 0.0)
        self.assertEqual(iam["metrics"]["failed_deployment_recovery_time"]["status"], "not_observed")
        self.assertIsNone(iam["metrics"]["failed_deployment_recovery_time"]["median_hours"])
        self.assertEqual(iam["metrics"]["deployment_rework_rate"]["percent"], 0.0)

    def test_missing_linkage_is_not_imputed(self):
        result = calculate(load_deployments(MISSING))
        svc = self.service(result, "example-service")
        lead = svc["metrics"]["change_lead_time"]
        self.assertEqual(lead["status"], "measured_partial")
        self.assertEqual(lead["eligible_changes"], 2)
        self.assertEqual(lead["measured_changes"], 1)
        self.assertEqual(lead["missing_change_linkage"], 1)
        self.assertEqual(lead["coverage_percent"], 50.0)
        self.assertEqual(lead["median_hours"], 2.0)

    def test_failed_deployment_requires_recovery_timestamps(self):
        content = FIXTURE.read_text(encoding="utf-8")
        content = content.replace(
            "true,2026-09-05T15:10:00Z,2026-09-05T17:10:00Z,false",
            "true,,,false",
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(DataError, "requires failure_detected_at"):
                load_deployments(path)

    def test_inconsistent_windows_fail_closed(self):
        content = MISSING.read_text(encoding="utf-8")
        content = content.replace(
            "2026-09-08T00:00:00Z,production,2026-09-04T12:00:00Z",
            "2026-09-09T00:00:00Z,production,2026-09-04T12:00:00Z",
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mixed.csv"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(DataError, "inconsistent observation windows"):
                calculate(load_deployments(path))


if __name__ == "__main__":
    unittest.main()
