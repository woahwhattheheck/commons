#!/usr/bin/env python3
"""Retained hostile proof for the Okaloosa TDD 77-26 source/truth contract."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKET_ROOT = ROOT / "revenue" / "okaloosa_tdd77_26_ivvy"
VALIDATOR_PATH = PACKET_ROOT / "validate_packet.py"
LEDGER_PATH = PACKET_ROOT / "source_ledger.json"


def _load_validator():
    spec = importlib.util.spec_from_file_location("okaloosa_packet_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Okaloosa packet validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


class OkaloosaPacketTruthContract(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = validator.load_packet(LEDGER_PATH)

    def test_reviewed_packet_verifies(self) -> None:
        result = validator.validate_packet(copy.deepcopy(self.packet))
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["source_count"], 9)
        self.assertEqual(result["authority_false_count"], 18)
        self.assertEqual(result["commercial_state"], "PROPOSED_NOT_ACCEPTED")
        self.assertEqual(
            result["notice_deadline"],
            "September 25, 2026 @ 3:00 PM (CST)",
        )
        self.assertIs(result["full_rfp_retained"], False)

    def test_semantic_mutations_fail_closed(self) -> None:
        mutations = []

        wrong_deadline = copy.deepcopy(self.packet)
        wrong_deadline["opportunity"]["literal_response_deadline_from_notice"] = (
            "September 25, 2026 @ 12:00 PM"
        )
        mutations.append(("deadline", wrong_deadline))

        promoted_notice = copy.deepcopy(self.packet)
        promoted_notice["sources"][1]["source_role"] = "CONTROLLING_FULL_RFP"
        mutations.append(("notice-role", promoted_notice))

        invented_packet = copy.deepcopy(self.packet)
        invented_packet["opportunity"]["buyer_controlled_full_rfp_and_addenda_retained"] = True
        mutations.append(("full-rfp-retained", invented_packet))

        promoted_summary = copy.deepcopy(self.packet)
        promoted_summary["sources"][2]["authority_ceiling"] = "AUTHORITATIVE_REQUIREMENTS"
        mutations.append(("summary-authority", promoted_summary))

        hidden_conflict = copy.deepcopy(self.packet)
        hidden_conflict["sources"][3]["known_conflicts"] = []
        mutations.append(("deadline-conflict", hidden_conflict))

        invented_vendor_claim = copy.deepcopy(self.packet)
        invented_vendor_claim["sources"][4]["supports"].append(
            "iVvy is fully compliant and bidding TDD 77-26"
        )
        mutations.append(("vendor-claim", invented_vendor_claim))

        accepted = copy.deepcopy(self.packet)
        accepted["commercial_hypothesis"]["state"] = "ACCEPTED"
        mutations.append(("commercial-state", accepted))

        repriced = copy.deepcopy(self.packet)
        repriced["commercial_hypothesis"]["fixed_fee_minor_units"] = 3500001
        mutations.append(("price", repriced))

        send_authority = copy.deepcopy(self.packet)
        send_authority["authority"]["external_send_authorized"] = True
        mutations.append(("send-authority", send_authority))

        revenue_authority = copy.deepcopy(self.packet)
        revenue_authority["authority"]["recognized_revenue"] = True
        mutations.append(("revenue-authority", revenue_authority))

        missing_non_inference = copy.deepcopy(self.packet)
        missing_non_inference["non_inferences"].pop()
        mutations.append(("non-inference", missing_non_inference))

        duplicate_source = copy.deepcopy(self.packet)
        duplicate_source["sources"].append(copy.deepcopy(duplicate_source["sources"][0]))
        mutations.append(("duplicate-source", duplicate_source))

        for label, packet in mutations:
            with self.subTest(label=label):
                with self.assertRaises(validator.PacketError):
                    validator.validate_packet(packet)

    def test_cli_verifies_under_normal_and_optimized_python(self) -> None:
        for optimized in (False, True):
            command = [sys.executable]
            if optimized:
                command.append("-O")
            command.extend(
                [
                    str(VALIDATOR_PATH),
                    "--verify",
                    "--ledger",
                    str(LEDGER_PATH),
                ]
            )
            run = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            with self.subTest(optimized=optimized, stderr=run.stderr):
                self.assertEqual(run.returncode, 0)
                receipt = json.loads(run.stdout)
                self.assertEqual(receipt["status"], "OK")
                self.assertEqual(receipt["semantic_digest"], validator.EXPECTED_SEMANTIC_DIGEST)

    def test_cli_rejects_mutation_under_normal_and_optimized_python(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["authority"]["proposal_accepted"] = True
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "mutated.json"
            path.write_text(json.dumps(packet), encoding="utf-8")
            for optimized in (False, True):
                command = [sys.executable]
                if optimized:
                    command.append("-O")
                command.extend([str(VALIDATOR_PATH), "--verify", "--ledger", str(path)])
                run = subprocess.run(
                    command,
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                with self.subTest(optimized=optimized):
                    self.assertEqual(run.returncode, 2)
                    self.assertIn("ERROR:", run.stderr)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "duplicate.json"
            path.write_text(
                '{"schema_version":2,"schema_version":2}',
                encoding="utf-8",
            )
            with self.assertRaises(validator.PacketError):
                validator.load_packet(path)

    def test_validator_uses_no_optimizable_asserts(self) -> None:
        source = VALIDATOR_PATH.read_text(encoding="utf-8")
        for line in source.splitlines():
            self.assertFalse(line.lstrip().startswith("assert "), line)


if __name__ == "__main__":
    unittest.main()
