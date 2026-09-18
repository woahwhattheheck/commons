"""Slack-to-Commons IDs must match the complete existing 8–80 character shape."""
from contextlib import redirect_stdout
import io
import json
import unittest

from host import commons_slack_full_body as mirror


class SlackToCommonsExactIdTests(unittest.TestCase):
    def test_valid_length_boundaries_and_alphabet(self):
        for post_id in ("a" * 8, "z" * 80, "ABC012._-"):
            with self.subTest(post_id=post_id):
                packet = mirror.slack_to_commons(text="body", post_id=post_id)
                self.assertTrue(packet["ok"])
                self.assertEqual(packet["errors"], [])
                self.assertEqual(packet["id"], post_id)
                self.assertIn(f"\nid: {post_id}\nkind: POST\n", packet["post"])

    def test_final_newline_is_not_accepted_or_trimmed(self):
        for length in (8, 79, 80):
            post_id = "a" * length + "\n"
            with self.subTest(length=length):
                packet = mirror.slack_to_commons(text="body\n", post_id=post_id)
                self.assertFalse(packet["ok"])
                self.assertEqual(packet["errors"], ["id-shape"])
                self.assertEqual(packet["id"], post_id)
                self.assertEqual(packet["body"], "body\n")

    def test_existing_malformed_ids_still_report_shape(self):
        for post_id in ("", "a" * 7, "a" * 81, "valid id", "invalid:id", "a\nbbbbbbb", "abcdefgh\r\n", "abcdefgh "):
            with self.subTest(post_id=post_id):
                packet = mirror.slack_to_commons(text="body", post_id=post_id)
                self.assertFalse(packet["ok"])
                self.assertIn("id-shape", packet["errors"])
                self.assertEqual(packet["id"], post_id)

    def test_unicode_and_multiline_body_stay_complete(self):
        for text in ("é🙂\n\n---\nlast", "é🙂\r\n\tlast\n", "body\n\n"):
            with self.subTest(text=text):
                packet = mirror.slack_to_commons(text=text, post_id="valid-id")
                body = text if text.endswith("\n") else text + "\n"
                self.assertTrue(packet["ok"])
                self.assertEqual(packet["body"], body)
                self.assertTrue(packet["post"].endswith("---\n\n" + body))
                self.assertTrue(packet["full_body"])

    def test_empty_body_and_timestamp_diagnostics_are_preserved(self):
        ts = "1788806000.123456"
        packet = mirror.slack_to_commons(text=" \n", post_id=ts, ts=ts)
        self.assertFalse(packet["ok"])
        self.assertEqual(packet["errors"], ["empty-slack-body", "slack-ts-as-commons-id"])
        self.assertEqual(packet["ts"], ts)
        self.assertEqual(packet["id"], ts)

    def test_metadata_and_default_speaker_are_unchanged(self):
        packet = mirror.slack_to_commons(text="body", post_id="valid-id", channel="channel-context", ts="123.456")
        self.assertTrue(packet["ok"])
        self.assertEqual(packet["channel"], "channel-context")
        self.assertEqual(packet["ts"], "123.456")
        self.assertIn("\nfrom: UNSEATED\n", packet["post"])
        self.assertFalse(packet["new_token"])
        self.assertFalse(packet["slack_ts_is_commons_id"])

    def test_cli_reports_malformed_id_with_existing_exit_code(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = mirror.main(["--slack-to-commons", "body", "--id", "valid-id\n", "--json"])
        packet = json.loads(stream.getvalue())
        self.assertEqual(code, 1)
        self.assertFalse(packet["ok"])
        self.assertEqual(packet["errors"], ["id-shape"])
        self.assertEqual(packet["id"], "valid-id\n")
        self.assertEqual(packet["body"], "body\n")

    def test_cli_keeps_valid_payload_and_success_exit_code(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = mirror.main(["--slack-to-commons", "é🙂\nbody", "--id", "valid-id", "--json"])
        packet = json.loads(stream.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(packet["ok"])
        self.assertEqual(packet["errors"], [])
        self.assertEqual(packet["body"], "é🙂\nbody\n")


if __name__ == "__main__":
    unittest.main()
