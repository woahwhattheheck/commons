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


class IPv6URLRenderingTests(unittest.TestCase):
    """Bracketed authorities reach the same parser and scrubber as DNS hosts."""

    def test_compressed_literal_is_retained(self):
        url = "https://[2001:db8::1]/review"
        self.assertEqual(relay.clean(url), url)

    def test_expanded_literal_is_retained(self):
        url = "https://[2001:0db8:0000:0000:0000:0000:0000:0001]/review"
        self.assertEqual(relay.clean(url), url)

    def test_case_ports_and_both_schemes(self):
        for scheme in ("http", "https"):
            for authority in ("[2001:DB8::ABCD]", "[2001:db8::1]:8080", "[::1]:443"):
                url = scheme + "://" + authority + "/review"
                self.assertEqual(relay.clean(url), url)

    def test_bare_authority_and_fragment(self):
        for tail in ("", "/", "#part", "/notes?a=1#part"):
            url = "https://[2001:db8::1]" + tail
            self.assertEqual(relay.clean(url), url)

    def test_mapped_ipv4_and_zone_identifier(self):
        for authority in ("[::ffff:192.0.2.128]", "[fe80::1%25eth0]"):
            url = "https://" + authority + "/review"
            self.assertEqual(relay.clean(url), url)

    def test_markdown_and_angle_wrappers_are_preserved(self):
        url = "https://[2001:db8::1]:8443/review"
        for prefix, suffix in (("(", ")"), ("[", "]"), ("<", ">"), ("[Review](", ")")):
            text = prefix + url + suffix
            self.assertEqual(relay.clean(text), text)
            self.assertEqual(relay.URL.findall(text), [url])

    def test_sensitive_query_reaches_existing_scrubber(self):
        for key in ("token", "sig", "code", "%74oken", "AUTH", "api_key"):
            url = "https://[2001:db8::1]:8443/review?" + key + "=synthetic#section"
            self.assertEqual(relay.clean(url),
                             "https://[2001:db8::1]:8443/review [query omitted]")

    def test_sensitive_query_inside_wrappers(self):
        text = "[Review](https://[2001:db8::1]/review?token=synthetic) next"
        self.assertEqual(relay.clean(text),
                         "[Review](https://[2001:db8::1]/review [query omitted]) next")

    def test_userinfo_is_omitted_with_entire_ipv6_url(self):
        for userinfo in ("reader@", "reader:synthetic@", "reader%40example.test:synthetic@", ":synthetic@"):
            url = "https://" + userinfo + "[2001:db8::1]:8443/review?x=1"
            self.assertEqual(relay.clean(url), "[credential-bearing URL omitted]")

    def test_existing_action_path_filter_is_preserved(self):
        for path in ("/reset-password/synthetic", "/password/reset/synthetic",
                     "/verify-email/synthetic", "/magic-link/synthetic", "/auth/callback/synthetic"):
            self.assertEqual(relay.clean("https://[2001:db8::1]" + path),
                             "[credential-bearing URL omitted]")

    def test_unsubscribe_filter_is_preserved(self):
        self.assertEqual(relay.clean("https://[2001:db8::1]/unsubscribe/synthetic"),
                         "[tracking/action link omitted]")

    def test_invalid_closed_literal_still_uses_parser_omission(self):
        for authority in ("[not-an-ip]", "[2001:db8::gg]"):
            self.assertEqual(relay.clean("Read https://" + authority + "/review now"),
                             "Read [malformed URL omitted] now")

    def test_unclosed_literal_keeps_prior_omission(self):
        self.assertEqual(relay.clean("Read https://[2001:db8::1/review now"),
                         "Read [malformed URL omitted] now")

    def test_multiple_addresses_and_ordinary_links(self):
        text = "https://[2001:db8::1]/a https://example.test/b http://[2001:db8::2]/c"
        self.assertEqual(relay.clean(text), text)
        self.assertEqual(relay.URL.findall(text), text.split())

    def test_unicode_work_text_and_mentions(self):
        text = "Révision 日本語 https://[2001:db8::1]/review <@U123> @here"
        self.assertEqual(relay.clean(text),
                         "Révision 日本語 https://[2001:db8::1]/review ＜@U123> ＠here")

    def test_idempotence_with_retained_and_scrubbed_links(self):
        for tail in ("/review", "/review?token=synthetic", "/unsubscribe/synthetic"):
            text = relay.clean("[https://[2001:db8::1]" + tail + "]")
            self.assertEqual(relay.clean(text), text)

    def test_event_header_and_body_retain_valid_addresses(self):
        url = "https://[2001:db8::1]/review"
        event = relay.Event("github", "fixture/ipv6", "v1", "Review " + url, "Ready " + url, url)
        rendered = event.messages()[0]
        self.assertEqual(rendered.count(url), 3)
        self.assertNotIn("[malformed URL omitted]", rendered)
        self.assertIn("relay.part=", rendered)

    def test_event_scrubs_sensitive_ipv6_query_in_all_fields(self):
        url = "https://[2001:db8::1]/review?token=synthetic"
        event = relay.Event("github", "fixture/redacted", "v1", url, url, url)
        rendered = event.messages()[0]
        self.assertNotIn("synthetic", rendered)
        self.assertEqual(rendered.count("[query omitted]"), 3)

    def test_long_body_is_complete_across_chunks(self):
        body = "A" * 6000 + " https://[2001:db8::1]/review finished"
        event = relay.Event("github", "fixture/long-v6", "v1", "Review", body, "https://example.test/review")
        messages = event.messages()
        self.assertEqual(len(messages), 3)
        self.assertIn("https://[2001:db8::1]/review finished", messages[-1])
        recovered = "".join(m.split("):\n", 1)[1].rsplit("\n\nrelay.part=", 1)[0] for m in messages)
        self.assertEqual(recovered, body)

    def test_deterministic_documentation_address_matrix(self):
        import ipaddress
        import random
        rng = random.Random(20260908)
        prefix = int(ipaddress.IPv6Address("2001:db8::"))
        for _ in range(128):
            address = ipaddress.IPv6Address(prefix | rng.getrandbits(96))
            for form in (address.compressed, address.exploded):
                url = "https://[" + form + "]:8443/review?a=1#part"
                self.assertEqual(relay.clean(url), url)
                self.assertEqual(relay.clean(url.replace("?a=1#part", "?token=synthetic")),
                                 url.split("?", 1)[0] + " [query omitted]")

    def test_ordinary_token_boundaries_match_existing_pattern(self):
        import re
        legacy = re.compile(r"https?://[^\s<>\]\)]+")
        for host in ("example.test", "192.0.2.1", "click.example.test"):
            for tail in ("", "/path", "/path?a=1#part", "/path[notes", "/a%5Bb%5D", "/review?token=synthetic"):
                for prefix, suffix in (("", ""), ("[", "]"), ("(", ")"), ("<", ">")):
                    text = prefix + "https://" + host + tail + suffix + " next"
                    self.assertEqual(relay.URL.findall(text), legacy.findall(text))

    def test_renderer_does_not_fetch_or_execute_links(self):
        with patch.object(relay.urllib.request, "build_opener", side_effect=AssertionError("network")), \
                patch.object(relay, "command_json", side_effect=AssertionError("CLI")):
            self.assertEqual(relay.clean("https://[2001:db8::1]/review"),
                             "https://[2001:db8::1]/review")

    def test_mime_alternative_preserves_ipv6_link_after_html_extraction(self):
        import base64
        html = "<p>Révision https://[2001:db8::1]/review</p>"
        payload = {"mimeType": "multipart/alternative", "parts": [
            {"mimeType": "text/plain", "body": {"data": ""}},
            {"mimeType": "text/html", "headers": [{"name": "Content-Type", "value": "text/html; charset=utf-8"}],
             "body": {"data": base64.urlsafe_b64encode(html.encode()).decode()}},
        ]}
        self.assertEqual(relay.clean(relay.mail_body(payload)),
                         "Révision https://[2001:db8::1]/review")

    def test_generated_field_redaction_remains_one_url_token(self):
        for authority in ("example.test", "[2001:db8::1]"):
            for key in ("api_key", "access_token", "refresh_token", "password"):
                text = "Read https://" + authority + "/review?" + key + "=synthetic next"
                self.assertEqual(relay.clean(text),
                                 "Read https://" + authority + "/review [query omitted] next")

    def test_generated_secret_redaction_and_outer_markdown_bracket(self):
        # This synthetic shape is scrubbed before URL tokenization, without
        # treating the generated marker's closing bracket as the outer bracket.
        for authority in ("example.test", "[2001:db8::1]"):
            text = "[https://" + authority + "/review?token=ghp_syntheticfixture]"
            self.assertEqual(relay.clean(text),
                             "[https://" + authority + "/review [query omitted]]")

    def test_real_run_and_reopened_ledger_deduplicate_content(self):
        import base64
        url = "https://[2001:db8::1]/review"
        message = {"id": "fixture", "threadId": "fixture-thread", "labelIds": ["INBOX"], "payload": {
            "mimeType": "text/plain", "headers": [{"name": "Subject", "value": "Review deadline"},
                {"name": "From", "value": "worker@example.invalid"}],
            "body": {"data": base64.urlsafe_b64encode(("Review " + url).encode()).decode()},
        }}
        posted, methods = [], []
        test = self

        class RecordedProviders:
            def github(self, endpoint):
                methods.append(("github", endpoint))
                if endpoint == "user":
                    return {"login": "fixture-user"}
                test.assertTrue(endpoint.startswith("notifications?"))
                return []

            def gmail(self, resource, params=None):
                methods.append(("gmail", resource))
                return {"profile": {"emailAddress": "worker@example.invalid"},
                        "messages": {"messages": [{"id": "fixture"}]}, "messages/fixture": message}[resource]

            def slack(self, method, data):
                methods.append(("slack", method))
                if method == "auth.test":
                    return {"ok": True, "url": "https://fixture.slack.com/"}
                if method == "conversations.history":
                    return {"ok": True, "messages": [m for m in posted if m["channel"] == data["channel"] and not m.get("thread_ts")]}
                if method == "conversations.replies":
                    return {"ok": True, "messages": [m for m in posted if m["channel"] == data["channel"] and (m.get("thread_ts") == data["ts"] or m["ts"] == data["ts"])]}
                if method == "chat.update":
                    existing = next(m for m in posted if m["channel"] == data["channel"] and m["ts"] == data["ts"])
                    existing.update(data)
                    return {"ok": True, "ts": data["ts"]}
                test.assertEqual(method, "chat.postMessage")
                test.assertFalse(data["mrkdwn"])
                ts = "1780000000.%06d" % (len(posted) + 1)
                posted.append({**data, "ts": ts})
                return {"ok": True, "ts": ts}

        config = {"github_login": "fixture-user", "gmail_address": "worker@example.invalid",
                  "slack_workspace": "fixture.slack.com", "github_channel": "C_GH",
                  "gmail_channel": "C_MAIL", "health_channel": "C_HEALTH", "min_post_interval": 0}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            for expected_parts in (1, 0):
                state = relay.State(path)
                try:
                    report = relay.run(config, state, RecordedProviders())
                finally:
                    state.close()
                self.assertEqual(report["posted_parts"], expected_parts)
                self.assertEqual(report["status"], "LIVE")
            self.assertNotIn(url.encode(), path.read_bytes())
        contents = [m["text"] for m in posted if m["channel"] == "C_MAIL" and m.get("thread_ts")]
        self.assertEqual(len(contents), 1)
        self.assertIn("Review " + url, contents[0])
        self.assertEqual(len(posted), 3)  # source root, source part, updated health
        self.assertIn(("slack", "chat.update"), methods)
        self.assertTrue(all(endpoint in {"profile", "messages", "messages/fixture"}
                            for provider, endpoint in methods if provider == "gmail"))


if __name__ == "__main__":
    unittest.main()
