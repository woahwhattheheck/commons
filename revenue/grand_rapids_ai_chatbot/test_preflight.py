import copy
import json
import unittest
from pathlib import Path

from preflight import REQUIRED_GATES, SCHEMA_VERSION, evaluate

HERE = Path(__file__).resolve().parent


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.state = json.loads((HERE / "submission_state.json").read_text(encoding="utf-8"))

    def test_current_state_is_hold(self):
        receipt = evaluate(self.state)
        self.assertEqual("HOLD", receipt["status"])
        self.assertFalse(receipt["errors"])
        self.assertGreater(len(receipt["blockers"]), 1)

    def test_digest_is_deterministic(self):
        a = evaluate(self.state)["state_sha256"]
        b = evaluate(json.loads(json.dumps(self.state)))["state_sha256"]
        self.assertEqual(a, b)

    def test_wrong_schema_is_invalid(self):
        s = copy.deepcopy(self.state); s["schema_version"] = "wrong"
        self.assertEqual("INVALID", evaluate(s)["status"])

    def test_wrong_solicitation_is_invalid(self):
        s = copy.deepcopy(self.state); s["solicitation_id"] = "other"
        self.assertEqual("INVALID", evaluate(s)["status"])

    def test_missing_gate_is_invalid(self):
        s = copy.deepcopy(self.state); del s["gates"][REQUIRED_GATES[0]]
        self.assertEqual("INVALID", evaluate(s)["status"])

    def test_unknown_gate_is_invalid(self):
        s = copy.deepcopy(self.state); s["gates"]["magic"] = {"status":"HOLD","evidence":[],"reason":"no"}
        self.assertEqual("INVALID", evaluate(s)["status"])

    def test_pass_requires_evidence(self):
        s = copy.deepcopy(self.state)
        s["gates"]["controlling_packet_acquired"] = {"status":"PASS","evidence":[],"reason":"claimed"}
        self.assertEqual("INVALID", evaluate(s)["status"])

    def test_placeholder_evidence_cannot_pass(self):
        s = copy.deepcopy(self.state)
        s["gates"]["controlling_packet_acquired"] = {"status":"PASS","evidence":["placeholder:packet"],"reason":"claimed"}
        self.assertEqual("INVALID", evaluate(s)["status"])

    def test_unknown_evidence_cannot_pass(self):
        s = copy.deepcopy(self.state)
        s["gates"]["controlling_packet_acquired"] = {"status":"PASS","evidence":["unknown:packet"],"reason":"claimed"}
        self.assertEqual("INVALID", evaluate(s)["status"])

    def test_gate_requires_reason(self):
        s = copy.deepcopy(self.state); s["gates"]["pricing_form_complete"]["reason"] = ""
        self.assertEqual("INVALID", evaluate(s)["status"])

    def test_all_explicit_pass_can_be_ready(self):
        s = {"schema_version": SCHEMA_VERSION, "solicitation_id": "920-45-269", "gates": {}}
        for gate in REQUIRED_GATES:
            s["gates"][gate] = {"status":"PASS","evidence":[f"sha256:{gate}"],"reason":"verified fixture evidence"}
        r = evaluate(s)
        self.assertEqual("READY", r["status"])
        self.assertFalse(r["blockers"])
        self.assertFalse(r["errors"])

    def test_owner_release_alone_cannot_make_ready(self):
        s = copy.deepcopy(self.state)
        s["gates"]["owner_release_to_submit"] = {"status":"PASS","evidence":["owner:event"],"reason":"owner released"}
        self.assertEqual("HOLD", evaluate(s)["status"])

    def test_packet_alone_cannot_make_ready(self):
        s = copy.deepcopy(self.state)
        for g in ("controlling_packet_acquired", "packet_sha256_verified"):
            s["gates"][g] = {"status":"PASS","evidence":[f"sha256:{g}"],"reason":"packet held"}
        self.assertEqual("HOLD", evaluate(s)["status"])


if __name__ == "__main__":
    unittest.main()
