#!/usr/bin/env python3
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compiler  # noqa: E402

POLICY_ROOT = "8a301398647177ce4a9e9575270979041a7c7cd0a83eb9b3d7ab45e6eaf17a14"
NOW = dt.datetime(2026, 9, 13, 15, 30, 0, tzinfo=dt.timezone.utc)


def load_json(name: str) -> dict:
    return compiler.loads_strict((HERE / "fixtures" / name).read_bytes())


def compile_fixture(policy: dict | None = None, evidence: dict | None = None) -> dict:
    return compiler.compile_report(
        load_json("policy.json") if policy is None else policy,
        load_json("evidence.json") if evidence is None else evidence,
        expected_policy_sha256=POLICY_ROOT if policy is None else compiler.sha256_bytes(compiler.canon(policy)),
        now=NOW,
    )


class RoomTurnContractTests(unittest.TestCase):
    def test_baseline_exact_decisions_and_scope(self) -> None:
        report = compile_fixture()
        self.assertEqual(report["event_count_unique"], 18)
        self.assertEqual(report["room_count"], 6)
        self.assertEqual(report["ready_count"], 2)
        self.assertEqual(report["blocked_count"], 4)
        decisions = {room["room_id"]: (room["decision"], room["reasons"]) for room in report["rooms"]}
        self.assertEqual(decisions["101"], ("READY", []))
        self.assertEqual(decisions["102"], ("READY", []))
        self.assertEqual(
            decisions["103"],
            ("BLOCKED", ["BLOCK_HOUSEKEEPING:linen_missing", "MISSING_MANAGER_RELEASE"]),
        )
        self.assertEqual(decisions["104"], ("BLOCKED", ["STALE_HOUSEKEEPING"]))
        self.assertEqual(decisions["105"], ("BLOCKED", ["CONFLICT_MAINTENANCE"]))
        self.assertEqual(
            decisions["106"],
            ("BLOCKED", ["MISSING_MANAGER_RELEASE", "WRONG_TURN_MANAGER_RELEASE:1"]),
        )
        self.assertEqual(report["commercial_terms"]["price_usd"], 2500)
        self.assertEqual(report["commercial_terms"]["duration_days"], 7)
        self.assertTrue(all(v is False for v in report["authority"].values()))

    def test_policy_root_mismatch_fails(self) -> None:
        with self.assertRaisesRegex(compiler.ContractError, "policy sha256 mismatch"):
            compiler.compile_report(
                load_json("policy.json"), load_json("evidence.json"),
                expected_policy_sha256="0" * 64, now=NOW,
            )

    def test_commercial_drift_fails_even_with_matching_new_root(self) -> None:
        policy = load_json("policy.json")
        policy["price_usd"] = 2499
        root = compiler.sha256_bytes(compiler.canon(policy))
        with self.assertRaisesRegex(compiler.ContractError, "price_usd drift"):
            compiler.compile_report(policy, load_json("evidence.json"), expected_policy_sha256=root, now=NOW)

    def test_bool_is_not_integer(self) -> None:
        policy = load_json("policy.json")
        policy["duration_days"] = True
        root = compiler.sha256_bytes(compiler.canon(policy))
        with self.assertRaisesRegex(compiler.ContractError, "must be integer"):
            compiler.compile_report(policy, load_json("evidence.json"), expected_policy_sha256=root, now=NOW)

    def test_duplicate_json_key_rejected(self) -> None:
        with self.assertRaisesRegex(compiler.ContractError, "duplicate JSON key"):
            compiler.loads_strict('{"schema_version":"a","schema_version":"b"}')

    def test_unknown_event_field_rejected(self) -> None:
        evidence = load_json("evidence.json")
        evidence["events"][0]["guest_name"] = "must-not-exist"
        with self.assertRaisesRegex(compiler.ContractError, "keys mismatch"):
            compiler.compile_report(load_json("policy.json"), evidence, expected_policy_sha256=POLICY_ROOT, now=NOW)

    def test_exact_event_replay_is_idempotent(self) -> None:
        evidence = load_json("evidence.json")
        parsed = compiler.parse_policy(load_json("policy.json"), POLICY_ROOT)
        events = compiler.parse_evidence(evidence, parsed)
        self.assertEqual(len(events), 18)
        self.assertEqual(sum(1 for e in events if e["event_id"] == "e102-mgr"), 1)

    def test_same_event_id_with_different_content_rejected(self) -> None:
        evidence = load_json("evidence.json")
        dup = copy.deepcopy(evidence["events"][0])
        dup["detail_code"] = "changed"
        evidence["events"].append(dup)
        with self.assertRaisesRegex(compiler.ContractError, "replay content mismatch"):
            compiler.compile_report(load_json("policy.json"), evidence, expected_policy_sha256=POLICY_ROOT, now=NOW)

    def test_event_reordering_is_byte_deterministic(self) -> None:
        evidence = load_json("evidence.json")
        a = compiler.canon(compiler.compile_report(load_json("policy.json"), evidence, expected_policy_sha256=POLICY_ROOT, now=NOW))
        evidence["events"] = list(reversed(evidence["events"]))
        b = compiler.canon(compiler.compile_report(load_json("policy.json"), evidence, expected_policy_sha256=POLICY_ROOT, now=NOW))
        self.assertEqual(a, b)

    def test_stale_event_cannot_release_room(self) -> None:
        report = compile_fixture()
        room = next(r for r in report["rooms"] if r["room_id"] == "104")
        self.assertEqual(room["decision"], "BLOCKED")
        self.assertIn("STALE_HOUSEKEEPING", room["reasons"])
        hk = next(c for c in room["checks"] if c["kind"] == "housekeeping")
        self.assertFalse(hk["clear"])
        self.assertEqual(hk["age_minutes"], 150)

    def test_same_timestamp_conflict_cannot_release_room(self) -> None:
        room = next(r for r in compile_fixture()["rooms"] if r["room_id"] == "105")
        self.assertEqual(room["decision"], "BLOCKED")
        self.assertEqual(room["reasons"], ["CONFLICT_MAINTENANCE"])

    def test_future_event_cannot_release_room(self) -> None:
        evidence = load_json("evidence.json")
        for event in evidence["events"]:
            if event["event_id"] == "e101-hk":
                event["observed_at"] = "2026-09-13T15:31:00Z"
        report = compiler.compile_report(load_json("policy.json"), evidence, expected_policy_sha256=POLICY_ROOT, now=NOW)
        room = next(r for r in report["rooms"] if r["room_id"] == "101")
        self.assertEqual(room["decision"], "BLOCKED")
        self.assertIn("FUTURE_HOUSEKEEPING", room["reasons"])

    def test_wrong_turn_evidence_never_clears_current_turn(self) -> None:
        room = next(r for r in compile_fixture()["rooms"] if r["room_id"] == "106")
        self.assertEqual(room["decision"], "BLOCKED")
        self.assertIn("MISSING_MANAGER_RELEASE", room["reasons"])
        self.assertIn("WRONG_TURN_MANAGER_RELEASE:1", room["reasons"])

    def test_unauthorized_manager_cannot_release_room(self) -> None:
        evidence = load_json("evidence.json")
        for event in evidence["events"]:
            if event["event_id"] == "e101-mgr":
                event["actor_id"] = "mgr.outsider"
        report = compiler.compile_report(load_json("policy.json"), evidence, expected_policy_sha256=POLICY_ROOT, now=NOW)
        room = next(r for r in report["rooms"] if r["room_id"] == "101")
        self.assertEqual(room["decision"], "BLOCKED")
        self.assertIn("UNAUTHORIZED_MANAGER", room["reasons"])

    def test_unknown_room_rejected(self) -> None:
        evidence = load_json("evidence.json")
        extra = copy.deepcopy(evidence["events"][0])
        extra["event_id"] = "e999-hk"
        extra["room_id"] = "999"
        extra["turn_id"] = "turn-999-a"
        evidence["events"].append(extra)
        with self.assertRaisesRegex(compiler.ContractError, "unknown rooms"):
            compiler.compile_report(load_json("policy.json"), evidence, expected_policy_sha256=POLICY_ROOT, now=NOW)

    def test_property_mismatch_rejected(self) -> None:
        evidence = load_json("evidence.json")
        evidence["property_id"] = "other-property"
        with self.assertRaisesRegex(compiler.ContractError, "property_id mismatch"):
            compiler.compile_report(load_json("policy.json"), evidence, expected_policy_sha256=POLICY_ROOT, now=NOW)

    def test_embedded_report_tamper_rejected_against_retained_receipt(self) -> None:
        report = compile_fixture()
        retained = report["receipt_sha256"]
        report["commercial_terms"]["price_usd"] = 1
        with self.assertRaisesRegex(compiler.ContractError, "report receipt mismatch"):
            compiler.verify_report(report, expected_policy_sha256=POLICY_ROOT, expected_report_sha256=retained)

    def test_resealed_report_still_fails_retained_receipt(self) -> None:
        report = compile_fixture()
        retained = report["receipt_sha256"]
        report["ready_count"] = 99
        unsigned = dict(report)
        del unsigned["receipt_sha256"]
        report["receipt_sha256"] = compiler.sha256_bytes(compiler.canon(unsigned))
        with self.assertRaisesRegex(compiler.ContractError, "retained receipt mismatch"):
            compiler.verify_report(report, expected_policy_sha256=POLICY_ROOT, expected_report_sha256=retained)

    def test_verify_requires_expected_policy_root(self) -> None:
        report = compile_fixture()
        with self.assertRaisesRegex(compiler.ContractError, "policy root mismatch"):
            compiler.verify_report(
                report, expected_policy_sha256="f" * 64,
                expected_report_sha256=report["receipt_sha256"],
            )

    def test_markdown_render_verified(self) -> None:
        report = compile_fixture()
        text = compiler.render_markdown(
            report,
            expected_policy_sha256=POLICY_ROOT,
            expected_report_sha256=report["receipt_sha256"],
        )
        self.assertIn("2 READY / 4 BLOCKED", text)
        self.assertIn("WRONG_TURN_MANAGER_RELEASE:1", text)
        self.assertIn("does not write to a PMS", text)

    def test_cli_refuses_overwrite_and_clock_override(self) -> None:
        with tempfile.TemporaryDirectory() as td_raw:
            td = Path(td_raw)
            policy = td / "policy.json"
            evidence = td / "evidence.json"
            out = td / "report.json"
            policy.write_bytes((HERE / "fixtures" / "policy.json").read_bytes())
            evidence.write_bytes((HERE / "fixtures" / "evidence.json").read_bytes())
            cmd = [
                sys.executable, str(HERE / "compiler.py"), "compile",
                "--policy", str(policy), "--evidence", str(evidence),
                "--expected-policy-sha256", POLICY_ROOT, "--out", str(out),
            ]
            first = subprocess.run(cmd, text=True, capture_output=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = subprocess.run(cmd, text=True, capture_output=True, check=False)
            self.assertEqual(second.returncode, 2)
            self.assertIn("refusing existing output path", second.stderr)
            clock_override = subprocess.run(cmd[:-2] + ["--now", "2026-09-13T15:30:00Z"] + cmd[-2:], text=True, capture_output=True, check=False)
            self.assertEqual(clock_override.returncode, 2)
            self.assertIn("unrecognized arguments: --now", clock_override.stderr)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unsupported")
    def test_cli_refuses_symlink_input(self) -> None:
        with tempfile.TemporaryDirectory() as td_raw:
            td = Path(td_raw)
            policy_real = td / "policy-real.json"
            policy_link = td / "policy-link.json"
            evidence = td / "evidence.json"
            out = td / "report.json"
            policy_real.write_bytes((HERE / "fixtures" / "policy.json").read_bytes())
            evidence.write_bytes((HERE / "fixtures" / "evidence.json").read_bytes())
            policy_link.symlink_to(policy_real)
            run = subprocess.run([
                sys.executable, str(HERE / "compiler.py"), "compile",
                "--policy", str(policy_link), "--evidence", str(evidence),
                "--expected-policy-sha256", POLICY_ROOT, "--out", str(out),
            ], text=True, capture_output=True, check=False)
            self.assertEqual(run.returncode, 2)
            self.assertIn("cannot open ordinary input file", run.stderr)

    def test_normal_and_optimized_fixed_time_report_bytes_match(self) -> None:
        code = f'''\nimport datetime as dt, sys\nfrom pathlib import Path\nsys.path.insert(0, {str(HERE)!r})\nimport compiler\np=compiler.loads_strict(Path({str(HERE / "fixtures" / "policy.json")!r}).read_bytes())\ne=compiler.loads_strict(Path({str(HERE / "fixtures" / "evidence.json")!r}).read_bytes())\nr=compiler.compile_report(p,e,expected_policy_sha256={POLICY_ROOT!r},now=dt.datetime(2026,9,13,15,30,0,tzinfo=dt.timezone.utc))\nsys.stdout.buffer.write(compiler.canon(r))\n'''
        normal = subprocess.run([sys.executable, "-c", code], capture_output=True, check=False)
        optimized = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, check=False)
        self.assertEqual(normal.returncode, 0, normal.stderr.decode())
        self.assertEqual(optimized.returncode, 0, optimized.stderr.decode())
        self.assertEqual(normal.stdout, optimized.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
