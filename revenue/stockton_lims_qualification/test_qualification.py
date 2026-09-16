from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from .cli import main as cli_main
from .engine import compile_at, verify_current, verify_historical
from .schema import (
    MANDATORY_PRIME_GATES,
    QualificationError,
    canonical_bytes,
    loads_strict,
    validate_packet,
)
from .source_binding import bind_source_file

NOW = "2026-09-15T20:00:00Z"
VALID_UNTIL = "2026-09-30T20:00:00Z"
D = "d" * 64
E = "e" * 64


def evidence(status: str = "VERIFIED", suffix: str = "x") -> dict[str, object]:
    if status != "VERIFIED":
        return {
            "status": status,
            "artifact_id": None,
            "sha256": None,
            "observed_at": None,
            "valid_until": None,
            "authority_ref": None,
        }
    return {
        "status": "VERIFIED",
        "artifact_id": f"artifact-{suffix}",
        "sha256": D,
        "observed_at": NOW,
        "valid_until": VALID_UNTIL,
        "authority_ref": f"authority-{suffix}",
    }


def packet(*, prime: bool = False, seam: bool = True) -> dict[str, object]:
    gates = []
    if prime:
        gates = [{"gate_id": gate_id, "evidence": evidence(suffix=f"g{index}")} for index, gate_id in enumerate(MANDATORY_PRIME_GATES)]
    return {
        "schema": "stockton-lims-qualification/input-v1",
        "opportunity_id": "stockton-pur-27-007",
        "opportunity_status": "OPEN",
        "status_evidence": evidence(suffix="status"),
        "sources": [
            {
                "source_id": "RFP_PDF",
                "status": "BOUND",
                "filename": "PUR_27-007_Final_.pdf",
                "sha256": D,
                "size_bytes": 123,
                "captured_at": NOW,
            },
            {
                "source_id": "REQUIREMENTS_XLSX",
                "status": "BOUND",
                "filename": "Requirements.xlsx",
                "sha256": E,
                "size_bytes": 456,
                "captured_at": NOW,
            },
        ],
        "addenda_census": evidence(suffix="addenda"),
        "gates": gates,
        "specialist_seam": {
            "scope_ids": ["CIWQS_REPORTING_VALIDATION", "QC_ACCEPTANCE_TESTS"] if seam else [],
            "evidence": evidence(suffix="seam") if seam else evidence("MISSING"),
            "proposed_fee_usd": 25000 if seam else None,
        },
    }


class QualificationTests(unittest.TestCase):
    def test_teaming_only(self) -> None:
        report = compile_at(packet(), NOW)
        self.assertEqual(report["disposition"], "TEAMING_ONLY")
        self.assertEqual(report["specialist_seam"]["commercial_state"], "PROPOSED_NOT_ACCEPTED")
        self.assertTrue(report["missing_prime_gates"])
        self.assertTrue(all(value is False for value in report["authority"].values()))

    def test_prime_ready_requires_every_gate(self) -> None:
        report = compile_at(packet(prime=True), NOW)
        self.assertEqual(report["disposition"], "PRIME_READY")
        self.assertEqual(report["missing_prime_gates"], [])

    def test_one_missing_prime_gate_prevents_prime(self) -> None:
        value = packet(prime=True)
        value["gates"] = value["gates"][:-1]
        self.assertEqual(compile_at(value, NOW)["disposition"], "TEAMING_ONLY")

    def test_missing_workbook_holds(self) -> None:
        value = packet()
        value["sources"][1] = {
            "source_id": "REQUIREMENTS_XLSX",
            "status": "SOURCE_REQUIRED",
            "filename": "Requirements.xlsx",
            "sha256": None,
            "size_bytes": None,
            "captured_at": None,
        }
        report = compile_at(value, NOW)
        self.assertEqual(report["disposition"], "HOLD")
        self.assertIn("REQUIREMENTS_XLSX_SOURCE_REQUIRED", report["reasons"])

    def test_metadata_only_rfp_holds(self) -> None:
        value = packet()
        value["sources"][0] = {
            "source_id": "RFP_PDF",
            "status": "METADATA_ONLY",
            "filename": "PUR_27-007_Final_.pdf",
            "sha256": None,
            "size_bytes": None,
            "captured_at": NOW,
        }
        self.assertEqual(compile_at(value, NOW)["disposition"], "HOLD")

    def test_missing_addenda_holds(self) -> None:
        value = packet()
        value["addenda_census"] = evidence("MISSING")
        self.assertEqual(compile_at(value, NOW)["disposition"], "HOLD")

    def test_stale_addenda_holds(self) -> None:
        value = packet()
        value["addenda_census"]["observed_at"] = "2026-09-13T20:00:00Z"
        value["addenda_census"]["valid_until"] = "2026-09-14T20:00:00Z"
        report = compile_at(value, NOW)
        self.assertEqual(report["disposition"], "HOLD")
        self.assertIn("ADDENDA_CENSUS_STALE", report["reasons"])

    def test_future_status_holds(self) -> None:
        value = packet()
        value["status_evidence"]["observed_at"] = "2026-09-16T20:00:00Z"
        value["status_evidence"]["valid_until"] = "2026-09-30T20:00:00Z"
        self.assertEqual(compile_at(value, NOW)["disposition"], "HOLD")

    def test_conflicting_gate_holds_not_teaming(self) -> None:
        value = packet()
        value["gates"] = [{"gate_id": "CGL_2M", "evidence": evidence("CONFLICT")}]
        report = compile_at(value, NOW)
        self.assertEqual(report["disposition"], "HOLD")
        self.assertIn("GATE_CGL_2M_CONFLICT", report["reasons"])

    def test_unverified_seam_holds(self) -> None:
        self.assertEqual(compile_at(packet(seam=False), NOW)["disposition"], "HOLD")

    def test_cancelled_is_no_bid(self) -> None:
        value = packet()
        value["opportunity_status"] = "CANCELLED"
        report = compile_at(value, NOW)
        self.assertEqual(report["disposition"], "NO_BID")
        self.assertIn("OPPORTUNITY_CANCELLED", report["reasons"])

    def test_closed_is_no_bid(self) -> None:
        value = packet()
        value["opportunity_status"] = "CLOSED"
        self.assertEqual(compile_at(value, NOW)["disposition"], "NO_BID")

    def test_deadline_is_no_bid(self) -> None:
        report = compile_at(packet(), "2026-10-08T21:00:00Z")
        self.assertEqual(report["disposition"], "NO_BID")
        self.assertEqual(report["windows"]["proposal_window"], "CLOSED")

    def test_question_window_closes_independently(self) -> None:
        report = compile_at(packet(), "2026-09-24T21:00:00Z")
        self.assertEqual(report["windows"]["question_window"], "CLOSED")
        self.assertEqual(report["windows"]["proposal_window"], "OPEN")

    def test_duplicate_json_key_rejected(self) -> None:
        with self.assertRaises(QualificationError):
            loads_strict('{"schema":1,"schema":2}')

    def test_nonfinite_json_rejected(self) -> None:
        with self.assertRaises(QualificationError):
            loads_strict('{"x":NaN}')

    def test_unknown_top_level_key_rejected(self) -> None:
        value = packet()
        value["shadow"] = True
        with self.assertRaises(QualificationError):
            validate_packet(value)

    def test_unknown_gate_rejected(self) -> None:
        value = packet()
        value["gates"] = [{"gate_id": "INVENTED", "evidence": evidence()}]
        with self.assertRaises(QualificationError):
            validate_packet(value)

    def test_duplicate_gate_rejected(self) -> None:
        value = packet()
        row = {"gate_id": "CGL_2M", "evidence": evidence()}
        value["gates"] = [row, copy.deepcopy(row)]
        with self.assertRaises(QualificationError):
            validate_packet(value)

    def test_bool_not_accepted_as_fee(self) -> None:
        value = packet()
        value["specialist_seam"]["proposed_fee_usd"] = True
        with self.assertRaises(QualificationError):
            validate_packet(value)

    def test_bad_digest_rejected(self) -> None:
        value = packet()
        value["sources"][0]["sha256"] = "abc"
        with self.assertRaises(QualificationError):
            validate_packet(value)

    def test_source_filename_substitution_rejected(self) -> None:
        value = packet()
        value["sources"][0]["filename"] = "other.pdf"
        with self.assertRaises(QualificationError):
            validate_packet(value)

    def test_deterministic_report(self) -> None:
        first = compile_at(packet(), NOW)
        second = compile_at(copy.deepcopy(packet()), NOW)
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))

    def test_historical_verify_and_tamper(self) -> None:
        value = packet()
        report = compile_at(value, NOW)
        self.assertTrue(verify_historical(value, report))
        report["disposition"] = "PRIME_READY"
        self.assertFalse(verify_historical(value, report))

    def test_current_verify_detects_semantic_age(self) -> None:
        value = packet()
        report = compile_at(value, NOW)
        with mock.patch("revenue.stockton_lims_qualification.engine.utc_now_string", return_value=NOW):
            self.assertTrue(verify_current(value, report))
        with mock.patch("revenue.stockton_lims_qualification.engine.utc_now_string", return_value="2026-10-09T00:00:00Z"):
            self.assertFalse(verify_current(value, report))

    def test_pdf_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "download.bin")
            path.write_bytes(b"%PDF-1.7\nexample\n%%EOF\n")
            row = bind_source_file("RFP_PDF", path, NOW)
            self.assertEqual(row["status"], "BOUND")
            self.assertEqual(row["filename"], "PUR_27-007_Final_.pdf")
            self.assertEqual(row["size_bytes"], path.stat().st_size)

    def test_xlsx_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "download.bin")
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types/>")
                archive.writestr("_rels/.rels", "<Relationships/>")
                archive.writestr("xl/workbook.xml", "<workbook/>")
            row = bind_source_file("REQUIREMENTS_XLSX", path, NOW)
            self.assertEqual(row["filename"], "Requirements.xlsx")

    def test_binding_rejects_wrong_magic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "bad.bin")
            path.write_bytes(b"not a pdf")
            with self.assertRaises(QualificationError):
                bind_source_file("RFP_PDF", path, NOW)

    def test_binding_rejects_symlink(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp, "real.pdf")
            link = Path(tmp, "link.pdf")
            real.write_bytes(b"%PDF-1.7\n%%EOF\n")
            os.symlink(real, link)
            with self.assertRaises(QualificationError):
                bind_source_file("RFP_PDF", link, NOW)

    def test_xlsx_rejects_fake_zip_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "fake.xlsx")
            path.write_bytes(b"PK\x03\x04not-a-real-zip")
            with self.assertRaises(QualificationError):
                bind_source_file("REQUIREMENTS_XLSX", path, NOW)

    def test_pdf_requires_terminal_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "truncated.pdf")
            path.write_bytes(b"%PDF-1.7\ntruncated")
            with self.assertRaises(QualificationError):
                bind_source_file("RFP_PDF", path, NOW)

    def test_cli_compile_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp, "input.json")
            report_path = Path(tmp, "report.json")
            md_path = Path(tmp, "report.md")
            input_path.write_bytes(json.dumps(packet()).encode())
            report_path.write_text("occupied")
            rc = cli_main(["compile", str(input_path), str(report_path), str(md_path), "--as-of", NOW])
            self.assertEqual(rc, 2)
            self.assertEqual(report_path.read_text(), "occupied")

    def test_cli_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp, "input.json")
            report_path = Path(tmp, "report.json")
            md_path = Path(tmp, "report.md")
            input_path.write_bytes(json.dumps(packet()).encode())
            self.assertEqual(cli_main(["compile", str(input_path), str(report_path), str(md_path), "--as-of", NOW]), 0)
            self.assertEqual(cli_main(["verify", str(input_path), str(report_path)]), 0)
            self.assertIn("TEAMING_ONLY", md_path.read_text())


if __name__ == "__main__":
    unittest.main()
