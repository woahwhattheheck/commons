import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from host import scope_to_delivery_time_authority as authority
from host import scope_to_delivery_time_gate as gate
from test_scope_to_delivery_time_gate import dynamic_agreement, project, raw


class ReviewedRedClosureTests(unittest.TestCase):
    def test_transitive_gate_helper_rebinding_cannot_promote_expired_source(self):
        doc = dynamic_agreement("expired")
        p = project(doc)

        original_temporal = authority._temporal_facts
        original_historical = authority._historical_project
        original_receipt_base = authority._receipt_base
        original_compose = authority.canonical_scope.compose_project
        original_run_name = authority.subprocess.run

        def fake_temporal(*args, **kwargs):
            return {
                "agreement_id": doc["agreement_id"],
                "state": "TEMPORAL_PREREQUISITE_READY",
                "temporal_ready": True,
                "trusted_as_of": "2026-09-13T11:00:00Z",
                "window_start": "2026-09-13T10:00:00Z",
                "window_end": "2026-09-13T12:00:00Z",
                "accepted_at": "2026-09-13T09:30:00Z",
                "agreement_canonical_sha256": "0" * 64,
                "observations_canonical_sha256": None,
                "observation_count": 0,
                "historical_evidence_temporally_admissible": False,
            }

        try:
            authority._temporal_facts = fake_temporal
            authority._historical_project = lambda *a, **k: p
            authority._receipt_base = lambda *a, **k: {
                "state": "TEMPORAL_PREREQUISITE_READY"
            }
            authority.canonical_scope.compose_project = lambda *a, **k: p
            authority.subprocess.run = lambda *a, **k: (_ for _ in ()).throw(
                AssertionError("public subprocess.run rebinding was consulted")
            )
            verdict = gate.verify_current_work_authority(
                raw(doc), None, canonical_project=p
            )
        finally:
            authority._temporal_facts = original_temporal
            authority._historical_project = original_historical
            authority._receipt_base = original_receipt_base
            authority.canonical_scope.compose_project = original_compose
            authority.subprocess.run = original_run_name

        self.assertFalse(verdict["valid"])
        self.assertEqual(verdict["state"], "HOLD_WINDOW_EXPIRED")

    def test_large_integer_resource_limit_is_controlled(self):
        hostile = b'{"x":' + (b"9" * 5000) + b"}"
        with self.assertRaises(authority.TemporalAuthorityError):
            gate.strict_loads(hostile, "hostile")

    def test_cli_large_integer_returns_controlled_two_normal_and_optimized(self):
        good = dynamic_agreement("ready")
        p = project(good)
        encoded = raw(good)
        hostile = encoded[:-1] + b',"resource_bomb":' + (b"9" * 5000) + b"}"

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            agreement_path = root / "agreement.json"
            project_path = root / "project.json"
            agreement_path.write_bytes(hostile)
            project_path.write_bytes(raw(p))
            for optimized in (False, True):
                cmd = [sys.executable]
                if optimized:
                    cmd.append("-O")
                cmd.extend(
                    [
                        str(Path(gate.__file__)),
                        "--agreement",
                        str(agreement_path),
                        "--project",
                        str(project_path),
                    ]
                )
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=30
                )
                self.assertEqual(
                    result.returncode, 2, result.stdout + result.stderr
                )
                self.assertNotIn("Traceback", result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(
                    payload["state"], "HOLD_INVALID_TEMPORAL_EVIDENCE"
                )
                self.assertIn("bounded JSON", payload["error"])

    def test_optimized_transitive_rebinding_predecessor(self):
        code = r'''
from host import scope_to_delivery_time_authority as authority
from host import scope_to_delivery_time_gate as gate
from test_scope_to_delivery_time_gate import dynamic_agreement, project, raw
doc = dynamic_agreement("expired")
p = project(doc)
authority._temporal_facts = lambda *a, **k: {
    "agreement_id": doc["agreement_id"],
    "state": "TEMPORAL_PREREQUISITE_READY",
    "temporal_ready": True,
    "trusted_as_of": "2026-09-13T11:00:00Z",
    "window_start": "2026-09-13T10:00:00Z",
    "window_end": "2026-09-13T12:00:00Z",
    "accepted_at": "2026-09-13T09:30:00Z",
    "agreement_canonical_sha256": "0" * 64,
    "observations_canonical_sha256": None,
    "observation_count": 0,
    "historical_evidence_temporally_admissible": False,
}
authority._historical_project = lambda *a, **k: p
authority._receipt_base = lambda *a, **k: {"state": "TEMPORAL_PREREQUISITE_READY"}
authority.canonical_scope.compose_project = lambda *a, **k: p
verdict = gate.verify_current_work_authority(raw(doc), None, canonical_project=p)
assert verdict["valid"] is False, verdict
assert verdict["state"] == "HOLD_WINDOW_EXPIRED", verdict
try:
    gate.strict_loads(b'{"x":' + b'9' * 5000 + b'}', "hostile")
except authority.TemporalAuthorityError:
    pass
else:
    raise AssertionError("large integer escaped strict loader")
'''
        result = subprocess.run(
            [sys.executable, "-O", "-c", code],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
