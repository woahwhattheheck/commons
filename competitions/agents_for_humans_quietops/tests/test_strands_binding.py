"""Contract tests for Strands wiring without needing model/provider credentials.

A tiny fake `strands` module exercises closure binding and tool surfaces. Official live
SDK execution remains a separate provider-side submission checklist item.
"""
import copy
import importlib
import sys
import types
import unittest

from quietops.core import QuietOpsError

H = "7" * 64


def safe_item():
    return {
        "task_id":"safe-1", "event_id":"event-safe-1", "kind":"RECONCILE_RECORDS",
        "action":"reconcile", "evidence":[{"ref":"x://1","sha256":H}],
        "confidence_bps":10000, "ambiguous_evidence":False, "external_effect":False,
        "context":{"expected_minor":100,"observed_minor":100,"currency":"USD"},
    }


def human_item():
    return {
        "task_id":"human-1", "event_id":"event-human-1", "kind":"CONTACT_CUSTOMER",
        "action":"send offer", "evidence":[{"ref":"x://2","sha256":H}],
        "confidence_bps":10000, "ambiguous_evidence":False, "external_effect":True,
        "amount_minor":350000,
    }


class FakeState:
    def __init__(self): self.values = {}
    def set(self, k, v): self.values[k] = v


class FakeAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.name = kwargs.get("name")
        self.description = kwargs.get("description")
        self.tools = kwargs.get("tools", [])
        self.state = FakeState()
    def __call__(self, prompt): return f"fake:{self.name}:{prompt}"


def fake_tool(fn):
    fn.__quietops_fake_tool__ = True
    return fn


class StrandsBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = sys.modules.get("strands")
        fake = types.ModuleType("strands")
        fake.Agent = FakeAgent
        fake.tool = fake_tool
        sys.modules["strands"] = fake
        sys.modules.pop("quietops.strands_app", None)
        cls.mod = importlib.import_module("quietops.strands_app")

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop("quietops.strands_app", None)
        if cls.old is None: sys.modules.pop("strands", None)
        else: sys.modules["strands"] = cls.old

    def _named_tool(self, root, name):
        for t in root.tools:
            if callable(t) and getattr(t, "__name__", "") == name:
                return t
        self.fail(f"tool missing: {name}")

    def test_bound_tool_has_no_item_parameter(self):
        root = self.mod.build_agents(safe_item())
        inspect = self._named_tool(root, "inspect_bound_work_item")
        with self.assertRaises(TypeError): inspect({"kind":"CONTACT_CUSTOMER"})

    def test_original_caller_object_mutation_cannot_change_bound_generation(self):
        item = safe_item()
        root = self.mod.build_agents(item)
        inspect = self._named_tool(root, "inspect_bound_work_item")
        before = inspect()["decision"]
        item["kind"] = "CONTACT_CUSTOMER"
        item["external_effect"] = True
        after = inspect()["decision"]
        self.assertEqual(before["input_sha256"], after["input_sha256"])
        self.assertEqual(after["authority"], "AUTONOMOUS_REVERSIBLE")

    def test_human_bound_item_execution_tool_is_closed(self):
        root = self.mod.build_agents(human_item())
        execute = self._named_tool(root, "execute_bound_reversible_work")
        with self.assertRaises(QuietOpsError): execute()

    def test_safe_bound_item_execution_mints_receipt(self):
        root = self.mod.build_agents(safe_item())
        execute = self._named_tool(root, "execute_bound_reversible_work")
        out = execute()
        self.assertEqual(out["decision"]["authority"], "AUTONOMOUS_REVERSIBLE")
        self.assertIsNotNone(out["receipt"])

    def test_human_decision_card_never_claims_external_action(self):
        root = self.mod.build_agents(human_item())
        card = self._named_tool(root, "human_decision_card")()
        self.assertEqual(card["authority"], "HUMAN_DECISION_REQUIRED")
        self.assertFalse(card["external_action_taken"])

    def test_root_state_binds_input_and_operation(self):
        root = self.mod.build_agents(safe_item())
        self.assertEqual(len(root.state.values["quietops_bound_input_sha256"]), 64)
        self.assertEqual(len(root.state.values["quietops_operation_id"]), 64)


if __name__ == "__main__": unittest.main()
