import tempfile
import unittest
from pathlib import Path
from unittest import mock

import action_executor as ae


class ActionExecutorTests(unittest.TestCase):
    def test_parse_action_record(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.md"
            p.write_text("from: SOL\nto: TOOLS\nid: sol-action-0001\nkind: ACTION\nact: PUSH\ntarget: out.txt\n\n---\n\nPUSH\ntarget: out.txt\n\nhello", encoding="utf-8")
            rec = ae.parse_record(p)
            self.assertEqual(rec["verb"], "PUSH")
            self.assertEqual(rec["target"], "out.txt")
            self.assertEqual(rec["payload"], "hello")

    def test_scope_selection(self):
        self.assertTrue(ae.is_device_target("bryce-pc"))
        self.assertTrue(ae.is_device_target("device:phone"))
        self.assertFalse(ae.is_device_target("repo"))

    def test_push_writes_exact_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rec = {"meta": {"id": "sol-action-0002", "from": "SOL"}, "verb": "PUSH", "target": "out/x.txt", "payload": "payload"}
            with mock.patch.object(ae, "ROOT", root):
                result = ae.execute(rec, "github")
            self.assertEqual((root / "out/x.txt").read_text(), "payload")
            self.assertEqual(result["changed"], ["out/x.txt"])


if __name__ == "__main__":
    unittest.main()
