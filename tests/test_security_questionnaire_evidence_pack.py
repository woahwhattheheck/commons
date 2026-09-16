from __future__ import annotations

import copy
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "revenue" / "security_questionnaire_evidence_pack"
EVIDENCE = PRODUCT / "fixtures" / "evidence"
if str(PRODUCT) not in sys.path:
    sys.path.insert(0, str(PRODUCT))

import questionnaire as q  # noqa: E402
import synthetic_fixture as fixture  # noqa: E402


def fixture_raw(root: Path = EVIDENCE) -> bytes:
    return fixture.fixture_bytes(root)


class SecurityQuestionnaireEvidencePackTests(unittest.TestCase):
    def test_golden_fixture_has_all_five_states(self):
        report, markdown = q.compile_bytes(fixture_raw(), EVIDENCE)
        self.assertEqual(report["summary"]["question_count"], 5)
        self.assertEqual(
            report["summary"]["counts"],
            {
                "SUPPORTED": 1,
                "PARTIAL": 1,
                "HOLD_MISSING_EVIDENCE": 1,
                "HOLD_STALE_EVIDENCE": 1,
                "NOT_APPLICABLE": 1,
            },
        )
        rows = {row["id"]: row for row in report["questions"]}
        self.assertEqual(rows["Q.ACCESS"]["status"], "SUPPORTED")
        self.assertEqual(rows["Q.PARTIAL"]["answer_fragments"][0]["evidence_id"], "E.ACCESS")
        self.assertEqual(rows["Q.MFA"]["answer_fragments"], [])
        self.assertIn("PROPOSED_NOT_ACCEPTED", markdown)

    def test_all_retained_artifacts_are_hash_verified(self):
        report, _ = q.compile_bytes(fixture_raw(), EVIDENCE)
        self.assertTrue(report["evidence"])
        self.assertTrue(all(row["artifact_sha256_verified"] is True for row in report["evidence"]))
        self.assertTrue(all(row["artifact_bytes"] > 0 for row in report["evidence"]))

    def test_artifact_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "evidence"
            shutil.copytree(EVIDENCE, root)
            raw = fixture_raw(root)
            (root / "backup.txt").write_text("tampered\n", encoding="utf-8")
            with self.assertRaises(q.PackError):
                q.compile_bytes(raw, root)

    def test_path_traversal_fails_closed(self):
        obj = q.loads_strict(fixture_raw())
        obj["evidence"][0]["artifact_path"] = "../escape.txt"
        with self.assertRaises(q.PackError):
            q.compile_bytes(q.canonical_bytes(obj), EVIDENCE)

    def test_duplicate_keys_floats_and_nonfinite_are_rejected(self):
        with self.assertRaises(q.PackError):
            q.loads_strict(b'{"x":1,"x":2}')
        with self.assertRaises(q.PackError):
            q.loads_strict(b'{"x":1.25}')
        with self.assertRaises(q.PackError):
            q.loads_strict(b'{"x":NaN}')

    def test_na_question_cannot_smuggle_evidence_requirements(self):
        obj = q.loads_strict(fixture_raw())
        row = next(item for item in obj["questions"] if item["id"] == "Q.NA")
        row["required_evidence_ids"] = ["E.ACCESS"]
        with self.assertRaises(q.PackError):
            q.compile_bytes(q.canonical_bytes(obj), EVIDENCE)

    def test_report_tamper_breaks_verification(self):
        raw = fixture_raw()
        report, _ = q.compile_bytes(raw, EVIDENCE)
        tampered = copy.deepcopy(report)
        tampered["questions"][0]["status"] = "SUPPORTED" if tampered["questions"][0]["status"] != "SUPPORTED" else "PARTIAL"
        with self.assertRaises(q.PackError):
            q.verify_bytes(raw, q.canonical_bytes(tampered), EVIDENCE)

    def test_input_order_does_not_change_semantic_packet(self):
        raw_a = fixture_raw()
        obj = q.loads_strict(raw_a)
        obj["evidence"].reverse()
        obj["questions"].reverse()
        raw_b = q.canonical_bytes(obj)
        report_a, _ = q.compile_bytes(raw_a, EVIDENCE)
        report_b, _ = q.compile_bytes(raw_b, EVIDENCE)
        self.assertNotEqual(report_a["receipt"]["raw_input_sha256"], report_b["receipt"]["raw_input_sha256"])
        self.assertEqual(report_a["receipt"]["semantic_manifest_sha256"], report_b["receipt"]["semantic_manifest_sha256"])
        self.assertEqual(report_a["summary"], report_b["summary"])
        self.assertEqual(report_a["questions"], report_b["questions"])
        self.assertEqual(report_a["evidence"], report_b["evidence"])

    def test_authority_and_commercial_truth_are_hard_bounded(self):
        report, _ = q.compile_bytes(fixture_raw(), EVIDENCE)
        self.assertTrue(report["authority"])
        self.assertTrue(all(value is False for value in report["authority"].values()))
        self.assertEqual(report["offer"]["fixed_sprint_usd_cents"], 1_500_000)
        self.assertEqual(report["offer"]["optional_quarterly_refresh_usd_cents"], 200_000)
        self.assertEqual(report["offer"]["commercial_state"], "PROPOSED_NOT_ACCEPTED")

    def test_future_evidence_is_held_not_asserted(self):
        obj = q.loads_strict(fixture_raw())
        access = next(item for item in obj["evidence"] if item["id"] == "E.ACCESS")
        access["observed_at"] = "2026-10-01T00:00:00Z"
        access["valid_until"] = "2026-12-31T23:59:59Z"
        report, _ = q.compile_bytes(q.canonical_bytes(obj), EVIDENCE)
        row = next(item for item in report["questions"] if item["id"] == "Q.ACCESS")
        self.assertEqual(row["status"], "HOLD_STALE_EVIDENCE")
        self.assertEqual(row["answer_fragments"], [])

    def test_cli_compile_verify_and_optimized_verify(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            input_path = temp / "input.json"
            report_path = temp / "report.json"
            markdown_path = temp / "report.md"
            input_path.write_bytes(fixture_raw())
            self.assertEqual(
                q.cli([
                    "compile",
                    "--input", str(input_path),
                    "--evidence-root", str(EVIDENCE),
                    "--report-json", str(report_path),
                    "--report-md", str(markdown_path),
                ]),
                0,
            )
            self.assertEqual(
                q.cli([
                    "verify",
                    "--input", str(input_path),
                    "--evidence-root", str(EVIDENCE),
                    "--report-json", str(report_path),
                ]),
                0,
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    "-O",
                    str(PRODUCT / "questionnaire.py"),
                    "verify",
                    "--input", str(input_path),
                    "--evidence-root", str(EVIDENCE),
                    "--report-json", str(report_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(markdown_path.read_text(encoding="utf-8").startswith("# Security Questionnaire Evidence Pack"))
            self.assertEqual(
                q.cli([
                    "compile",
                    "--input", str(input_path),
                    "--evidence-root", str(EVIDENCE),
                    "--report-json", str(report_path),
                    "--report-md", str(markdown_path),
                ]),
                2,
            )


if __name__ == "__main__":
    unittest.main()
