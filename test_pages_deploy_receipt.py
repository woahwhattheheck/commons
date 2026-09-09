#!/usr/bin/env python3
"""In-tree pages-deploy.json survives github-pages[bot] overwrite."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from host import pages_deploy_receipt as receipt
from host import pages_github_io_required as required


ROOT = Path(__file__).resolve().parent


class PagesDeployReceiptTests(unittest.TestCase):
    def test_receipt_is_in_git_and_valid(self) -> None:
        path = ROOT / "pages-deploy.json"
        self.assertTrue(path.is_file())
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(receipt.receipt_errors(payload), ())
        self.assertTrue(receipt.in_tree(ROOT))
        report = receipt.report(ROOT)
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["in_tree"])
        self.assertTrue(report["open_door"])
        self.assertTrue(report["copy_filter_is_not_admission"])
        self.assertTrue(report["workflow_untouched"])
        self.assertTrue(report["pages_source_unflipped"])
        self.assertIs(report["owns_deploy_workflow"], False)
        self.assertIs(report["gate"], False)
        self.assertEqual(report["cite"], "cursor-pages-deploy-json-overwrite-20260902-01")
        self.assertEqual(payload["run_id"], "33586981030")
        self.assertEqual(payload["sha"], "c994a5718a137d8b46b039503d935f42f7202d93")
        self.assertIn("chunks/", payload["keeps"])
        self.assertIn("action.html", payload["keeps"])

    def test_missing_or_gated_receipt_is_flagged(self) -> None:
        self.assertIn("missing:sha", receipt.receipt_errors({"run_id": "1"}))
        bad = {
            "sha": "not-a-sha",
            "run_id": "1",
            "excludes": [],
            "keeps": ["chunks/", "action.html", "pay.html"],
            "source": "artifact-only",
            "survives_github_pages_bot_overwrite": False,
            "owns_deploy_workflow": True,
            "gate": True,
        }
        errors = receipt.receipt_errors(bad)
        self.assertIn("sha_not_40_hex", errors)
        self.assertIn("source_not_in_tree_canary", errors)
        self.assertIn("missing_overwrite_survive", errors)
        self.assertIn("steals_deploy_workflow", errors)
        self.assertIn("gate_true", errors)

    def test_does_not_steal_fable_workflow_or_required_doors(self) -> None:
        self.assertNotIn(receipt.RECEIPT.name, required.required_files(ROOT))
        self.assertTrue(required.live_workflow_writes_pages_deploy_receipt(ROOT))
        text = (ROOT / "host" / "pages_deploy_receipt.py").read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("possessing the link stays authorization", lowered)
        self.assertIn("does not write", lowered)
        self.assertNotIn("authentication required", lowered)
        self.assertNotIn("permission denied", lowered)
        self.assertNotIn("allowed_verbs", lowered)
        workflow = (ROOT / ".github" / "workflows" / "pages-deploy.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("_site/pages-deploy.json", workflow)

    def test_cli_json_is_clean(self) -> None:
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = receipt.main(["--root", str(ROOT), "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["errors"], [])
        self.assertTrue(payload["in_tree"])


if __name__ == "__main__":
    unittest.main()
