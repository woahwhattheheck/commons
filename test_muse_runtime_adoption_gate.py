from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from coordination import muse_runtime_adoption_gate as g


class MuseRuntimeAdoptionGateTests(unittest.TestCase):
    NOW = 2_000_000_000

    def sha(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def event(self, cls: str, sec: int, *, session="session-a", event_id=None, **overrides):
        raw = {
            "id": event_id or f"e-{cls.lower()}-{sec}",
            "event_class": cls,
            "occurred_at": __import__("datetime").datetime.fromtimestamp(
                sec, tz=__import__("datetime").timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "operation_key": "USP-COMPUGEN-20260917",
            "counterparty": "Compugen Inc.",
            "route": "hello@example.test",
            "purpose": "paid teaming qualification",
            "lease_id": "lease-123",
            "session": session,
            "runtime_instance_id": "muse-prod-1",
            "runtime_build_id": "build-atomic-7",
            "runtime_source_sha256": self.sha("runtime-source"),
            "source_ref": f"slack://retained/{cls.lower()}/{sec}",
            "source_sha256": self.sha(f"source-{cls}-{sec}"),
        }
        if cls in {"CONSUMED", "GO", "COMMIT"}:
            raw["capability_sha256"] = self.sha("capability-one")
        if cls == "COMMIT":
            raw["provider"] = "gmail"
            raw["provider_message_id"] = "message-1"
        raw.update(overrides)
        return raw

    def packet(self, classes=("SELECTED", "LEASED", "CONSUMED", "GO"), *, capture=None, max_age=300):
        base = self.NOW - 20
        events = [self.event(cls, base + i + 1) for i, cls in enumerate(classes)]
        capture_sec = capture if capture is not None else self.NOW - 5
        ts = __import__("datetime").datetime.fromtimestamp(capture_sec, tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "schema": "commons.muse-runtime-adoption-evidence/v1",
            "operation_key": "USP-COMPUGEN-20260917",
            "counterparty": "Compugen Inc.",
            "route": "hello@example.test",
            "purpose": "paid teaming qualification",
            "lease_id": "lease-123",
            "selected_session": "session-a",
            "runtime": {
                "instance_id": "muse-prod-1",
                "build_id": "build-atomic-7",
                "source_sha256": self.sha("runtime-source"),
            },
            "capture": {"captured_at": ts, "max_age_seconds": max_age},
            "transcript_source_ref": "slack-export://muse/retained/one",
            "transcript_source_sha256": self.sha("transcript"),
            "events": events,
        }

    def compile(self, packet, now=None):
        return g._compile_at_for_test(packet, self.NOW if now is None else now)

    def assert_hard_false(self, diagnostic):
        for value in diagnostic["authority"].values():
            self.assertIs(value, False)
        self.assertFalse(diagnostic["evidence_claims"]["runtime_deployment_independently_authenticated"])
        self.assertFalse(diagnostic["evidence_claims"]["provider_send_independently_authenticated"])

    def test_positive_atomic_sequence_is_diagnostic_only(self):
        out = self.compile(self.packet())
        self.assertEqual(out["status"], "ATOMIC_SEQUENCE_OBSERVED")
        self.assertTrue(out["atomic_sequence_consistent"])
        self.assertTrue(out["evidence_claims"]["retained_transcript_internally_consistent"])
        self.assert_hard_false(out)

    def test_selected_only_predecessor_holds(self):
        out = self.compile(self.packet(("SELECTED",)))
        self.assertEqual(out["status"], "HOLD_SELECTED_ONLY")
        self.assert_hard_false(out)

    def test_selected_lease_without_consume_holds(self):
        out = self.compile(self.packet(("SELECTED", "LEASED")))
        self.assertEqual(out["status"], "HOLD_NO_CONSUME")

    def test_consumed_without_go_holds(self):
        out = self.compile(self.packet(("SELECTED", "LEASED", "CONSUMED")))
        self.assertEqual(out["status"], "HOLD_NO_GO")

    def test_duplicate_go_holds(self):
        p = self.packet(("SELECTED", "LEASED", "CONSUMED", "GO", "GO"))
        p["events"][4]["id"] = "second-go"
        out = self.compile(p)
        self.assertEqual(out["status"], "HOLD_DUPLICATE_GO")

    def test_wrong_session_holds(self):
        p = self.packet()
        p["events"][3]["session"] = "session-b"
        self.assertEqual(self.compile(p)["status"], "HOLD_WRONG_SESSION")

    def test_scope_transplant_holds(self):
        p = self.packet()
        p["events"][2]["route"] = "other@example.test"
        self.assertEqual(self.compile(p)["status"], "HOLD_SCOPE_DRIFT")

    def test_runtime_transplant_holds(self):
        p = self.packet()
        p["events"][2]["runtime_build_id"] = "other-build"
        self.assertEqual(self.compile(p)["status"], "HOLD_RUNTIME_DRIFT")

    def test_capability_mismatch_holds(self):
        p = self.packet()
        p["events"][3]["capability_sha256"] = self.sha("other-capability")
        self.assertEqual(self.compile(p)["status"], "HOLD_EVIDENCE")

    def test_optional_commit_coherent_but_not_provider_proof(self):
        out = self.compile(self.packet(("SELECTED", "LEASED", "CONSUMED", "GO", "COMMIT")))
        self.assertEqual(out["status"], "ATOMIC_SEQUENCE_OBSERVED")
        self.assertTrue(out["provider_commit_observed"])
        self.assertEqual(out["provider_commit"]["provider_message_id"], "message-1")
        self.assertFalse(out["authority"]["provider_send_proven"])

    def test_commit_capability_tamper_holds(self):
        p = self.packet(("SELECTED", "LEASED", "CONSUMED", "GO", "COMMIT"))
        p["events"][4]["capability_sha256"] = self.sha("other")
        self.assertEqual(self.compile(p)["status"], "HOLD_EVIDENCE")

    def test_stale_boundary_exact_then_first_second(self):
        capture = self.NOW - 300
        p = self.packet(capture=capture, max_age=300)
        for i, event in enumerate(p["events"]):
            sec = capture - 10 + i
            event["occurred_at"] = __import__("datetime").datetime.fromtimestamp(
                sec, tz=__import__("datetime").timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertEqual(self.compile(p, self.NOW)["status"], "ATOMIC_SEQUENCE_OBSERVED")
        self.assertEqual(self.compile(p, self.NOW + 1)["status"], "HOLD_STALE_CAPTURE")

    def test_future_capture_and_future_event_hold_evidence(self):
        p = self.packet(capture=self.NOW + 1)
        self.assertEqual(self.compile(p)["status"], "HOLD_EVIDENCE")
        p = self.packet()
        future = self.NOW + 1
        p["events"][-1]["occurred_at"] = __import__("datetime").datetime.fromtimestamp(future, tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertEqual(self.compile(p)["status"], "HOLD_EVIDENCE")

    def test_reordered_or_equal_time_rejected(self):
        p = self.packet()
        p["events"][2], p["events"][3] = p["events"][3], p["events"][2]
        with self.assertRaises(g.AdoptionGateError):
            self.compile(p)
        p = self.packet()
        p["events"][2]["occurred_at"] = p["events"][1]["occurred_at"]
        with self.assertRaises(g.AdoptionGateError):
            self.compile(p)

    def test_duplicate_event_id_and_changed_same_id_rejected(self):
        p = self.packet()
        p["events"][3]["id"] = p["events"][2]["id"]
        with self.assertRaises(g.AdoptionGateError):
            self.compile(p)

    def test_strict_json_duplicate_float_bool_and_surrogate(self):
        with self.assertRaises(g.AdoptionGateError):
            g.loads_strict('{"a":1,"a":2}')
        with self.assertRaises(g.AdoptionGateError):
            g.loads_strict('{"a":1.5}')
        p = self.packet()
        p["capture"]["max_age_seconds"] = True
        with self.assertRaises(g.AdoptionGateError):
            self.compile(p)
        with self.assertRaises(g.AdoptionGateError):
            g.loads_strict('"\\ud800"')

    def test_huge_integer_and_excess_depth_are_stable_domain_errors(self):
        with self.assertRaises(g.AdoptionGateError):
            g.loads_strict('{"a":' + '9' * 5000 + '}')
        deep = '[' * 30 + '0' + ']' * 30
        with self.assertRaises(g.AdoptionGateError):
            g.loads_strict(deep)

    def test_receipt_and_input_tamper_fail_verification(self):
        p = self.packet()
        d = self.compile(p)
        ok, reason, _ = g.verify_artifact(p, d)
        self.assertTrue(ok, reason)
        bad = copy.deepcopy(d)
        bad["status"] = "HOLD_EVIDENCE"
        ok, reason, _ = g.verify_artifact(p, bad)
        self.assertFalse(ok)
        self.assertEqual(reason, "receipt_mismatch")
        changed = copy.deepcopy(p)
        changed["purpose"] = "different purpose"
        ok, reason, _ = g.verify_artifact(changed, d)
        self.assertFalse(ok)

    def test_resealed_semantic_tamper_still_fails_exact_recompile(self):
        p = self.packet()
        d = self.compile(p)
        bad = copy.deepcopy(d)
        bad["status"] = "HOLD_EVIDENCE"
        unsigned = dict(bad)
        unsigned.pop("receipt_sha256")
        bad["receipt_sha256"] = hashlib.sha256(g.canonical_json(unsigned)).hexdigest()
        ok, reason, _ = g.verify_artifact(p, bad)
        self.assertFalse(ok)
        self.assertEqual(reason, "semantic_recompile_mismatch")

    def test_public_semantic_and_stdlib_mirror_poisoning_does_not_steer_generation(self):
        p = self.packet()
        baseline = self.compile(p)
        saved = {
            "authority": g._AUTHORITY,
            "status": g._STATUS,
            "event_classes": g._EVENT_CLASSES,
            "input_schema": g._INPUT_SCHEMA,
            "hashlib": g._hashlib,
            "json": g._json,
            "path": g._Path,
            "error": g.AdoptionGateError,
        }
        try:
            g._AUTHORITY = {"send_authorized": True, "revenue_recognized": True}
            g._STATUS = frozenset({"FORGED"})
            g._EVENT_CLASSES = frozenset({"FORGED"})
            g._INPUT_SCHEMA = "forged"
            g._hashlib = type("HashPoison", (), {"sha256": staticmethod(lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("poison")))})
            g._json = type("JsonPoison", (), {})
            g._Path = lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("poison"))
            g.AdoptionGateError = RuntimeError
            after = self.compile(p)
            self.assertEqual(g.canonical_json(after), g.canonical_json(baseline))
            self.assert_hard_false(after)
        finally:
            g._AUTHORITY = saved["authority"]
            g._STATUS = saved["status"]
            g._EVENT_CLASSES = saved["event_classes"]
            g._INPUT_SCHEMA = saved["input_schema"]
            g._hashlib = saved["hashlib"]
            g._json = saved["json"]
            g._Path = saved["path"]
            g.AdoptionGateError = saved["error"]

    def test_public_clock_rebind_does_not_steer_current_api(self):
        original = getattr(g, "_time", None)
        g._time = type("Fake", (), {"time_ns": staticmethod(lambda: 1)})
        try:
            p = self.packet(capture=int(__import__("time").time()), max_age=60)
            out = g.compile_current(p)
            self.assertGreater(out["evaluated_at"], "1970-01-01T00:00:01Z")
        finally:
            if original is not None:
                g._time = original

    def test_cli_compile_and_verify_current(self):
        now = int(__import__("time").time())
        p = self.packet(capture=now, max_age=60)
        for i, event in enumerate(p["events"]):
            sec = now - 10 + i
            event["occurred_at"] = __import__("datetime").datetime.fromtimestamp(sec, tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            packet_path = td / "packet.json"
            diag_path = td / "diag.json"
            packet_path.write_text(json.dumps(p, separators=(",", ":")), encoding="utf-8")
            cmd = [sys.executable, "coordination/muse_runtime_adoption_gate.py", "compile", "--input", str(packet_path)]
            cp = subprocess.run(cmd, cwd=Path(__file__).parent, capture_output=True, check=False)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(cp.stdout, b"")
            d = g.compile_current(p)
            self.assertEqual(d["status"], "ATOMIC_SEQUENCE_OBSERVED")
            diag_path.write_bytes(g.canonical_json(d))
            cp2 = subprocess.run(
                [sys.executable, "coordination/muse_runtime_adoption_gate.py", "verify", "--input", str(packet_path), "--diagnostic", str(diag_path)],
                cwd=Path(__file__).parent,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp2.returncode, 0, cp2.stdout + cp2.stderr)
            self.assertEqual(cp2.stdout, b"")


if __name__ == "__main__":
    unittest.main()
