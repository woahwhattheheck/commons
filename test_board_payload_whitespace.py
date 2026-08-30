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

    def test_slack_payload_keeps_ordinary_local_path_exact(self):
        source = (
            "Local live-proof APK: "
            r"C:\Users\lucys\Documents\Codex\proof\app-debug.apk"
        )

        landed, extra, slack_chat = bi._prepare_body_and_struct(
            source,
            {
                "carrier": "slack-connector",
                "kind": "slack_message",
            },
        )

        self.assertTrue(slack_chat)
        self.assertEqual(landed, source)
        self.assertNotIn("local path redacted", landed)
        self.assertNotIn("target", extra)

    def test_slack_body_target_sentence_is_not_promoted(self):
        source = (
            "START — Resource Master claims three paths.\n"
            "• ground/RESOURCE_LEDGER.json\n"
            "Target: existing revenue-offer-stack only"
        )

        landed, extra, slack_chat = bi._prepare_body_and_struct(
            source,
            {
                "carrier": "slack-connector",
                "kind": "slack_message",
            },
        )

        self.assertTrue(slack_chat)
        self.assertEqual(landed, source)
        self.assertNotIn("target", extra)

    def test_slack_reply_keeps_explicit_envelope_target(self):
        source = "Target: this is ordinary source prose"
        target = "slack-1788103429-674559"

        landed, extra, slack_chat = bi._prepare_body_and_struct(
            source,
            {
                "carrier": "slack-connector",
                "kind": "slack_thread_reply",
                "target": target,
            },
        )

        self.assertTrue(slack_chat)
        self.assertEqual(landed, source)
        self.assertEqual(extra["target"], target)


if __name__ == "__main__":
    unittest.main()
