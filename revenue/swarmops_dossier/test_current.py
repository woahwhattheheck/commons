from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import revenue.swarmops_dossier.current as current_module
from revenue.swarmops_dossier.acceptance import fixture
from revenue.swarmops_dossier.cli import main as cli_main
from revenue.swarmops_dossier.current import (
    CURRENT_MODE,
    HISTORICAL_MODE,
    OUTPUT_SCHEMA,
    compile_historical_dossier,
    verify_historical_dossier,
)
from revenue.swarmops_dossier.engine import compile_dossier, digest

AS_OF = "2026-09-13T14:00:00Z"
_OPT_CHILD_ENV = "SWARMOPS_CURRENT_OPT_CHILD"
_IS_OPT_CHILD = os.environ.get(_OPT_CHILD_ENV) == "1"


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _freshen(packet: dict, when: str) -> dict:
    fresh = copy.deepcopy(packet)
    for row in fresh["evidence"]:
        row["observed_at"] = when
    return fresh


def _forge_current_candidate(packet: dict, policy: dict, as_of: str) -> dict:
    """Adversarial self-sealed candidate; verifier must still own current time."""
    core = compile_dossier(packet, policy, as_of, {})
    wrapped = dict(core)
    core_receipt = wrapped.pop("receipt_sha256")
    wrapped["schema"] = OUTPUT_SCHEMA
    wrapped["evaluation_mode"] = CURRENT_MODE
    wrapped["core_v3_receipt_sha256"] = core_receipt
    wrapped["receipt_sha256"] = digest(wrapped)
    return wrapped


class CurrentFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.policy = fixture()

    def fresh_packet(self) -> dict:
        return _freshen(self.packet, _utc_text(datetime.now(timezone.utc)))

    def test_current_compile_owns_sealed_process_clock(self):
        packet = self.fresh_packet()
        before = datetime.now(timezone.utc) - timedelta(seconds=1)
        out = current_module.compile_current_dossier(packet, self.policy)
        after = datetime.now(timezone.utc) + timedelta(seconds=1)
        self.assertEqual(out["schema"], OUTPUT_SCHEMA)
        self.assertEqual(out["evaluation_mode"], CURRENT_MODE)
        self.assertLessEqual(before, _parse_utc(out["as_of"]))
        self.assertLessEqual(_parse_utc(out["as_of"]), after)
        self.assertEqual(out["status"], "READY_FOR_OWNER_REVIEW")
        self.assertNotIn("historical_status", out)

    def test_module_clock_reassignment_cannot_mint_or_freeze_current(self):
        stale_ready = _forge_current_candidate(self.packet, self.policy, AS_OF)
        self.assertEqual(stale_ready["status"], "READY_FOR_OWNER_REVIEW")
        with mock.patch.object(
            current_module,
            "_process_utc_now_text",
            create=True,
            new=lambda: AS_OF,
        ), mock.patch.object(
            current_module,
            "_clock_text",
            create=True,
            new=lambda: AS_OF,
        ):
            out = current_module.compile_current_dossier(self.fresh_packet(), self.policy)
            self.assertNotEqual(out["as_of"], AS_OF)
            self.assertFalse(
                current_module.verify_current_dossier(
                    self.packet, self.policy, stale_ready
                )
            )

    def test_reload_discards_inserted_legacy_clock_seam(self):
        stale_ready = _forge_current_candidate(self.packet, self.policy, AS_OF)
        current_module._process_utc_now_text = lambda: AS_OF
        current_module._clock_text = lambda: AS_OF
        reloaded = importlib.reload(current_module)
        self.assertFalse(hasattr(reloaded, "_process_utc_now_text"))
        self.assertFalse(hasattr(reloaded, "_clock_text"))
        out = reloaded.compile_current_dossier(self.fresh_packet(), self.policy)
        self.assertNotEqual(out["as_of"], AS_OF)
        self.assertFalse(reloaded.verify_current_dossier(self.packet, self.policy, stale_ready))

    def test_current_verify_accepts_still_fresh_current_receipt(self):
        packet = self.fresh_packet()
        out = current_module.compile_current_dossier(packet, self.policy)
        self.assertTrue(current_module.verify_current_dossier(packet, self.policy, out))

    def test_current_verify_expires_old_forged_ready_receipt(self):
        old = _forge_current_candidate(self.packet, self.policy, AS_OF)
        self.assertEqual(old["status"], "READY_FOR_OWNER_REVIEW")
        self.assertFalse(current_module.verify_current_dossier(self.packet, self.policy, old))

    def test_current_verify_rejects_future_evaluation_time(self):
        future = _utc_text(datetime.now(timezone.utc) + timedelta(days=1))
        candidate = _forge_current_candidate(self.packet, self.policy, future)
        self.assertFalse(
            current_module.verify_current_dossier(self.packet, self.policy, candidate)
        )

    def test_current_receipt_tamper_fails(self):
        packet = self.fresh_packet()
        out = current_module.compile_current_dossier(packet, self.policy)
        out["summary"]["DEMONSTRATED"] += 1
        self.assertFalse(current_module.verify_current_dossier(packet, self.policy, out))

    def test_historical_replay_is_deterministic_and_never_current(self):
        a = compile_historical_dossier(self.packet, self.policy, AS_OF)
        b = compile_historical_dossier(self.packet, self.policy, AS_OF)
        self.assertEqual(a, b)
        self.assertEqual(a["schema"], OUTPUT_SCHEMA)
        self.assertEqual(a["evaluation_mode"], HISTORICAL_MODE)
        self.assertEqual(a["status"], "NON_CURRENT")
        self.assertEqual(a["historical_status"], "READY_FOR_OWNER_REVIEW")
        self.assertTrue(
            verify_historical_dossier(self.packet, self.policy, AS_OF, a)
        )
        self.assertFalse(current_module.verify_current_dossier(self.packet, self.policy, a))

    def test_cli_without_as_of_is_current_process_time(self):
        with tempfile.TemporaryDirectory() as td:
            packet_data = self.fresh_packet()
            packet = Path(td, "packet.json")
            policy = Path(td, "policy.json")
            out = Path(td, "out.json")
            md = Path(td, "out.md")
            packet.write_text(json.dumps(packet_data))
            policy.write_text(json.dumps(self.policy))
            self.assertEqual(
                cli_main([
                    "compile", str(packet), str(policy),
                    "--json-out", str(out), "--markdown-out", str(md),
                ]),
                0,
            )
            compiled = json.loads(out.read_text())
            self.assertEqual(compiled["evaluation_mode"], CURRENT_MODE)
            self.assertNotEqual(compiled["as_of"], AS_OF)
            self.assertNotIn("NON-CURRENT HISTORICAL REPLAY", md.read_text())

    def test_programmatic_legacy_as_of_is_historical_only(self):
        with tempfile.TemporaryDirectory() as td:
            packet = Path(td, "packet.json")
            policy = Path(td, "policy.json")
            out = Path(td, "out.json")
            md = Path(td, "out.md")
            packet.write_text(json.dumps(self.packet))
            policy.write_text(json.dumps(self.policy))
            self.assertEqual(
                cli_main([
                    "compile", str(packet), str(policy),
                    "--as-of", AS_OF,
                    "--json-out", str(out), "--markdown-out", str(md),
                ]),
                0,
            )
            replay = json.loads(out.read_text())
            self.assertEqual(replay["evaluation_mode"], HISTORICAL_MODE)
            self.assertEqual(replay["status"], "NON_CURRENT")
            self.assertIn("NON-CURRENT HISTORICAL REPLAY", md.read_text())

    def test_public_cli_rejects_caller_clock(self):
        with mock.patch(
            "sys.argv",
            [
                "swarmops-dossier",
                "compile",
                "packet.json",
                "policy.json",
                "--as-of",
                AS_OF,
                "--json-out",
                "out.json",
                "--markdown-out",
                "out.md",
            ],
        ):
            with self.assertRaises(SystemExit) as caught:
                cli_main()
        self.assertEqual(caught.exception.code, 2)

    def test_cli_current_verify_reacquires_real_clock(self):
        with tempfile.TemporaryDirectory() as td:
            packet_data = self.fresh_packet()
            packet = Path(td, "packet.json")
            policy = Path(td, "policy.json")
            candidate = Path(td, "candidate.json")
            packet.write_text(json.dumps(packet_data))
            policy.write_text(json.dumps(self.policy))
            candidate.write_text(
                json.dumps(current_module.compile_current_dossier(packet_data, self.policy))
            )
            self.assertEqual(
                cli_main(["verify", str(packet), str(policy), str(candidate)]),
                0,
            )

            stale_packet = Path(td, "stale-packet.json")
            stale_candidate = Path(td, "stale-candidate.json")
            stale_packet.write_text(json.dumps(self.packet))
            stale_candidate.write_text(
                json.dumps(_forge_current_candidate(self.packet, self.policy, AS_OF))
            )
            self.assertEqual(
                cli_main([
                    "verify", str(stale_packet), str(policy), str(stale_candidate)
                ]),
                3,
            )


@unittest.skipIf(_IS_OPT_CHILD, "parent-only optimized replay harness")
class CurrentFreshnessOptimizedBridgeTests(unittest.TestCase):
    def test_real_python_optimized_replay(self):
        env = os.environ.copy()
        env[_OPT_CHILD_ENV] = "1"
        repo_root = Path(__file__).resolve().parents[2]
        completed = subprocess.run(
            [sys.executable, "-O", "-m", "unittest", "revenue.swarmops_dossier.test_current"],
            cwd=repo_root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("OK", completed.stdout)


if __name__ == "__main__":
    unittest.main()
