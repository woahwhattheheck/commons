#!/usr/bin/env python3
"""Retained hostiles for Okaloosa root-schema and generation metadata custody."""
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
    spec = importlib.util.spec_from_file_location("okaloosa_packet_validator_root", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Okaloosa packet validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


class OkaloosaRootSchemaGuard(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = validator.load_packet(LEDGER_PATH)

    def test_reviewed_root_schema_is_accepted(self) -> None:
        result = validator.validate_packet(copy.deepcopy(self.packet))
        self.assertEqual(result["status"], "OK")

    def test_unknown_root_authority_keys_fail_closed(self) -> None:
        for key, value in (
            ("submission_authorized", True),
            ("controlling_rfp", {"retained": True, "authoritative": True}),
        ):
            packet = copy.deepcopy(self.packet)
            packet[key] = value
            with self.subTest(key=key):
                with self.assertRaisesRegex(validator.PacketError, "root key set changed"):
                    validator.validate_packet(packet)

    def test_generated_at_is_exact_and_required(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["generated_at_utc"] = "2099-01-01T00:00:00Z"
        with self.assertRaisesRegex(validator.PacketError, "generated_at_utc changed"):
            validator.validate_packet(changed)

        missing = copy.deepcopy(self.packet)
        missing["generated_at_utc"] = None
        with self.assertRaisesRegex(validator.PacketError, "generated_at_utc changed"):
            validator.validate_packet(missing)

    def test_cli_rejects_root_and_generation_mutations_under_normal_and_optimized_python(self) -> None:
        variants = []
        extra = copy.deepcopy(self.packet)
        extra["submission_authorized"] = True
        variants.append(("extra-root-authority", extra, "root key set changed"))

        generated = copy.deepcopy(self.packet)
        generated["generated_at_utc"] = "2099-01-01T00:00:00Z"
        variants.append(("generated-at", generated, "generated_at_utc changed"))

        with tempfile.TemporaryDirectory() as td:
            for label, packet, message in variants:
                path = Path(td) / f"{label}.json"
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
                    with self.subTest(label=label, optimized=optimized):
                        self.assertEqual(run.returncode, 2)
                        self.assertIn(message, run.stderr)


if __name__ == "__main__":
    unittest.main()
