"""Exercise diagnostic schema serialization with the real publication checker.

Only pure production functions are compiled from their source AST, avoiding
service-provider initialization. The receipt backend is a recording fixture;
these tests do not execute payments, the full equipment catalog, or Slack.

Run: python -B tests/test_diagnostic_catalog_publication.py -v
"""
from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from commons_publication_policy import check_publication, require_publication

EQUIPMENT = ROOT / "integrations" / "shared_equipment"


def load_function(path: Path, name: str, namespace: dict) -> Any:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    matches = [node for node in tree.body
               if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise AssertionError(f"Expected exactly one {name} in {path}")
    unit = ast.Module(body=matches, type_ignores=[])
    exec(compile(unit, str(path), "exec"), namespace)
    return namespace[name]


class DiagnosticCatalogPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        namespace = {"Any": Any}
        load_function(EQUIPMENT / "services.py", "_schema", namespace)
        cls.schemas = staticmethod(load_function(
            EQUIPMENT / "diagnostic_equipment_cards.py",
            "diagnostic_card_tool_schemas", namespace))

    def setUp(self):
        self.cards = self.schemas()
        self.receipt = next(card for card in self.cards
                            if card["name"] == "autopsy_receipt_card")

    def test_identifier_is_code_and_keeps_the_documented_state(self):
        self.assertIn("Default state `UNVERIFIED`.", self.receipt["description"])
        self.assertEqual(self.receipt["description"].count("`"), 2)

    def test_receipt_description_passes_existing_checker(self):
        self.assertTrue(require_publication(self.receipt["description"])["allowed"])

    def test_complete_diagnostic_family_serializes_and_passes(self):
        self.assertEqual(len(self.cards), len({c["name"] for c in self.cards}))
        for indent in (None, 2):
            for ascii_only in (True, False):
                with self.subTest(indent=indent, ensure_ascii=ascii_only):
                    body = json.dumps({"tools": self.cards}, indent=indent,
                                      ensure_ascii=ascii_only)
                    self.assertEqual(json.loads(body)["tools"], self.cards)
                    self.assertTrue(require_publication(body)["allowed"])

    def test_original_description_reproduces_the_reported_rule(self):
        original = self.receipt["description"].replace("`UNVERIFIED`", "UNVERIFIED")
        for body in (original, json.dumps({**self.receipt, "description": original})):
            with self.subTest(serialized=body.startswith("{")):
                decision = check_publication(body)
                self.assertFalse(decision["allowed"])
                self.assertEqual(decision["rule"], "general_disagreement")

    def test_original_diagnostic_family_reproduces_the_rule(self):
        old_cards = copy.deepcopy(self.cards)
        next(c for c in old_cards if c["name"] == "autopsy_receipt_card")[
            "description"] = self.receipt["description"].replace("`UNVERIFIED`", "UNVERIFIED")
        decision = check_publication(json.dumps({"tools": old_cards}))
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["rule"], "general_disagreement")

    def test_input_contract_remains_exact(self):
        self.assertEqual(self.receipt["inputSchema"], {
            "type": "object",
            "properties": {
                "role": {"type": "object"},
                "case_ref": {"type": "string"},
                "client_reference_id": {"type": "string"},
                "sku": {"type": "string"},
                "g2_run_id": {"type": "string"},
                "g2_session_id": {"type": "string"},
                "payment_observed_at": {"type": "string"},
                "state": {"type": "string"},
            },
            "required": ["role", "case_ref"],
        })

    def test_handler_keeps_default_and_explicit_state_values(self):
        calls = []

        def record(role, **kwargs):
            calls.append((role, kwargs))
            return {"state": kwargs["state"]}

        modules = {
            "roles": SimpleNamespace(RoleError=ValueError),
            "autopsy_paid": SimpleNamespace(build_receipt_row_from_role=record),
        }
        namespace = {"Any": Any, "_load_transferable_roles_mod": modules.__getitem__}
        handler = load_function(EQUIPMENT / "diagnostic_equipment_cards.py",
                                "call_diagnostic_card", namespace)
        cases = ({}, {"state": None}, {"state": ""}, {"state": "UNVERIFIED"},
                 {"state": "PAID"}, {"state": "custom_state"})
        expected = ("UNVERIFIED", "UNVERIFIED", "UNVERIFIED", "UNVERIFIED",
                    "PAID", "custom_state")
        for extra, state in zip(cases, expected):
            with self.subTest(extra=extra):
                role = {"role_id": "fixture-role"}
                args = {"role": role, "case_ref": "fixture-case", **extra}
                original = copy.deepcopy(args)
                result = handler("autopsy_receipt_card", args)
                self.assertEqual(result, {"ok": True, "card": {"state": state}})
                self.assertEqual(calls[-1][1]["state"], state)
                self.assertEqual(calls[-1][1]["case_ref"], "fixture-case")
                self.assertIs(calls[-1][0], role)
                self.assertEqual(args, original)
        self.assertEqual(len(calls), len(cases))


if __name__ == "__main__":
    unittest.main()
