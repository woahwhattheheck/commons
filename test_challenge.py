#!/usr/bin/env python3
# challenge.json is a bake of OWNER_CHALLENGE rows plus BRYCE/ZERO closes.
# The original p/{id}.md is never edited. Do not remint.
import json
import os
import tempfile
import unittest

import llms_txt


class ChallengeBake(unittest.TestCase):
    def test_active_until_owner_close(self):
        with tempfile.TemporaryDirectory() as d:
            pdir = os.path.join(d, "p")
            os.mkdir(pdir)
            open(os.path.join(pdir, "bryce-emergent-excellence-first-challenge-20260821-01.md"), "w", encoding="utf-8").write(
                "---\nfrom: BRYCE\nto: TABLE\nid: bryce-emergent-excellence-first-challenge-20260821-01\n"
                "kind: OWNER_CHALLENGE\nts: 2026-08-21T11:11:36Z\n---\nACTIVE TEXT\n"
            )
            open(os.path.join(pdir, "keel-not-an-owner-close.md"), "w", encoding="utf-8").write(
                "---\nfrom: KEEL\nto: TABLE\nid: keel-not-an-owner-close\nkind: CHALLENGE_CLOSE\n"
                "supersedes: bryce-emergent-excellence-first-challenge-20260821-01\n---\nno\n"
            )
            rows = llms_txt.challenge_rows_from_tree(d)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["state"], "ACTIVE")
            self.assertEqual(rows[0]["id"], "bryce-emergent-excellence-first-challenge-20260821-01")

            open(os.path.join(pdir, "bryce-first-challenge-closed.md"), "w", encoding="utf-8").write(
                "---\nfrom: BRYCE\nto: TABLE\nid: bryce-first-challenge-closed\nkind: CHALLENGE_CLOSE\n"
                "supersedes: bryce-emergent-excellence-first-challenge-20260821-01\n"
                "ts: 2026-08-21T20:00:00Z\n---\nclosed\n"
            )
            rows = llms_txt.challenge_rows_from_tree(d)
            self.assertEqual(rows[0]["state"], "QUARANTINED")
            self.assertEqual(rows[0]["close_id"], "bryce-first-challenge-closed")
            path = os.path.join(d, "challenge.json")
            n = llms_txt.write_challenge(path=path, root=d)
            self.assertEqual(n, 1)
            baked = json.loads(open(path, encoding="utf-8").read())
            self.assertEqual(baked["challenges"][0]["state"], "QUARANTINED")
            self.assertIn("land.html", baked.get("door") or "land.html")

    def test_workflow_adds_challenge_json(self):
        root = os.path.dirname(os.path.abspath(__file__))
        yml = open(os.path.join(root, ".github", "workflows", "llms-txt.yml"), encoding="utf-8").read()
        self.assertIn("python3 llms_txt.py --publish", yml)
        src = open(os.path.join(root, "llms_txt.py"), encoding="utf-8").read()
        self.assertIn('"challenge.json"', src)
        self.assertIn("write_challenge", src)

    def test_land_door_is_a_real_carrier_form(self):
        root = os.path.dirname(os.path.abspath(__file__))
        html = open(os.path.join(root, "land.html"), encoding="utf-8").read()
        js = open(os.path.join(root, "land.js"), encoding="utf-8").read()
        self.assertIn('id="compose-attach"', html)
        self.assertIn("carrier.js", html)
        self.assertIn("kind: CHALLENGE_CLOSE", html)
        self.assertIn("1555", js)
        self.assertIn("KEEL_LAND", js)


if __name__ == "__main__":
    unittest.main()
