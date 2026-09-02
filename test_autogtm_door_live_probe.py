#!/usr/bin/env python3
"""Door leftover: autogtm.html live-probes Explee from the browser."""

from __future__ import annotations

import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOOR = (ROOT / "autogtm.html").read_text(encoding="utf-8")
EXPLEE_PROJECTS = "https://api.explee.com/public/api/v1/autogtm/projects"


class TestAutogtmDoorLiveProbe(unittest.TestCase):
    def test_door_fetches_explee_projects_with_credentials_omit(self) -> None:
        self.assertIn(EXPLEE_PROJECTS, DOOR)
        self.assertIn('credentials: "omit"', DOOR)
        self.assertIn("mode: \"cors\"", DOOR)
        self.assertIn("id=\"explee-live\"", DOOR)
        self.assertIn("id=\"live-http\"", DOOR)
        self.assertIn("probeExplee", DOOR)
        self.assertIn("Never silent 0", DOOR)

    def test_door_has_no_login_or_api_key_input(self) -> None:
        self.assertNotIn('type="password"', DOOR)
        self.assertNotIn("type='password'", DOOR)
        self.assertNotIn('id="api', DOOR)
        self.assertNotIn("name=\"api", DOOR)
        self.assertNotIn("<form", DOOR.lower())
        self.assertIn("No login", DOOR)

    def test_door_links_sibling_gtm_index_outbound(self) -> None:
        self.assertIn('href="./lm-gtm-index.html"', DOOR)
        self.assertIn('href="./website-people-email-book.html"', DOOR)
        self.assertIn("python3 host/autogtm_same_loop.py --json --url", DOOR)

    def test_does_not_remint_lead_or_harborline_leftovers(self) -> None:
        self.assertTrue(
            (ROOT / "p/cursor-explee-skills-adopt-20260902-01.md").exists()
        )
        self.assertTrue(
            (ROOT / "p/cursor-explee-qualify-clone-20260902-01.md").exists()
        )
        self.assertNotIn("qualify.html", DOOR)
        self.assertNotIn(".cursor/skills/explee-autogtm", DOOR)

    def test_live_explee_projects_is_finder_failed_not_zero(self) -> None:
        req = urllib.request.Request(
            EXPLEE_PROJECTS,
            headers={"User-Agent": "commons-autogtm-door-live-probe", "Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                code = resp.status
                body = resp.read()
        except urllib.error.HTTPError as err:
            code = err.code
            body = err.read()
        except OSError as err:
            self.assertTrue(str(err), msg="network miss must carry search space")
            return
        self.assertEqual(code, 401)
        self.assertIn(b"Missing API key", body)
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
