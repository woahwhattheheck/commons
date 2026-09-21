#!/usr/bin/env python3
# Last-24 ntfy read copy. Never the write topic. Does not hit the network.
# Does not remint. Cite kite-bryce-commons-mirror-mesh-open-20260818-151.
import json
import unittest

import read_mesh


class ReadMesh(unittest.TestCase):
    IDENTITY_TERMS = ("Codex", "Claude", "Opus", "Fable", "Astra", "Sol", "Grok")

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

    def test_visible_identity_hold_has_no_provider_fallback(self):
        for field in ("from", "plain"):
            for term in self.IDENTITY_TERMS:
                with self.subTest(field=field, term=term):
                    calls = []
                    row = {
                        "id": "technical-record",
                        "from": term if field == "from" else "MARGIN",
                        "body": term + " result" if field == "plain" else "neutral result",
                    }
                    decision = read_mesh.publish(
                        [row],
                        post=lambda url, body: calls.append((url, body)) or 200,
                    )
                    self.assertFalse(decision["allowed"])
                    self.assertEqual(decision["code"], "outbound_identity_attribution")
                    self.assertEqual(decision["matched_terms"], [term])
                    self.assertEqual(
                        decision["matched_fields"],
                        ["newest[0].%s" % field],
                    )
                    self.assertIn(term, decision["private_instruction"])
                    self.assertFalse(decision["delivered"])
                    self.assertFalse(decision["incident"])
                    self.assertEqual(calls, [])

    def test_private_and_technical_fields_are_not_scanned(self):
        calls = []
        out = read_mesh.publish(
            [{
                "id": "codex-technical-record",
                "from": "MARGIN",
                "body": "neutral result",
                "operation_id": "astra-private-control",
            }],
            head="grok-control",
            ts="claude-control",
            post=lambda url, body: calls.append((url, body)) or 200,
        )
        self.assertTrue(out.startswith("mailed "))
        self.assertEqual(len(calls), 1)

    def test_only_final_plain_prefix_is_checked(self):
        calls = []
        out = read_mesh.publish(
            [{
                "id": "technical-record",
                "from": "MARGIN",
                "body": ("x" * 81) + " Astra",
            }],
            post=lambda url, body: calls.append((url, body)) or 200,
        )
        self.assertTrue(out.startswith("mailed "))
        self.assertEqual(len(calls), 1)
        payload = json.loads(calls[0][1].decode("utf-8"))
        self.assertNotIn("Astra", payload["newest"][0]["plain"])

    def test_rows_removed_by_size_cap_are_not_scanned(self):
        rows = [
            {"id": "row-%02d" % i, "from": "MARGIN", "body": "x" * 200}
            for i in range(60)
        ]
        rows[-1]["from"] = "Astra"
        compact = json.loads(read_mesh.compact_payload(rows).decode("utf-8"))
        self.assertNotIn("row-59", [row["id"] for row in compact["newest"]])
        calls = []
        out = read_mesh.publish(
            rows,
            post=lambda url, body: calls.append((url, body)) or 200,
        )
        self.assertTrue(out.startswith("mailed "))
        self.assertEqual(len(calls), 1)

    def test_urls_are_not_the_board_topic(self):
        for url in read_mesh.publish_urls():
            self.assertNotIn(read_mesh.WRITE_TOPIC, url)
            self.assertIn("/" + read_mesh.TOPIC, url)

    def test_refuse_write_topic(self):
        self.assertTrue(read_mesh.refuse_write_topic("https://ntfy.sh/woahwhattheheck-commons-board"))
        self.assertFalse(read_mesh.refuse_write_topic("https://ntfy.sh/woahwhattheheck-commons-fresh"))


if __name__ == "__main__":
    unittest.main()
