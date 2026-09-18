#!/usr/bin/env python3
"""Regression coverage for Slack provider-session queue documentation."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import slack_service_tag as sst  # noqa: E402


class SlackServiceTagProviderSigninDocsTest(unittest.TestCase):
    def test_provider_session_docstrings_match_current_queue(self) -> None:
        module_doc = sst.__doc__ or ""
        blocker_doc = sst.format_owner_blocker.__doc__ or ""

        self.assertIn("#provider-sign-in", module_doc)
        self.assertIn("#needs-bryce", module_doc)
        self.assertNotIn("go to #needs-bryce", module_doc)
        self.assertIn("Provider-sign-in", blocker_doc)
        self.assertNotIn("#needs-bryce shape", blocker_doc)

    def test_installed_login_channel_wins_over_legacy_owner_queue(self) -> None:
        catalog = {
            "install": {
                "login_channel": {
                    "id": "C0BUFA9G23E",
                    "name": "#provider-sign-in",
                }
            },
            "owner_signin_channel": {
                "id": "C0BRX6EV739",
                "name": "#needs-bryce",
            },
        }

        signin = sst._signin_channel(catalog)
        self.assertEqual(signin["id"], "C0BUFA9G23E")
        self.assertEqual(signin["name"], "#provider-sign-in")

    def test_legacy_fallback_remains_available_without_install_channel(self) -> None:
        catalog = {
            "owner_signin_channel": {
                "id": "C0BRX6EV739",
                "name": "#needs-bryce",
            }
        }

        signin = sst._signin_channel(catalog)
        self.assertEqual(signin["id"], "C0BRX6EV739")
        self.assertEqual(signin["name"], "#needs-bryce")


if __name__ == "__main__":
    unittest.main()
