#!/usr/bin/env python3
from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compiler  # noqa: E402


def load_fixture() -> dict:
    return compiler.loads_strict((HERE / "fixtures" / "synthetic_packet.json").read_text(encoding="utf-8"))


class CompilerContractTests(unittest.TestCase):
    def test_baseline_exact_holds_and_commercial_terms(self) -> None:
        report = compiler.compile_packet(load_fixture())
        self.assertEqual(report["status_counts"], {
            "HOLD_CONFLICT": 1,
            "HOLD_MISSING_EVIDENCE": 1,
            "HOLD_STALE_EVIDENCE": 1,
            "READY": 9,
        })
        self.assertEqual(report["aggregate_state"], "HOLD_FOR_PRIME_EVIDENCE_RECONCILIATION")
        self.assertEqual(report["commercial_terms"]["base_fee_usd"], 24000)
        self.assertEqual(report["commercial_terms"]["optional_readout_support_usd"], 4000)
        self.assertTrue(all(value is False for value in report["authority"].values()))
        for cell in report["assessment_matrix"]:
            if cell["status"] != "READY":
                self.assertIsNone(cell["maturity"])
                self.assertIsNone(cell["confidence_bp"])

    def test_input_order_is_byte_identical(self) -> None:
        packet = load_fixture()
        one = compiler.canonical_json_bytes(compiler.compile_packet(packet))
        packet["observations"] = list(reversed(packet["observations"]))
        two = compiler.canonical_json_bytes(compiler.compile_packet(packet))
        self.assertEqual(one, two)

    def test_duplicate_json_key_rejected(self) -> None:
        with self.assertRaisesRegex(compiler.ContractError, "duplicate JSON key"):
            compiler.loads_strict('{"schema_version":1,"schema_version":1}')

    def test_bool_is_not_integer_maturity(self) -> None:
        packet = load_fixture()
        packet["observations"][0]["maturity"] = True
        with self.assertRaisesRegex(compiler.ContractError, "must be integer"):
            compiler.compile_packet(packet)

    def test_unknown_field_rejected(self) -> None:
        packet = load_fixture()
        packet["unexpected"] = "no"
        with self.assertRaisesRegex(compiler.ContractError, "keys mismatch"):
            compiler.compile_packet(packet)

    def test_commercial_drift_rejected(self) -> None:
        packet = load_fixture()
        packet["engagement"]["base_fee_usd"] = 23999
        with self.assertRaisesRegex(compiler.ContractError, "base fee drift"):
            compiler.compile_packet(packet)

    def test_cross_cell_transplant_rejected(self) -> None:
        packet = load_fixture()
        packet["observations"][0]["group"] = "RIS"
        with self.assertRaisesRegex(compiler.ContractError, "scope_commitment mismatch"):
            compiler.compile_packet(packet)

    def test_future_evidence_rejected(self) -> None:
        packet = load_fixture()
        packet["observations"][0]["observed_date"] = "2026-09-14"
        with self.assertRaisesRegex(compiler.ContractError, "future"):
            compiler.compile_packet(packet)

    def test_claim_digest_drift_rejected(self) -> None:
        packet = load_fixture()
        packet["observations"][0]["claim"] += " changed"
        with self.assertRaisesRegex(compiler.ContractError, "evidence_sha256 mismatch"):
            compiler.compile_packet(packet)

    def test_report_receipt_detects_tamper(self) -> None:
        report = compiler.compile_packet(load_fixture())
        self.assertTrue(compiler.verify_report(report))
        tampered = copy.deepcopy(report)
        tampered["commercial_terms"]["base_fee_usd"] += 1
        with self.assertRaisesRegex(compiler.ContractError, "receipt mismatch"):
            compiler.verify_report(tampered)

    def test_cli_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            source = td / "packet.json"
            out = td / "report.json"
            source.write_bytes((HERE / "fixtures" / "synthetic_packet.json").read_bytes())
            first = subprocess.run(
                [sys.executable, str(HERE / "compiler.py"), "compile", str(source), str(out)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            second = subprocess.run(
                [sys.executable, str(HERE / "compiler.py"), "compile", str(source), str(out)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(second.returncode, 2)
            self.assertIn("refusing existing output path", second.stderr)

    def test_normal_and_optimized_cli_bytes_match(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            source = td / "packet.json"
            out_a = td / "a.json"
            out_b = td / "b.json"
            source.write_bytes((HERE / "fixtures" / "synthetic_packet.json").read_bytes())
            for flags, output in [([], out_a), (["-O"], out_b)]:
                run = subprocess.run(
                    [sys.executable, *flags, str(HERE / "compiler.py"), "compile", str(source), str(output)],
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(out_a.read_bytes(), out_b.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
