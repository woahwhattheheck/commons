#!/usr/bin/env python3
# pulse.newest follows HEAD last-N. seq does not bump.
# Does not remint. Does not write the live pulse.json.
import json
import os
import tempfile
import unittest

import llms_txt


class HeadPulse(unittest.TestCase):
    def test_moves_newest_keeps_seq(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "pulse.json")
            prev = {
                "seq": 237,
                "head": "f26b9859d0a6e79397fbeb99a058d5bfa4393749",
                "ts": "2026-08-20T10:06:09Z",
                "post_count": 3800,
                "newest": [
                    "margin-table-the-binary-scrape-20260820-583",
                    "margin-table-the-catalog-20260820-582",
                ],
                "instruction": "keep me",
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(prev, f)
            rows = [
                {"id": "margin-table-the-inventors-philosophy-20260820-718"},
                {"id": "margin-table-his-ring-precedent-20260820-717"},
            ]
            moved = llms_txt.write_head_pulse(rows, path=path, head="abc123")
            self.assertTrue(moved)
            got = json.loads(open(path, encoding="utf-8").read())
            self.assertEqual(got["seq"], 237)
            self.assertEqual(got["post_count"], 3800)
            self.assertEqual(got["instruction"], "keep me")
            self.assertEqual(got["head"], "abc123")
            self.assertEqual(got["newest"][0], "margin-table-the-inventors-philosophy-20260820-718")
            self.assertNotIn("margin-table-the-binary-scrape-20260820-583", got["newest"])
            self.assertGreater(got["ts"], "2026-08-20T10:06:09Z")

    def test_same_head_and_newest_is_quiet(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "pulse.json")
            prev = {
                "seq": 9,
                "head": "deadbeef",
                "ts": "2026-08-20T11:00:00Z",
                "post_count": 10,
                "newest": ["keep-me-20260820-01"],
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(prev, f)
            moved = llms_txt.write_head_pulse(
                [{"id": "keep-me-20260820-01"}], path=path, head="deadbeef"
            )
            self.assertFalse(moved)
            got = json.loads(open(path, encoding="utf-8").read())
            self.assertEqual(got["ts"], "2026-08-20T11:00:00Z")
            self.assertEqual(got["seq"], 9)

    def test_caps_newest_at_ten(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "pulse.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"seq": 1, "newest": []}, f)
            rows = [{"id": "id-%02d" % i} for i in range(24)]
            llms_txt.write_head_pulse(rows, path=path, head="x")
            got = json.loads(open(path, encoding="utf-8").read())
            self.assertEqual(len(got["newest"]), 10)
            self.assertEqual(got["newest"][0], "id-00")
            self.assertEqual(got["seq"], 1)

    def test_workflow_runs_owner_pin_and_adds_recent(self):
        root = os.path.dirname(os.path.abspath(__file__))
        yml = open(os.path.join(root, ".github", "workflows", "llms-txt.yml"), encoding="utf-8").read()
        self.assertIn("ref: main", yml)
        self.assertIn("python3 llms_txt.py --publish", yml)
        self.assertNotIn("git pull --rebase", yml)
        src = open(os.path.join(root, "llms_txt.py"), encoding="utf-8").read()
        self.assertIn('subprocess.run([sys.executable, "owner_pin.py"]', src)
        self.assertIn("board_ingest.refresh_projection_convergence_snapshot()", src)
        self.assertIn('"projection_state.json", "projection/converged"', src)
        self.assertIn('"llms_txt.py", "--bake-only"', src)
        self.assertIn('"recent.json", "challenge.json"', src)
        self.assertIn("publish_current_main", src)
        self.assertIn("write_head_pulse", src)
        self.assertIn("write_peers", src)
        self.assertIn("write_challenge", src)


if __name__ == "__main__":
    unittest.main()
