"""One end-to-end regression for the CSV-to-existing-assessor workflow."""
import base64
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from catalog_from_csv import convert_csv
from test_data_assessor import evaluate_catalog


class CsvIntakeWorkflow(unittest.TestCase):
    def test_csv_to_assessment_preserves_evidence_and_source(self):
        raw = (ROOT / "catalog_template.csv").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "catalog.json"
            command = [sys.executable, "-O", str(ROOT / "catalog_from_csv.py"),
                       str(ROOT / "catalog_template.csv"), "--as-of", "2026-09-19",
                       "--label", "Synthetic starter", "--output", str(output)]
            converted = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(converted.returncode, 0, converted.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(base64.b64decode(payload["_csv_source"]["bytes_base64"]), raw)
            self.assertEqual(payload["datasets"][0]["owner_role"], "Role, not person")
            self.assertEqual(payload["datasets"][0]["covered_boundary_cases"], ["boundary_a", "boundary_b"])
            assessed = subprocess.run([sys.executable, "-O", str(ROOT / "test_data_assessor.py"),
                                       str(output), "--format", "json"],
                                      capture_output=True, text=True, timeout=10)
            self.assertEqual(assessed.returncode, 0, assessed.stderr)
            self.assertEqual(json.loads(assessed.stdout)["summary"],
                             {"EVIDENCED": 7, "OBSERVED_GAP": 0, "UNKNOWN": 0})
            refused = subprocess.run(command[:-1] + [str(ROOT / "catalog_template.csv")],
                                     capture_output=True, text=True, timeout=10)
            self.assertEqual(refused.returncode, 2)
            self.assertEqual((ROOT / "catalog_template.csv").read_bytes(), raw)

        # One fictional three-service catalog distinguishes omission from explicit values.
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8"))))
        headers, starter = rows
        headers = headers + ["operator_note"]
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=headers)
        writer.writeheader()
        for identity, service, updates in [
            ("UNKNOWN", "ESS", {"covered_boundary_cases": "", "cleanup_required": "", "retention_days": ""}),
            ("EMPTY", "RIS", {"covered_boundary_cases": "[]", "cleanup_required": "false", "retention_days": "0"}),
            ("FUTURE", "IAM", {"last_refreshed": "2026-09-20", "cleanup_last_verified": "2026-09-20"}),
        ]:
            row = dict(zip(headers, starter))
            row.update(dataset_id=identity, service=service, purpose="Fictional, Ω\nsecond line",
                       operator_note="retained, not evaluated", **updates)
            writer.writerow(row)
        source = b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")
        catalog = convert_csv(source, as_of="2026-09-19")
        report = evaluate_catalog(catalog)
        states = [{c["check_id"]: c["state"] for c in row["checks"]} for row in report["datasets"]]
        self.assertEqual([s["representativeness"] for s in states], ["UNKNOWN", "OBSERVED_GAP", "EVIDENCED"])
        self.assertEqual([s["cleanup"] for s in states], ["UNKNOWN", "EVIDENCED", "UNKNOWN"])
        self.assertEqual([s["retention"] for s in states], ["UNKNOWN", "EVIDENCED", "EVIDENCED"])
        self.assertEqual(states[2]["refresh_freshness"], "UNKNOWN")
        self.assertNotIn("retention_days", catalog["datasets"][0])
        self.assertEqual(catalog["datasets"][1]["retention_days"], 0)
        self.assertEqual(catalog["datasets"][0]["purpose"], "Fictional, Ω\nsecond line")
        self.assertEqual(catalog["_csv_source"]["unevaluated_columns"], ["operator_note"])
        self.assertEqual(base64.b64decode(catalog["_csv_source"]["bytes_base64"]), source)
        self.assertGreater(catalog["_csv_source"]["records"][0]["end_line"], 2)
        with self.assertRaisesRegex(ValueError, "duplicate CSV headers"):
            convert_csv(b"dataset_id,service,purpose,service\nx,ESS,p,ESS\n", as_of="2026-09-19")
        with self.assertRaisesRegex(ValueError, "expected 3 cells"):
            convert_csv(b"dataset_id,service,purpose\nx,ESS\n", as_of="2026-09-19")
        with self.assertRaisesRegex(ValueError, "cleanup_required"):
            convert_csv(raw.replace(b",true,", b",1,"), as_of="2026-09-19")
