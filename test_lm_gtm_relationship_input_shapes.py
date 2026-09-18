#!/usr/bin/env python3
"""Exercise real handoff validation/helpers with temporary JSONL, without live ledgers.

Load only the production symbols used by this boundary. This avoids unrelated
mailbox imports and CRM composition, and does not replace the parser, validation,
projection, or file I/O with mocks. Full CLI/integration tests remain separate.
"""
from __future__ import annotations

import ast
import copy
import datetime as dt
import json
import re
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def load_symbols(relative_path, names, **extra):
    path = ROOT / relative_path
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    nodes, found = [], set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            declared = {node.name}
        elif isinstance(node, ast.Assign):
            declared = {t.id for t in node.targets if isinstance(t, ast.Name)}
        else:
            continue
        if declared & names:
            nodes.append(node)
            found.update(declared & names)
    if found != names:
        raise AssertionError(f"Missing production symbols in {path}: {names - found}")
    namespace = dict(dt=dt, json=json, re=re, Path=Path, Any=Any, ROOT=ROOT, **extra)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return types.SimpleNamespace(**namespace)


idx = load_symbols("host/lm_gtm_index.py", {
    "SCHEMA_VERSION", "SUBJECT_RE", "EVENT_ID_RE", "EMAIL_AT_RE", "PHONE_RE",
    "LIVE_ROLES", "DUE_RE", "IndexError_", "parse_time", "load_jsonl",
    "_assert_no_pii_in_index_blob",
})
handoff = load_symbols("host/lm_gtm_relationship_handoff.py", {
    "KIND_RELATIONSHIP_EVIDENCE", "RELATIONSHIP_EVIDENCE_REL",
    "RELATIONSHIP_EVIDENCE_TYPES", "SOURCE_RELATIONSHIP_EVIDENCE",
    "_INTERNAL_SOURCE", "_relationship_evidence_path", "_load_relationship_evidence",
    "_event_paths", "_apply_relationship_evidence",
}, idx=idx)


class RelationshipInputShapesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / handoff.RELATIONSHIP_EVIDENCE_REL
        self.path.parent.mkdir(parents=True)
        self.record = {
            "schema_version": idx.SCHEMA_VERSION,
            "kind": handoff.KIND_RELATIONSHIP_EVIDENCE,
            "id": "synthetic-event-001",
            "subject_id": "synthetic-customer",
            "type": "STATUS",
            "cash_usd": 0,
            "transport": "NONE",
            "ts": "2026-09-08T11:00:00Z",
            "source_paths": ["synthetic:note"],
            "decision": "OWNER_HOLD",
            "dnr": True,
            "due": "2026-09-28",
            "next_action": "Continue the recorded workflow.",
        }

    def load(self, *records, canonical=()):
        self.path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
        before = self.path.read_bytes()
        try:
            return handoff._load_relationship_evidence({"root": self.root}, set(canonical))
        finally:
            self.assertEqual(self.path.read_bytes(), before, "validation rewrote evidence")

    def assert_invalid(self, field, values, message, event_type="STATUS"):
        for value in values:
            with self.subTest(field=field, value=value, event_type=event_type):
                row = dict(self.record, type=event_type, role="external_prospect", organization="Synthetic shop")
                row[field] = value
                with self.assertRaisesRegex(idx.IndexError_, message):
                    self.load(row)

    def test_type_arrays(self):
        self.assert_invalid("type", [[], ["STATUS"]], "illegal type")

    def test_type_objects(self):
        self.assert_invalid("type", [{}, {"type": "STATUS"}], "illegal type")

    def test_type_other_invalid_json_values(self):
        self.assert_invalid("type", [None, True, False, 0, 2.5, "", "UNKNOWN"], "illegal type")

    def test_transport_arrays(self):
        self.assert_invalid("transport", [[], ["NONE"]], "claimed transport")

    def test_transport_objects(self):
        self.assert_invalid("transport", [{}, {"transport": "NONE"}], "claimed transport")

    def test_transport_other_invalid_json_values(self):
        self.assert_invalid("transport", [True, False, 0, 2.5, "", "SMTP"], "claimed transport")

    def test_role_arrays_for_both_pointer_types(self):
        for event_type in ("MATERIAL_REPLY", "SENT_AWAITING_REPLY"):
            self.assert_invalid("role", [[], ["external_prospect"]], "cannot cite role", event_type)

    def test_role_objects_for_both_pointer_types(self):
        for event_type in ("MATERIAL_REPLY", "SENT_AWAITING_REPLY"):
            self.assert_invalid("role", [{}, {"role": "inbound_contact"}], "cannot cite role", event_type)

    def test_role_other_invalid_json_values(self):
        self.assert_invalid("role", [None, True, False, 0, 2.5, "", "seller_context"], "cannot cite role", "MATERIAL_REPLY")

    def test_valid_status_preserves_every_field(self):
        original = copy.deepcopy(self.record)
        rows = self.load(self.record)
        expected = dict(original, **{handoff._INTERNAL_SOURCE: handoff.SOURCE_RELATIONSHIP_EVIDENCE})
        self.assertEqual(rows, [expected])
        self.assertEqual(self.record, original)

    def test_valid_pointer_types_roles_and_transport(self):
        for event_type in ("MATERIAL_REPLY", "SENT_AWAITING_REPLY"):
            for role in ("external_prospect", "inbound_contact"):
                for transport in (None, "NONE"):
                    with self.subTest(event_type=event_type, role=role, transport=transport):
                        row = dict(self.record, type=event_type, role=role, transport=transport, organization="Synthetic shop")
                        expected = dict(row, **{handoff._INTERNAL_SOURCE: handoff.SOURCE_RELATIONSHIP_EVIDENCE})
                        self.assertEqual(self.load(row), [expected])

    def test_transport_may_remain_absent(self):
        row = dict(self.record)
        del row["transport"]
        self.assertNotIn("transport", self.load(row)[0])

    def test_status_does_not_require_pointer_role(self):
        row = dict(self.record, role={"context": "retained"})
        self.assertEqual(self.load(row)[0]["role"], row["role"])

    def test_empty_and_absent_evidence_remain_empty(self):
        self.assertEqual(handoff._load_relationship_evidence({"root": self.root}, set()), [])
        self.assertEqual(self.load(), [])
        self.path.write_text("\n  \n", encoding="utf-8")
        self.assertEqual(handoff._load_relationship_evidence({"root": self.root}, set()), [])

    def test_existing_id_collisions_remain_diagnostic(self):
        with self.assertRaisesRegex(idx.IndexError_, "id collision"):
            self.load(self.record, self.record)
        with self.assertRaisesRegex(idx.IndexError_, "id collision"):
            self.load(self.record, canonical=[self.record["id"]])

    def test_existing_source_path_validation_remains(self):
        self.assert_invalid("source_paths", [None, [], {}, "synthetic:note", [None], [""]], "missing source_paths")

    def test_non_object_jsonl_remains_diagnostic(self):
        for row in ([], None, "record", 7):
            with self.subTest(row=row), self.assertRaisesRegex(idx.IndexError_, "must be a JSON object"):
                self.load(row)

    def test_valid_then_invalid_does_not_return_partial_or_write(self):
        row = dict(self.record, id="synthetic-event-002", transport=[])
        with self.assertRaisesRegex(idx.IndexError_, "claimed transport"):
            self.load(self.record, row)

    def test_valid_projection_preserves_existing_row_and_hold(self):
        events = self.load(self.record)
        row = {"source_paths": ["synthetic:original"], "overlay_event_ids": ["canonical-event-001"], "decision": "SENT_AWAITING_REPLY", "dnr": False}
        original = copy.deepcopy(row)
        effective, ids = handoff._apply_relationship_evidence(row, events)
        self.assertEqual(row, original)
        self.assertEqual(ids, [self.record["id"]])
        self.assertEqual(effective["decision"], "OWNER_HOLD")
        self.assertTrue(effective["dnr"])
        self.assertEqual(effective["due"], self.record["due"])
        self.assertEqual(effective["next_action"], self.record["next_action"])
        self.assertEqual(effective["overlay_event_ids"], original["overlay_event_ids"])
        self.assertEqual(effective["source_paths"], ["synthetic:original", "synthetic:note", handoff.RELATIONSHIP_EVIDENCE_REL])


if __name__ == "__main__":
    unittest.main()
