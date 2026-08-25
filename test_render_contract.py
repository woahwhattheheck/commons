#!/usr/bin/env python3
"""Workflow contract leftover: YAML is not a passing Chromium run."""

from __future__ import annotations

import os
import sys
import threading
import unittest
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
sys.path.insert(0, ROOT)

from render_check import serve
from render_contract import (
    COMMAND,
    FAILED_MAIN_RUN,
    PAGES,
    TOOL,
    WORKFLOW,
    classify,
    folded_body,
    last_main_run,
    load_catalog,
    measure_root,
    parse_tool,
    parse_workflow,
)


class TestRenderContract(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_missing_command_stays_not_landed(self):
        measured = parse_workflow("python3 render_check.py board.html\n")
        verdict = classify({"measured": True, **measured, **parse_tool(""), "runs": []})
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("8bit.html", verdict["note"])

    def test_failed_run_without_threading_is_not_landed(self):
        verdict = classify(
            {
                "measured": True,
                **parse_workflow(COMMAND + "\nplaywright\nupload-artifact\n"),
                **parse_tool("class Server(socketserver.TCPServer):\n    pass\n"),
                "runs": [
                    {
                        "id": FAILED_MAIN_RUN,
                        "conclusion": "failure",
                        "head_branch": "main",
                        "event": "push",
                    }
                ],
            }
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn(str(FAILED_MAIN_RUN), verdict["note"])
        self.assertIn("passing run", verdict["note"])

    def test_failed_run_with_threading_is_candidate(self):
        verdict = classify(
            {
                "measured": True,
                **parse_workflow(COMMAND + "\nplaywright\nupload-artifact\n"),
                **parse_tool("ThreadingMixIn\nBrokenPipeError\n"),
                "runs": [
                    {
                        "id": FAILED_MAIN_RUN,
                        "conclusion": "failure",
                        "head_branch": "main",
                        "event": "push",
                    }
                ],
            }
        )
        self.assertEqual(verdict["state"], "CANDIDATE")
        self.assertIn("ThreadingMixIn", verdict["note"])

    def test_successful_main_run_is_integrated(self):
        verdict = classify(
            {
                "measured": True,
                **parse_workflow(COMMAND + "\nplaywright\nupload-artifact\n"),
                **parse_tool("ThreadingMixIn\nBrokenPipeError\n"),
                "runs": [
                    {
                        "id": 99,
                        "conclusion": "success",
                        "head_branch": "main",
                        "event": "push",
                    }
                ],
            }
        )
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("99", verdict["note"])

    def test_live_tree_measures_the_failed_main_run(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["workflow_present"])
        self.assertTrue(row["tool_present"])
        self.assertTrue(row["catalog_present"])
        self.assertTrue(row["has_exact_command"])
        self.assertEqual(row["page_count"], len(PAGES))
        self.assertTrue(row["has_threading"])
        self.assertTrue(row["swallows_broken_pipe"])
        last = last_main_run(row["runs"])
        self.assertIsNotNone(last)
        self.assertEqual(last["id"], FAILED_MAIN_RUN)
        self.assertEqual(last["conclusion"], "failure")
        verdict = classify(row)
        self.assertEqual(verdict["state"], "CANDIDATE")
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertIn("rivet-ship-render-check-20260825-01", row["hands_off"])

    def test_catalog_names_the_three_failed_runs(self):
        catalog_path = os.path.join(ROOT, "ground", "RENDER_CONTRACT.json")
        with open(catalog_path, "r", encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        ids = [row["id"] for row in catalog["runs"]]
        self.assertEqual(ids, [32812516738, 32812503966, 32812350086])
        self.assertEqual(catalog["slack_ts"], "1787637223.298509")

    def test_live_workflow_keeps_the_exact_command(self):
        with open(os.path.join(ROOT, WORKFLOW), "r", encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(COMMAND, folded_body(text))
        with open(os.path.join(ROOT, TOOL), "r", encoding="utf-8") as handle:
            tool = handle.read()
        self.assertIn("ThreadingMixIn", tool)
        self.assertIn("BrokenPipeError", tool)
        self.assertIn("daemon_threads", tool)

    def test_threaded_server_serves_visual_html_concurrently(self):
        httpd, port = serve(ROOT, 18973)
        errors = []

        def hit():
            url = "http://127.0.0.1:%d/visual.html" % port
            try:
                with urllib.request.urlopen(url, timeout=8) as response:
                    body = response.read()
                if b"<title>VISUAL" not in body:
                    errors.append("missing VISUAL title")
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=hit) for _ in range(16)]
        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=12)
        finally:
            httpd.shutdown()
            httpd.server_close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
