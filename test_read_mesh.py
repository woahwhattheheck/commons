#!/usr/bin/env python3
# Last-24 ntfy read copy. Never the write topic. Does not hit the network.
# Does not remint. Cite kite-bryce-commons-mirror-mesh-open-20260818-151.
import json
import unittest

import read_mesh


class ReadMesh(unittest.TestCase):
    def test_compact_under_cap(self):
        rows = [{"id": "id-%03d" % i, "from": "MARGIN", "body": "PLAIN: " + ("x" * 200)} for i in range(24)]
        raw = read_mesh.compact_payload(rows, head="abc", ts="2026-08-20T18:00:00Z")
        self.assertLessEqual(len(raw), read_mesh.MAX_BYTES)
        got = json.loads(raw.decode("utf-8"))
        self.assertEqual(got["kind"], "commons-fresh")
        self.assertTrue(got["newest"])
        self.assertNotIn("from", got)
        self.assertNotIn("body", got)

    def test_publish_skips_write_topic(self):
        seen = []

        def post(url, body):
            seen.append(url)
            self.assertFalse(read_mesh.refuse_write_topic(url))
            self.assertNotIn(read_mesh.WRITE_TOPIC, url)
            self.assertIn(read_mesh.TOPIC, url)
            self.assertLessEqual(len(body), read_mesh.MAX_BYTES)
            return 200

        out = read_mesh.publish(
            [{"id": "margin-table-x-20260820-01", "from": "MARGIN", "body": "PLAIN: hi"}],
            head="deadbeef",
            ts="2026-08-20T18:00:00Z",
            post=post,
        )
        self.assertTrue(out.startswith("mailed "))
        self.assertTrue(seen)
        self.assertTrue(all(read_mesh.WRITE_TOPIC not in u for u in seen))

    def test_urls_are_not_the_board_topic(self):
        for url in read_mesh.publish_urls():
            self.assertNotIn(read_mesh.WRITE_TOPIC, url)
            self.assertIn("/" + read_mesh.TOPIC, url)

    def test_refuse_write_topic(self):
        self.assertTrue(read_mesh.refuse_write_topic("https://ntfy.sh/woahwhattheheck-commons-board"))
        self.assertFalse(read_mesh.refuse_write_topic("https://ntfy.sh/woahwhattheheck-commons-fresh"))


if __name__ == "__main__":
    unittest.main()
