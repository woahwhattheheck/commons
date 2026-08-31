#!/usr/bin/env python3
"""Hostile regressions for the customer-facing link boundary."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from host import customer_link_boundary as boundary


class CustomerLinkBoundaryTests(unittest.TestCase):
    def test_forbidden_customer_links_fail_closed_across_formats(self):
        cases = {
            "https://github.com/woahwhattheheck/commons": "GITHUB_HOST",
            "HTTPS://GIST.GITHUB.COM./demo": "GITHUB_HOST",
            "raw.githubusercontent.com/owner/repo/main/file": "GITHUB_HOST",
            "https://woahwhattheheck.github.io/commons/demo": "GITHUB_PAGES_HOST",
            "www.github.com/owner/repo": "GITHUB_HOST",
            "github.com/owner/repo": "GITHUB_HOST",
            "//api.github.com/repos/owner/repo": "GITHUB_HOST",
            "<https://github.com/owner/repo|internal proof>": "GITHUB_HOST",
            "[proof](https://github.com/owner/repo)": "GITHUB_HOST",
            "https://TOKENJUNKIELABS.slack.com/archives/C123/p1": "COMMONS_SLACK_HOST",
            "http://commons.mno/p/internal": "COMMONS_HOST",
            "https://assets.githubassets.com/icon.svg": "GITHUB_HOST",
        }
        for text, reason in cases.items():
            with self.subTest(text=text):
                report = boundary.customer_link_report(text)
                self.assertFalse(report["safe"])
                self.assertEqual(report["state"], "BLOCKED_CUSTOMER_LINK")
                self.assertEqual(report["violation_count"], 1)
                self.assertEqual(report["violations"][0]["reason"], reason)

    def test_branded_and_direct_transaction_links_are_allowed(self):
        text = (
            "See https://demo.example.com/repair. "
            "Approve at https://buy.stripe.com/test_receipt. "
            "GitHub is an internal evidence system, not this CTA. "
            "Questions: person@github.com."
        )
        report = boundary.require_customer_link_safe(text)
        self.assertTrue(report["safe"])
        self.assertEqual(report["state"], "CUSTOMER_LINK_SAFE")
        self.assertEqual(report["violations"], [])

    def test_multiple_findings_preserve_exact_order_and_offsets(self):
        text = "first github.com/a then <https://x.github.io/demo|second>"
        report = boundary.customer_link_report(text)
        self.assertEqual(report["violation_count"], 2)
        self.assertEqual(
            [item["raw"] for item in report["violations"]],
            ["github.com/a", "https://x.github.io/demo"],
        )
        for item in report["violations"]:
            self.assertEqual(text[item["start"]:item["end"]], item["raw"])

    def test_backslash_and_trailing_dot_cannot_hide_github_host(self):
        text = "https://GitHub.Com.\\owner\\repo."
        report = boundary.customer_link_report(text)
        self.assertFalse(report["safe"])
        item = report["violations"][0]
        self.assertEqual(item["host"], "github.com")
        self.assertEqual(item["normalized_url"], "https://GitHub.Com./owner/repo")

    def test_exception_contains_machine_readable_report(self):
        with self.assertRaises(boundary.CustomerLinkBoundaryError) as caught:
            boundary.require_customer_link_safe("send https://github.com/acme/demo")
        report = json.loads(str(caught.exception))
        self.assertEqual(report["schema"], boundary.SCHEMA)
        self.assertFalse(report["safe"])
        self.assertEqual(report["violation_count"], 1)

    def test_non_text_input_fails_closed(self):
        for value in (None, b"https://github.com/x", 0, {}, []):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    boundary.scan_customer_text(value)

    def test_cli_exit_and_json_contract(self):
        script = ROOT / "host" / "customer_link_boundary.py"
        with tempfile.TemporaryDirectory() as tmp:
            safe_path = Path(tmp) / "safe.txt"
            blocked_path = Path(tmp) / "blocked.txt"
            safe_path.write_text("https://demo.example.com and https://buy.stripe.com/x", encoding="utf-8")
            blocked_path.write_text("https://github.com/owner/repo", encoding="utf-8")

            safe = subprocess.run(
                [sys.executable, str(script), str(safe_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            blocked = subprocess.run(
                [sys.executable, str(script), str(blocked_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(safe.returncode, 0)
            self.assertTrue(json.loads(safe.stdout)["safe"])
            self.assertEqual(blocked.returncode, 1)
            self.assertFalse(json.loads(blocked.stdout)["safe"])


if __name__ == "__main__":
    unittest.main()
