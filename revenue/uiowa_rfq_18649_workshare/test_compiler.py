#!/usr/bin/env python3
from __future__ import annotations

import copy
import datetime as dt
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compiler  # noqa: E402

FIXED_TODAY = dt.date(2026, 9, 13)


def load_fixture() -> dict:
    return compiler.loads_strict((HERE / "fixtures" / "synthetic_packet.json").read_text(encoding="utf-8"))


def load_registry() -> dict:
    return compiler.loads_strict((HERE / "trusted_evidence_registry.json").read_text(encoding="utf-8"))


class CompilerContractTests(unittest.TestCase):
    def compile_fixed(self, packet: dict | None = None) -> dict:
        with mock.patch.object(compiler, "_current_utc_date", return_value=FIXED_TODAY):
            return compiler.compile_packet(load_fixture() if packet is None else packet)

    def verify_fixed(self, report: dict) -> bool:
        with mock.patch.object(compiler, "_current_utc_date", return_value=FIXED_TODAY):
            return compiler.verify_report(report)

    def test_baseline_exact_holds_and_commercial_terms(self) -> None:
        report = self.compile_fixed()
        self.assertEqual(report["status_counts"], {
            "HOLD_CONFLICT": 1,
            "HOLD_MISSING_EVIDENCE": 1,
            "HOLD_STALE_EVIDENCE": 1,
            "READY": 9,
        })
        self.assertEqual(report["aggregate_state"], "HOLD_FOR_PRIME_EVIDENCE_RECONCILIATION")
        self.assertEqual(report["commercial_terms"]["base_fee_usd"], 24000)
        self.assertEqual(report["commercial_terms"]["optional_readout_support_usd"], 4000)
        self.assertEqual(report["commercial_terms"]["status"], "PROPOSED_NOT_ACCEPTED")
        self.assertEqual(report["trusted_registry_sha256"], compiler.TRUSTED_REGISTRY_SHA256)
        self.assertTrue(all(value is False for value in report["authority"].values()))
        for cell in report["assessment_matrix"]:
            if cell["status"] != "READY":
                self.assertIsNone(cell["maturity"])
                self.assertIsNone(cell["confidence_bp"])

    def test_input_order_is_byte_identical(self) -> None:
        packet = load_fixture()
        one = compiler.canonical_json_bytes(self.compile_fixed(packet))
        packet["observations"] = list(reversed(packet["observations"]))
        two = compiler.canonical_json_bytes(self.compile_fixed(packet))
        self.assertEqual(one, two)

    def test_duplicate_json_key_rejected(self) -> None:
        with self.assertRaisesRegex(compiler.ContractError, "duplicate JSON key"):
            compiler.loads_strict('{"schema_version":2,"schema_version":2}')

    def test_candidate_cannot_choose_clock(self) -> None:
        packet = load_fixture()
        packet["evaluation_date"] = "2026-01-01"
        with self.assertRaisesRegex(compiler.ContractError, "keys mismatch"):
            self.compile_fixed(packet)

    def test_candidate_cannot_choose_score_or_provenance(self) -> None:
        packet = load_fixture()
        packet["observations"][0]["maturity"] = 4
        packet["observations"][0]["confidence_bp"] = 10000
        packet["observations"][0]["evidence_sha256"] = "0" * 64
        with self.assertRaisesRegex(compiler.ContractError, "keys mismatch"):
            self.compile_fixed(packet)

    def test_fabricated_self_hashed_evidence_cannot_enter_registry(self) -> None:
        packet = load_fixture()
        packet["observations"].append({
            "evidence_id": "ESS-AI-FABRICATED",
            "claim": "perfect evidence",
        })
        with self.assertRaisesRegex(compiler.ContractError, "exactly match trusted registry"):
            self.compile_fixed(packet)

    def test_candidate_cannot_omit_unfavorable_trusted_evidence(self) -> None:
        packet = load_fixture()
        packet["observations"] = [row for row in packet["observations"] if row["evidence_id"] != "IAM-DEP-01"]
        with self.assertRaisesRegex(compiler.ContractError, "exactly match trusted registry"):
            self.compile_fixed(packet)

    def test_claim_transplant_rejected(self) -> None:
        packet = load_fixture()
        packet["observations"][0]["claim"], packet["observations"][1]["claim"] = (
            packet["observations"][1]["claim"], packet["observations"][0]["claim"]
        )
        with self.assertRaisesRegex(compiler.ContractError, "claim does not match trusted registry"):
            self.compile_fixed(packet)

    def test_registry_root_is_pinned(self) -> None:
        registry = load_registry()
        registry["assessor_policy_id"] = "attacker-policy"
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            with mock.patch.object(compiler, "TRUSTED_REGISTRY_PATH", path):
                with self.assertRaisesRegex(compiler.ContractError, "trusted registry root mismatch"):
                    self.compile_fixed()

    def test_source_generation_substitution_rejected(self) -> None:
        registry = load_registry()
        registry["entries"][0]["source_generation"] = "forged-v2"
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            with mock.patch.object(compiler, "TRUSTED_REGISTRY_PATH", path):
                with self.assertRaisesRegex(compiler.ContractError, "trusted registry root mismatch"):
                    self.compile_fixed()

    def test_assessor_score_drift_rejected(self) -> None:
        registry = load_registry()
        registry["entries"][0]["maturity"] = 4
        registry["entries"][0]["confidence_bp"] = 10000
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            with mock.patch.object(compiler, "TRUSTED_REGISTRY_PATH", path):
                with self.assertRaisesRegex(compiler.ContractError, "trusted registry root mismatch"):
                    self.compile_fixed()

    def test_registry_omission_rejected(self) -> None:
        registry = load_registry()
        registry["entries"].pop()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            with mock.patch.object(compiler, "TRUSTED_REGISTRY_PATH", path):
                with self.assertRaisesRegex(compiler.ContractError, "trusted registry root mismatch"):
                    self.compile_fixed()

    def test_report_receipt_detects_tamper(self) -> None:
        report = self.compile_fixed()
        self.assertTrue(self.verify_fixed(report))
        tampered = copy.deepcopy(report)
        tampered["commercial_terms"]["base_fee_usd"] += 1
        with self.assertRaisesRegex(compiler.ContractError, "receipt mismatch"):
            self.verify_fixed(tampered)

    def test_stale_at_verify_fails_currentness(self) -> None:
        report = self.compile_fixed()
        with mock.patch.object(compiler, "_current_utc_date", return_value=dt.date(2027, 1, 20)):
            with self.assertRaisesRegex(compiler.ContractError, "not current"):
                compiler.verify_report(report)

    def test_semantic_report_with_recomputed_receipt_still_fails_recompile(self) -> None:
        report = self.compile_fixed()
        report["observations"][0]["maturity"] = 4
        unsigned = dict(report)
        unsigned.pop("receipt_sha256")
        report["receipt_sha256"] = compiler._sha256_bytes(compiler.canonical_json_bytes(unsigned))
        with self.assertRaisesRegex(compiler.ContractError, "semantic recompile mismatch"):
            self.verify_fixed(report)

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
