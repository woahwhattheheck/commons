"""Malformed links cannot prevent readable work-item delivery."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from host import inbox_slack_relay as relay


class URLRenderingTests(unittest.TestCase):
    def test_unclosed_ip_literal(self):
        self.assertEqual(relay.clean("Review https://[broken/path today"),
                         "Review [malformed URL omitted] today")

    def test_nfkc_authority_delimiters(self):
        for delimiter in ("\uff0f", "\uff1a", "\uff20", "\uff1f", "\uff03"):
            with self.subTest(delimiter=delimiter):
                self.assertEqual(relay.clean("Review https://example.test" + delimiter + "private now"),
                                 "Review [malformed URL omitted] now")

    def test_malformed_at_end(self):
        self.assertEqual(relay.clean("Please review https://[broken"),
                         "Please review [malformed URL omitted]")

    def test_multiple_bad_links_preserve_good_link(self):
        text = "https://[bad one http://example.test/review two https://[other"
        self.assertEqual(relay.clean(text),
                         "[malformed URL omitted] one http://example.test/review two [malformed URL omitted]")

    def test_unicode_work_text_preserved(self):
        self.assertEqual(relay.clean("R\u00e9vision \u65e5\u672c\u8a9e https://[bad termin\u00e9e"),
                         "R\u00e9vision \u65e5\u672c\u8a9e [malformed URL omitted] termin\u00e9e")

    def test_valid_links_unchanged(self):
        for text in ("https://example.test/review", "http://example.test/path?a=1#part", "[Review](https://example.test/path)"):
            with self.subTest(text=text):
                self.assertEqual(relay.clean(text), text)

    def test_sensitive_query_still_removed(self):
        self.assertEqual(relay.clean("https://example.test/path?token=fixture"),
                         "https://example.test/path [query omitted]")

    def test_userinfo_still_omitted(self):
        self.assertEqual(relay.clean("https://reader:fixture@example.test/path"),
                         "[credential-bearing URL omitted]")

    def test_reset_link_still_omitted(self):
        self.assertEqual(relay.clean("https://example.test/reset-password/fixture"),
                         "[credential-bearing URL omitted]")

    def test_tracking_link_still_omitted(self):
        self.assertEqual(relay.clean("https://click.example.test/tracking/fixture"),
                         "[tracking/action link omitted]")

    def test_other_scrubbing_continues(self):
        text = "api_key=fixture https://[bad <@U123> @here"
        result = relay.clean(text)
        self.assertIn("api_key=[REDACTED]", result)
        self.assertIn("[malformed URL omitted]", result)
        self.assertNotIn("fixture", result)
        self.assertNotIn("<@", result)
        self.assertNotIn("@here", result)

    def test_clean_is_idempotent_after_omission(self):
        result = relay.clean("Review https://[bad today")
        self.assertEqual(relay.clean(result), result)

    def test_event_renders_malformed_header_and_body(self):
        event = relay.Event("github", "fixture/1", "v1", "Review https://[title", "Fix ready https://[body", "https://[source")
        messages = event.messages()
        self.assertEqual(len(messages), 1)
        self.assertIn("Fix ready [malformed URL omitted]", messages[0])
        self.assertIn("relay.part=", messages[0])
        self.assertEqual(messages[0].count("[malformed URL omitted]"), 3)

    def test_delivery_progress_and_repeat_dedup(self):
        posted = []
        def slack(method, data):
            if method == "conversations.history":
                return {"ok": True, "messages": [m for m in posted if not m.get("thread_ts")]}
            if method == "conversations.replies":
                return {"ok": True, "messages": [m for m in posted if m.get("thread_ts") == data["ts"] or m["ts"] == data["ts"]]}
            self.assertEqual(method, "chat.postMessage")
            self.assertFalse(data["mrkdwn"])
            ts = "1780000000.%06d" % (len(posted) + 1)
            posted.append({**data, "ts": ts})
            return {"ok": True, "ts": ts}
        first = relay.Event("github", "fixture/1", "v1", "Review https://[bad", "First work item", "https://example.test/1")
        second = relay.Event("github", "fixture/2", "v1", "Next review", "Second work item", "https://example.test/2")
        with tempfile.TemporaryDirectory() as tmp:
            state = relay.State(Path(tmp) / "state.sqlite3")
            try:
                delivery = relay.Delivery(state, slack, min_interval=0)
                self.assertEqual(delivery.deliver(first, "C_FIXTURE"), 1)
                self.assertEqual(delivery.deliver(second, "C_FIXTURE"), 1)
                self.assertEqual(delivery.deliver(first, "C_FIXTURE"), 0)
                self.assertEqual(delivery.deliver(second, "C_FIXTURE"), 0)
            finally:
                state.close()
        self.assertEqual(len(posted), 4)
        self.assertTrue(any("Second work item" in m["text"] for m in posted))

    def test_clean_performs_no_network_or_cli_operation(self):
        with patch.object(relay.urllib.request, "build_opener", side_effect=AssertionError("network")), patch.object(relay, "command_json", side_effect=AssertionError("CLI")):
            self.assertEqual(relay.clean("https://[bad"), "[malformed URL omitted]")

    def test_falsey_inputs_unchanged(self):
        self.assertEqual(relay.clean(None), "")
        self.assertEqual(relay.clean(0), "")

    def test_unrelated_exceptions_not_swallowed(self):
        with patch.object(relay.urllib.parse, "urlsplit", side_effect=RuntimeError("fixture")):
            with self.assertRaises(RuntimeError):
                relay.clean("https://example.test")

    def test_long_work_body_is_not_truncated(self):
        body = "A" * 6000 + " https://[bad finish"
        event = relay.Event("github", "fixture/long", "v1", "Review", body, "https://example.test/long")
        messages = event.messages()
        self.assertEqual(len(messages), 3)
        self.assertIn("[malformed URL omitted] finish", messages[-1])
        self.assertTrue(all("relay.part=" in part for part in messages))


if __name__ == "__main__":
    unittest.main()
