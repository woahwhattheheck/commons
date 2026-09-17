from __future__ import annotations

import copy
import importlib.util
import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "revenue" / "uark_rfp09112026_cmmc"
CURRENT_PATH = PKG / "current_authority.py"
LEGACY_PATH = PKG / "qualifier.py"
FIXTURE_PATH = PKG / "synthetic_candidate.json"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


current = load(CURRENT_PATH, "uark_current_authority_test")
legacy = load(LEGACY_PATH, "uark_historical_facade_test")


def fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def run_current_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-S", str(CURRENT_PATH), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_json(path: Path, value: object) -> None:
    path.write_text(current.canonical_json(value) + "\n", encoding="utf-8")


class UarkCurrentAuthorityTests(unittest.TestCase):
    def test_imported_current_signatures_expose_no_clock(self) -> None:
        self.assertEqual(list(inspect.signature(current.compile_current).parameters), ["intake"])
        self.assertEqual(list(inspect.signature(current.compile_production).parameters), ["intake"])
        self.assertEqual(list(inspect.signature(current.verify_packet_current).parameters), ["packet"])

    def test_imported_current_apis_fail_closed_without_transport(self) -> None:
        with mock.patch("subprocess.Popen", side_effect=AssertionError("transport used")):
            with self.assertRaisesRegex(current.InputError, "CLI-only"):
                current.compile_current(fixture())
            with self.assertRaisesRegex(current.InputError, "CLI-only"):
                current.compile_production(fixture())
            with self.assertRaisesRegex(current.InputError, "CLI-only"):
                current.verify_packet_current({})

    def test_imported_sentinels_ignore_parent_global_rebinding(self) -> None:
        class Broken:
            def __getattr__(self, name):
                raise AssertionError(f"rebound global used: {name}")

        with (
            mock.patch.object(current, "datetime", Broken()),
            mock.patch.object(current, "timezone", Broken()),
            mock.patch.object(current, "time", Broken()),
            mock.patch.object(current, "sys", Broken()),
            mock.patch.object(current, "_core", Broken()),
            mock.patch.object(current, "_PROCESS_NOW", lambda: utc("2099-01-01T00:00:00Z")),
            mock.patch("subprocess.Popen", side_effect=AssertionError("transport used")),
        ):
            with self.assertRaisesRegex(current.InputError, "CLI-only"):
                current.compile_current(fixture())
            with self.assertRaisesRegex(current.InputError, "CLI-only"):
                current.verify_packet_current({})

    def test_legacy_facade_is_explicitly_historical_only(self) -> None:
        self.assertEqual(legacy.AUTHORITY_MODE, "HISTORICAL_INTEGRITY_ONLY")
        self.assertFalse(hasattr(legacy, "compile_production"))
        self.assertFalse(hasattr(legacy, "verify_packet_current"))
        packet = legacy.compile_historical(fixture())
        self.assertTrue(legacy.verify_packet_historical(packet))

    def test_isolated_cli_compile_ignores_backdated_input(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = "2000-01-01T00:00:00Z"
        with tempfile.TemporaryDirectory() as td:
            intake_path = Path(td) / "intake.json"
            packet_path = Path(td) / "packet.json"
            write_json(intake_path, value)
            before = datetime.now(timezone.utc).replace(microsecond=0)
            proc = run_current_cli("compile", str(intake_path), "--json-out", str(packet_path))
            after = datetime.now(timezone.utc).replace(microsecond=0)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            stamped = utc(packet["evaluated_at_utc"])
            self.assertGreaterEqual(stamped, before)
            self.assertLessEqual(stamped, after)
            self.assertNotEqual(packet["evaluated_at_utc"], "2000-01-01T00:00:00Z")

    def test_nonisolated_current_cli_fails_closed(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(CURRENT_PATH), "compile", str(FIXTURE_PATH)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("direct isolated/no-site execution", proc.stderr)

    def test_future_historical_packet_is_rejected_by_isolated_cli_clock(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = "2099-01-01T00:00:00Z"
        packet = current.compile_historical(value)
        with tempfile.TemporaryDirectory() as td:
            packet_path = Path(td) / "packet.json"
            write_json(packet_path, packet)
            proc = run_current_cli("verify", str(packet_path))
            self.assertEqual(proc.returncode, 2)
            self.assertIn("ahead of process UTC", proc.stderr)

    def test_pre_source_historical_hold_is_not_laundered_as_current(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = "2026-09-15T00:57:59Z"
        packet = current.compile_historical(value)
        self.assertIn("EVALUATION_PRECEDES_SOURCE_CAPTURE", packet["decision"]["blockers"])
        with tempfile.TemporaryDirectory() as td:
            packet_path = Path(td) / "packet.json"
            write_json(packet_path, packet)
            proc = run_current_cli("verify", str(packet_path))
            self.assertEqual(proc.returncode, 2)
            self.assertIn("no longer current", proc.stderr)

    def test_historical_round_trip_is_separate_and_deterministic(self) -> None:
        left = current.compile_historical(fixture())
        right = current.compile_historical(fixture())
        self.assertEqual(left, right)
        self.assertTrue(current.verify_packet_historical(left))

    def test_isolated_cli_rejects_semantic_tamper_even_after_reseal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            packet_path = Path(td) / "packet.json"
            proc = run_current_cli("compile", str(FIXTURE_PATH), "--json-out", str(packet_path))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            forged = json.loads(packet_path.read_text(encoding="utf-8"))
            forged["decision"]["status"] = "PRIME_READY"
            decision = copy.deepcopy(forged["decision"])
            decision.pop("decision_receipt_sha256")
            forged["decision"]["decision_receipt_sha256"] = current.sha256_obj(decision)
            unsigned = copy.deepcopy(forged)
            unsigned.pop("packet_receipt_sha256")
            forged["packet_receipt_sha256"] = current.sha256_obj(unsigned)
            forged_path = Path(td) / "forged.json"
            write_json(forged_path, forged)
            verified = run_current_cli("verify", str(forged_path))
            self.assertEqual(verified.returncode, 2)
            self.assertIn("semantic verification", verified.stderr)

    def test_isolated_cli_exposes_no_caller_now_option(self) -> None:
        proc = run_current_cli(
            "compile", str(FIXTURE_PATH), "--now", "2000-01-01T00:00:00Z"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unrecognized arguments", proc.stderr)

    def test_isolated_cli_round_trip_and_exclusive_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            packet_path = Path(td) / "packet.json"
            markdown_path = Path(td) / "packet.md"
            verification_path = Path(td) / "verification.json"
            compiled = run_current_cli(
                "compile", str(FIXTURE_PATH),
                "--json-out", str(packet_path), "--markdown-out", str(markdown_path),
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            verified = run_current_cli(
                "verify", str(packet_path), "--verification-out", str(verification_path)
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            verification = json.loads(verification_path.read_text(encoding="utf-8"))
            self.assertTrue(verification["current"])
            self.assertFalse(verification["external_actions_authorized"])
            self.assertEqual(
                verification["authority_mode"], "ISOLATED_CLI_PROCESS_UTC"
            )
            again = run_current_cli(
                "compile", str(FIXTURE_PATH), "--json-out", str(packet_path)
            )
            self.assertEqual(again.returncode, 2)
            self.assertIn("File exists", again.stderr)


if __name__ == "__main__":
    unittest.main()
