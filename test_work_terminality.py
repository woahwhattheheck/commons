#!/usr/bin/env python3
import pathlib
import unittest

import work_terminality as wt

ROOT = pathlib.Path(__file__).resolve().parent
OP = "INBOUND-PAID-SCOPE-OWNER-CLOSE-DESK-20260916-ZSOL"
DUP = "Build-genuine-human-inbound---owner-close-desk"
EVIDENCE = "ccab91f74dfec13e1dcb8228b422e044fbc19e08"
OPEN = "OPEN-UNSEATED-CONTROL-20260917"


class WorkTerminalityTests(unittest.TestCase):
    def setUp(self):
        self.registry = wt.load_registry(str(ROOT))

    def active(self):
        return wt.active_terminal_index(
            root=str(ROOT),
            registry=self.registry,
            head="HEAD",
            is_ancestor=lambda evidence, head: evidence == EVIDENCE and head == "HEAD",
        )

    def test_exact_15130_and_15616_predecessors_are_terminal(self):
        index = self.active()
        canonical = {
            "id": OP,
            "from": "UNSEATED",
            "body": "historical canonical source stays durable",
        }
        duplicate = {
            "id": DUP,
            "from": "UNSEATED",
            "body": "Operation: `%s`\nDuplicate carrier" % OP,
        }
        self.assertTrue(wt.is_actionable_terminal(canonical, index))
        self.assertTrue(wt.is_actionable_terminal(duplicate, index))

    def test_open_unseated_control_remains_actionable(self):
        rows = [
            {"id": OP, "from": "UNSEATED", "body": ""},
            {"id": DUP, "from": "UNSEATED", "body": "Operation: `%s`" % OP},
            {"id": OPEN, "from": "UNSEATED", "body": "Operation: `%s`" % OPEN},
        ]
        kept = wt.filter_actionable_rows(
            rows,
            root=str(ROOT),
            registry=self.registry,
            is_ancestor=lambda evidence, head: evidence == EVIDENCE,
        )
        self.assertEqual([row["id"] for row in kept], [OPEN])

    def test_history_from_non_unseated_sender_is_not_suppressed(self):
        row = {"id": OP, "from": "GROK", "body": ""}
        self.assertFalse(wt.is_actionable_terminal(row, self.active()))

    def test_missing_or_non_ancestor_evidence_fails_visible(self):
        rows = [{"id": OP, "from": "UNSEATED", "body": ""}]
        kept = wt.filter_actionable_rows(
            rows,
            root=str(ROOT),
            registry=self.registry,
            is_ancestor=lambda evidence, head: False,
        )
        self.assertEqual(kept, rows)

    def test_operation_identity_is_exact_structured_field(self):
        self.assertEqual(
            wt.explicit_operation_id({"body": "Operation: `%s`\nrest" % OP}),
            OP,
        )
        self.assertEqual(
            wt.explicit_operation_id({"body": "please finish %s soon" % OP}),
            "",
        )

    def test_registry_rejects_duplicate_keys_and_nonfinite_values(self):
        with self.assertRaises(ValueError):
            wt.loads_strict('{"schema":"a","schema":"b","entries":[]}')
        with self.assertRaises(ValueError):
            wt.loads_strict('{"schema":"a","entries":[NaN]}')

    def test_registry_binds_exact_issue_and_main_receipt(self):
        entry = self.registry["entries"][0]
        self.assertEqual(entry["operation_id"], OP)
        self.assertEqual(entry["canonical_issue"], 15130)
        self.assertEqual(entry["duplicate_issues"], [15616])
        self.assertEqual(entry["evidence_commit"], EVIDENCE)
        self.assertEqual(entry["card_ids"], [OP, DUP])

    def test_real_repository_head_contains_landed_evidence(self):
        index = wt.active_terminal_index(root=str(ROOT), registry=self.registry, head="HEAD")
        self.assertIn(OP, index["operation_ids"])
        self.assertIn(DUP, index["card_ids"])

    def test_producer_and_home_renderer_are_wired_to_registry(self):
        llms = (ROOT / "llms_txt.py").read_text(encoding="utf-8")
        head = (ROOT / "head.js").read_text(encoding="utf-8")
        self.assertIn("import work_terminality", llms)
        self.assertIn("work_terminality.is_actionable_terminal", llms)
        self.assertIn("bindActionableTerminality", head)
        self.assertIn("parseTerminalRegistry", head)
        self.assertIn("work_terminality.json", head)
        self.assertIn("MutationObserver", head)
        self.assertIn("owner-pin", head)


if __name__ == "__main__":
    unittest.main()
