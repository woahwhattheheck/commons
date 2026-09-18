#!/usr/bin/env python3
"""Local AutoGTM leftover: same loop as Sheshiyer/explee-skills, sends 0."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from explee_autogtm_local import (
    API_HOST,
    COMPOSED_ENDPOINTS,
    DO_NOT_REMINT,
    DO_NOT_WRITE,
    SOURCE_SKILL,
    empty_page_failure,
    main,
    refuse_send,
    run_pipeline,
    self_test,
)


PACKS_HTML = """
<html>
<head>
  <title>Open Bench Packs</title>
  <meta name="description" content="Public commons leftover board for agent GTM.">
</head>
<body>
  <h1>Ship leftover work</h1>
  <p>Cursor cloud seats, RevOps, and SaaS founders paste a URL and get ICP drafts.</p>
  <h2>Outbound without a card</h2>
  <a href="mailto:desk@example.test">desk</a>
</body>
</html>
"""

FLORAL_HTML = """
<html>
<head><title>Northwindow Silk</title>
<meta name="description" content="Wholesale silk flowers for hotels and event studios.">
</head>
<body>
<h1>Silk by the box</h1>
<p>Wholesale supply for florists, wedding planners, and boutique hotels.</p>
</body>
</html>
"""


class TestExpleeAutogtmLocal(unittest.TestCase):
    def test_self_test_ok(self):
        self.assertEqual(self_test(), "ok")

    def test_cli_self_test(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--self-test"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["self_test"], "ok")
        self.assertEqual(payload["sent"], 0)

    def test_packs_pipeline_drafts_and_icp(self):
        row = run_pipeline(PACKS_HTML, url="https://example.test/packs")
        self.assertEqual(row["state"], "DRAFT")
        self.assertEqual(row["sent"], 0)
        self.assertEqual(row["checkout"], "NOT_MINTED")
        labels = [item["label"] for item in row["icp"]]
        self.assertIn("AI agent operators", labels)
        self.assertIn("RevOps / GTM operators", labels)
        self.assertGreaterEqual(row["counts"]["found"], 2)
        self.assertEqual(row["counts"]["found"], row["counts"]["enriched"])
        self.assertTrue(row["drafts"])
        self.assertTrue(all(draft["send"] == 0 for draft in row["drafts"]))
        self.assertTrue(all(draft["state"] == "owner-review" for draft in row["drafts"]))
        self.assertTrue(row["demo_queue"])
        self.assertTrue(all(item["status"] == "need_owner_review" for item in row["demo_queue"]))
        self.assertTrue(all(item["booked"] is False for item in row["demo_queue"]))
        self.assertEqual(row["source_skill"], SOURCE_SKILL)
        self.assertEqual(row["api_host_not_called"], API_HOST)
        self.assertEqual(row["endpoints_composed_not_called"], list(COMPOSED_ENDPOINTS))
        self.assertIn("cursor-explee-qualify-clone-20260902-01", row["do_not_remint"])
        self.assertIn("cursor-autogtm-explee-same-loop-20260902-01", row["do_not_remint"])
        self.assertIn("qualify.html", row["do_not_write"])
        self.assertIn("autogtm.html", row["do_not_write"])
        self.assertEqual(row["seller"]["seller_email_on_page"], "desk@example.test")
        self.assertTrue(all(c["email_status"] == "UNVERIFIED" for c in row["candidates"]))
        self.assertFalse(any(c.get("email") for c in row["candidates"]))

    def test_floral_icp_is_event_not_agent(self):
        row = run_pipeline(FLORAL_HTML)
        labels = [item["label"] for item in row["icp"]]
        self.assertIn("Event designers", labels)
        self.assertIn("Wholesale buyers", labels)
        self.assertNotIn("AI agent operators", labels)
        self.assertEqual(row["sent"], 0)

    def test_empty_is_finder_failed_not_zero(self):
        row = run_pipeline("   ")
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertIsNone(row["counts"]["found"])
        self.assertNotEqual(row["counts"]["found"], 0)
        self.assertEqual(row["sent"], 0)
        self.assertIn("never silent 0", empty_page_failure()["note"].lower())

    def test_send_apply_go_refused(self):
        for flag in ("send", "apply", "go"):
            row = refuse_send(flag)
            self.assertEqual(row["state"], "REFUSED")
            self.assertEqual(row["sent"], 0)
            self.assertIn(flag, row["flag"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--send"])
        self.assertEqual(rc, 2)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["state"], "REFUSED")
        self.assertEqual(payload["sent"], 0)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--apply"])
        self.assertEqual(rc, 2)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--go"])
        self.assertEqual(rc, 2)

    def test_missing_input_is_finder_failed(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main([])
        self.assertEqual(rc, 1)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["state"], "FINDER-FAILED")
        self.assertEqual(payload["sent"], 0)

    def test_html_file_roundtrip(self):
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".html", delete=False
        ) as handle:
            handle.write(PACKS_HTML)
            path = handle.name
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = main(["--html-file", path])
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["state"], "DRAFT")
            self.assertEqual(payload["sent"], 0)
            blob = payload["seller"]["what_they_sell"] + payload["seller"]["company"]
            self.assertIn("Open Bench Packs", blob)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def test_does_not_name_qualify_path_as_ours(self):
        self.assertIn("qualify.html", DO_NOT_WRITE)
        self.assertIn("autogtm.html", DO_NOT_WRITE)
        self.assertIn("cursor-explee-qualify-clone-20260902-01", DO_NOT_REMINT)
        self.assertIn("cursor-autogtm-explee-same-loop-20260902-01", DO_NOT_REMINT)

    def test_no_explee_testimonial_copy(self):
        row = run_pipeline(PACKS_HTML)
        blob = json.dumps(row)
        self.assertNotIn("I tried Instantly", blob)
        self.assertNotIn("LogSure", blob)
        self.assertNotIn("larksilk", blob.lower())


if __name__ == "__main__":
    unittest.main()
