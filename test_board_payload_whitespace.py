#!/usr/bin/env python3
"""Regression coverage for lossless board payload boundaries."""

import unittest

import board_ingest as bi


class BoardPayloadWhitespaceTests(unittest.TestCase):
    def test_attachment_only_payload_keeps_leading_lf(self):
        source = "\nFiles: screenshot.jpg (ID: F123, image/jpeg, 10 KB)"
        issue = (
            "from: BERNAYS\n"
            "to: TABLE\n"
            "id: slack-1787890378-158149\n"
            "carrier: slack-connector\n"
            "---\n"
            + source
        )

        src, dest, ident, landed, extra = bi._issue_post_fields(
            {"title": "slack-1787890378-158149", "body": issue}
        )

        self.assertEqual(
            (src, dest, ident),
            ("BERNAYS", "TABLE", "slack-1787890378-158149"),
        )
        self.assertEqual(extra["carrier"], "slack-connector")
        self.assertEqual(landed, source)

    def test_only_terminal_newlines_are_normalized(self):
        source = "\nopaque payload\n\n"
        issue = "id: payload-whitespace-0001\n---\n" + source

        self.assertEqual(
            bi._body_text(issue, preserve_leading=True), "\nopaque payload"
        )


if __name__ == "__main__":
    unittest.main()
