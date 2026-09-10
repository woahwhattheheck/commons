# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json
import random
import tempfile
import unittest
from pathlib import Path

from identity_firewall import (
    ContractError, audit_contract, disabled_identity_firewall,
    git_blob_sha1, run_identity_oracle,
)


class StaticTests(unittest.TestCase):
    def audit(self, source, *, call_rules=(), field_rules=()):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = source.encode()
            (root / "target.py").write_bytes(data)
            return audit_contract(root, {
                "source_ref": "fixture",
                "files": {"target.py": {"git_blob_sha1": git_blob_sha1(data)}},
                "call_rules": list(call_rules), "field_rules": list(field_rules),
                "expected_current_findings": [],
            })

    @staticmethod
    def rule(required=("alpha",)):
        return {"id": "call", "path": "target.py", "class": "P", "method": "act",
                "calls": ["self.optional"], "requires_any": list(required)}

    def test_git_blob_known_vector(self):
        self.assertEqual(git_blob_sha1(b"test content\n"), "d670460b4b4aece5915caf5c68d12f560a9fe3e4")

    def test_pre_gate_call_is_red(self):
        out = self.audit("class P:\n def act(self):\n  self.optional()\n  if not self.alpha:return\n", call_rules=[self.rule()])
        self.assertEqual(out["actual_findings"], ["call::unguarded_call::self.optional"])

    def test_fail_fast_gate_is_clean(self):
        out = self.audit("class P:\n def act(self):\n  if not self.alpha:return\n  self.optional()\n", call_rules=[self.rule()])
        self.assertEqual(out["actual_findings"], [])

    def test_any_domain_gate_is_clean(self):
        source = "class P:\n def act(self):\n  if not self.alpha and not self.beta:return\n  self.optional()\n"
        self.assertEqual(self.audit(source, call_rules=[self.rule(("alpha", "beta"))])["actual_findings"], [])

    def test_broad_gate_does_not_prove_narrow_feature(self):
        source = "class P:\n def act(self):\n  if self.alpha or self.beta:self.optional()\n"
        self.assertEqual(self.audit(source, call_rules=[self.rule()])["actual_findings"], ["call::unguarded_call::self.optional"])

    def test_call_in_if_test_is_red(self):
        source = "class P:\n def act(self):\n  if self.optional():return 1\n"
        self.assertEqual(self.audit(source, call_rules=[self.rule()])["actual_findings"], ["call::unguarded_call::self.optional"])

    def test_missing_feature_field(self):
        source = "class Features:\n alpha: bool=False\n"
        rule = {"id": "field", "path": "target.py", "class": "Features", "required": ["alpha", "beta"]}
        self.assertEqual(self.audit(source, field_rules=[rule])["actual_findings"], ["field::missing_field::beta"])

    def test_binding_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "target.py").write_text("x=1\n")
            with self.assertRaises(ContractError):
                audit_contract(root, {"files": {"target.py": {"git_blob_sha1": "0" * 40}}})


class DynamicTests(unittest.TestCase):
    class Base:
        def __init__(self): self.route = [["PASS"]]; self.pending = []
        def act(self, case): return {"action": copy.deepcopy(case)}
    class OutputDrift(Base):
        def act(self, case):
            out = super().act(case); out["action"]["market"] = [["SELL", "MILK", 1]]; return out
    class StateDrift(Base):
        def act(self, case): self.pending.append(case["step"]); return super().act(case)
    class RngDrift(Base):
        def act(self, case): random.random(); return super().act(case)

    def oracle(self, candidate):
        return run_identity_oracle(
            baseline_factory=self.Base, candidate_factory=candidate,
            cases=[{"step": 29, "market": []}, {"step": 30, "market": []}],
            invoke=lambda agent, case: agent.act(case),
            projections={"route": lambda agent: agent.route, "pending": lambda agent: agent.pending}, seed=7,
        )

    def test_equal(self): self.assertTrue(self.oracle(self.Base)["equal"])
    def test_output_drift(self): self.assertFalse(self.oracle(self.OutputDrift)["steps"][0]["surfaces"]["output"])
    def test_state_drift(self):
        step = self.oracle(self.StateDrift)["steps"][0]
        self.assertTrue(step["surfaces"]["output"]); self.assertFalse(step["surfaces"]["projection:pending"])
    def test_rng_drift(self): self.assertFalse(self.oracle(self.RngDrift)["steps"][0]["surfaces"]["python_random"])

    def test_disabled_hard_edge_never_invokes(self):
        calls = []; selected = {"market": []}
        def unsafe(_obs, action): calls.append(1); action["market"].append(["SELL", "MILK", 1]); random.random(); return action
        before = random.getstate()
        returned = disabled_identity_firewall(lambda: False, unsafe)({}, selected)
        self.assertIs(returned, selected); self.assertEqual(calls, []); self.assertEqual(random.getstate(), before)


class ExactRepositoryTest(unittest.TestCase):
    here = Path(__file__).resolve().parent
    root = here.parents[1]

    @unittest.skipUnless((root / "spatial_tempo.py").is_file(), "exact repository checkout not present")
    def test_pinned_current_finding_set(self):
        contract = json.loads((self.here / "contract.json").read_text())
        result = audit_contract(self.root, contract)
        self.assertTrue(result["expectation_matches"], result)
        self.assertFalse(result["clean"], "update contract after the source repair lands")


if __name__ == "__main__":
    unittest.main()
