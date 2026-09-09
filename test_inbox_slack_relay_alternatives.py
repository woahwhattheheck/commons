"""Readable MIME-alternative fallback; synthetic source data only."""
import base64
import copy
import unittest

from host.inbox_slack_relay import gmail_events, mail_body


def part(text, mime_type="text/plain", encoding="utf-8", **extra):
    return {
        "mimeType": mime_type,
        "headers": [{"name": "Content-Type", "value": f"{mime_type}; charset={encoding}"}],
        "body": {"data": base64.urlsafe_b64encode(text.encode(encoding)).decode("ascii").rstrip("=")},
        **extra,
    }


def alternative(*parts):
    return {"mimeType": "multipart/alternative", "parts": list(parts)}


class MailAlternativeTests(unittest.TestCase):
    def test_empty_plain_falls_back_to_readable_html(self):
        payload = alternative(part(""), part("<p>Review tomorrow</p>", "text/html"))
        self.assertEqual(mail_body(payload), "Review tomorrow")

    def test_blank_plain_falls_back_to_readable_html(self):
        payload = alternative(part("  \r\n\t"), part("<p>Review tomorrow</p>", "text/html"))
        self.assertEqual(mail_body(payload), "Review tomorrow")

    def test_named_plain_attachment_is_omitted_not_selected(self):
        payload = alternative(part("private attachment", filename="note.txt"), part("<p>Public review</p>", "text/html"))
        self.assertEqual(mail_body(payload), "Public review")

    def test_usable_plain_still_wins_over_html(self):
        payload = alternative(part("plain body"), part("<p>duplicate HTML body</p>", "text/html"))
        self.assertEqual(mail_body(payload), "plain body")

    def test_next_usable_plain_precedes_html(self):
        payload = alternative(part(""), part("plain body"), part("<p>duplicate</p>", "text/html"))
        self.assertEqual(mail_body(payload), "plain body")

    def test_unsupported_last_alternative_does_not_hide_html(self):
        payload = alternative(part("<p>Review tomorrow</p>", "text/html"), part("calendar bytes", "text/calendar"))
        self.assertEqual(mail_body(payload), "Review tomorrow")

    def test_nonplain_alternatives_keep_last_usable_preference(self):
        payload = alternative(part("<p>old alternative</p>", "text/html"), part("<p>last alternative</p>", "text/html"))
        self.assertEqual(mail_body(payload), "last alternative")

    def test_blank_latest_html_falls_back_without_concatenating(self):
        payload = alternative(part("<p>Readable</p>", "text/html"), part("<p> </p>", "text/html"))
        self.assertEqual(mail_body(payload), "Readable")

    def test_nested_alternatives_retain_one_body(self):
        payload = {"mimeType": "multipart/mixed", "parts": [
            alternative(part(""), alternative(part(""), part("<p>Review</p>", "text/html"))),
            part(" separate body"),
        ]}
        self.assertEqual(mail_body(payload), "Review\n separate body")

    def test_fallback_keeps_leaf_charset_repair(self):
        payload = alternative(part(""), part("<p>Résumé — €200</p>", "text/html", "windows-1252"))
        self.assertEqual(mail_body(payload), "Résumé — €200")

    def test_all_blank_or_unsupported_alternatives_are_empty(self):
        for payload in (alternative(), alternative(part("   ")), alternative(part("x", "application/octet-stream"))):
            with self.subTest(payload=payload):
                self.assertEqual(mail_body(payload), "")

    def test_pending_plain_falls_back_when_html_is_readable(self):
        pending = {"mimeType": "text/plain", "body": {"attachmentId": "synthetic"}}
        self.assertEqual(mail_body(alternative(pending, part("<p>HTML</p>", "text/html"))), "HTML")

    def test_invalid_plain_falls_back_when_html_is_readable(self):
        invalid = {"mimeType": "text/plain", "body": {"data": "a"}}
        self.assertEqual(mail_body(alternative(invalid, part("<p>HTML</p>", "text/html"))), "HTML")

    def test_input_parts_are_not_mutated(self):
        payload = alternative(part(""), part("<p>Review</p>", "text/html"))
        before = copy.deepcopy(payload)
        mail_body(payload)
        self.assertEqual(payload, before)

    def test_gmail_event_carries_fallback_body_through_existing_scrubber(self):
        payload = alternative(part(""), part("<p>Résumé review &lt;@U123&gt; @here</p>", "text/html", "windows-1252"))
        payload["headers"] = [{"name": "Subject", "value": "Review deadline"}, {"name": "From", "value": "work@example.invalid"}]
        message = {"id": "synthetic", "threadId": "synthetic-thread", "labelIds": ["INBOX"], "payload": payload}
        calls = []
        def get(resource, params=None):
            calls.append(resource)
            return {"profile": {"emailAddress": "work@example.invalid"}, "messages": {"messages": [{"id": "synthetic"}]}, "messages/synthetic": message}[resource]
        events, info = gmail_events(get, {"gmail_address": "work@example.invalid"}, "")
        self.assertEqual(len(events), 1)
        self.assertEqual(info["body_pending"], 0)
        self.assertIn("Résumé review", events[0].body)
        rendered = "\n".join(events[0].messages())
        self.assertIn("Résumé review", rendered)
        self.assertNotIn("<@U123>", rendered)
        self.assertNotIn("@here", rendered)
        self.assertEqual(calls, ["profile", "messages", "messages/synthetic"])


class MailDiagnosticAlternativeTests(unittest.TestCase):
    pending_text = "[Body stored as an attachment; read original in Gmail.]"
    invalid_text = "[Body decoding failed; read original in Gmail.]"

    @staticmethod
    def pending(mime_type="text/plain"):
        return {"mimeType": mime_type, "body": {"attachmentId": "synthetic"}}

    @staticmethod
    def invalid(mime_type="text/plain"):
        return {"mimeType": mime_type, "body": {"data": "a"}}

    def test_pending_plain_uses_next_readable_plain_before_html(self):
        payload = alternative(self.pending(), part("next plain"), part("<p>HTML</p>", "text/html"))
        self.assertEqual(mail_body(payload), "next plain")

    def test_invalid_plain_uses_next_readable_plain(self):
        self.assertEqual(mail_body(alternative(self.invalid(), part("next plain"))), "next plain")

    def test_pending_last_html_does_not_hide_earlier_html(self):
        payload = alternative(part("<p>available</p>", "text/html"), self.pending("text/html"))
        self.assertEqual(mail_body(payload), "available")

    def test_invalid_last_html_does_not_hide_earlier_html(self):
        payload = alternative(part("<p>available</p>", "text/html"), self.invalid("text/html"))
        self.assertEqual(mail_body(payload), "available")

    def test_nested_diagnostic_alternative_does_not_hide_readable_body(self):
        payload = alternative(part("<p>available</p>", "text/html"), alternative(self.pending(), self.invalid()))
        self.assertEqual(mail_body(payload), "available")

    def test_nested_diagnostic_mixed_part_does_not_hide_readable_body(self):
        unavailable = {"mimeType": "multipart/mixed", "parts": [self.pending(), self.invalid()]}
        self.assertEqual(mail_body(alternative(part("<p>available</p>", "text/html"), unavailable)), "available")

    def test_mixed_readable_and_missing_parts_preserve_missing_diagnostic(self):
        mixed = {"mimeType": "multipart/mixed", "parts": [self.pending(), part("available portion")]}
        self.assertEqual(mail_body(alternative(part("<p>earlier</p>", "text/html"), mixed)),
                         self.pending_text + "\navailable portion")

    def test_pending_diagnostic_retained_without_readable_alternative(self):
        self.assertEqual(mail_body(alternative(self.pending(), part("<p> </p>", "text/html"))), self.pending_text)
        self.assertEqual(mail_body(self.pending()), self.pending_text)

    def test_decode_diagnostic_retained_without_readable_alternative(self):
        self.assertEqual(mail_body(alternative(self.invalid(), part(""))), self.invalid_text)
        self.assertEqual(mail_body(self.invalid()), self.invalid_text)

    def test_multiple_unavailable_alternatives_keep_first_diagnostic(self):
        self.assertEqual(mail_body(alternative(self.pending(), self.invalid())), self.pending_text)
        self.assertEqual(mail_body(alternative(self.invalid(), self.pending())), self.invalid_text)

    def test_literal_diagnostic_looking_source_text_is_readable(self):
        for literal in (self.pending_text, self.invalid_text, self.pending_text + "\n" + self.invalid_text):
            with self.subTest(literal=literal):
                self.assertEqual(mail_body(alternative(part(literal), part("<p>HTML</p>", "text/html"))), literal)

    def test_hidden_only_html_does_not_discard_diagnostic(self):
        hidden = part("<head><title>hidden</title></head><script>ignored</script><style>hidden</style>", "text/html")
        self.assertEqual(mail_body(alternative(self.pending(), hidden)), self.pending_text)

    def test_diagnostic_fallback_preserves_leaf_charset(self):
        for body, encoding in (("Résumé — €200", "windows-1252"), ("日本語", "iso-2022-jp")):
            with self.subTest(encoding=encoding):
                payload = alternative(self.pending(), part("<p>" + body + "</p>", "text/html", encoding))
                self.assertEqual(mail_body(payload), body)

    def test_named_attachment_is_not_a_readable_fallback(self):
        payload = alternative(self.pending(), part("attachment contents", filename="private.txt"))
        self.assertEqual(mail_body(payload), self.pending_text)

    def test_diagnostic_fallback_does_not_mutate_mime_tree(self):
        payload = alternative(self.pending(), alternative(self.invalid(), part("<p>available</p>", "text/html")))
        before = copy.deepcopy(payload)
        self.assertEqual(mail_body(payload), "available")
        self.assertEqual(payload, before)

    def test_diagnostic_fallback_never_fetches_attachments_or_links(self):
        from unittest.mock import patch
        from host import inbox_slack_relay as relay
        with patch.object(relay.urllib.request, "build_opener", side_effect=AssertionError("network")), \
                patch.object(relay, "command_json", side_effect=AssertionError("CLI")):
            payload = alternative(self.pending(), part('<p>available</p><img src="https://example.invalid/image">', "text/html"))
            self.assertEqual(mail_body(payload), "available")

    def test_gmail_fallback_has_no_pending_body_and_keeps_redaction(self):
        payload = alternative(self.pending(), part("<p>Review &lt;@U123&gt; @here api_key=fixture</p>", "text/html"))
        payload["headers"] = [{"name": "Subject", "value": "Review deadline"}, {"name": "From", "value": "work@example.invalid"}]
        message = {"id": "synthetic", "threadId": "synthetic-thread", "labelIds": ["INBOX"], "payload": payload}
        calls = []
        def get(resource, params=None):
            calls.append(resource)
            return {"profile": {"emailAddress": "work@example.invalid"}, "messages": {"messages": [{"id": "synthetic"}]}, "messages/synthetic": message}[resource]
        events, info = gmail_events(get, {"gmail_address": "work@example.invalid"}, "")
        self.assertEqual(len(events), 1)
        self.assertEqual(info["body_pending"], 0)
        rendered = "\n".join(events[0].messages())
        self.assertIn("Review", rendered)
        self.assertIn("api_key=[REDACTED]", rendered)
        self.assertNotIn("fixture", rendered)
        self.assertNotIn("<@U123>", rendered)
        self.assertNotIn("@here", rendered)
        self.assertEqual(calls, ["profile", "messages", "messages/synthetic"])
        self.assertEqual(events[0].messages(), events[0].messages())

    def test_gmail_missing_mixed_part_still_counts_as_pending(self):
        mixed = {"mimeType": "multipart/mixed", "parts": [self.pending(), part("available portion")]}
        payload = alternative(part("<p>earlier</p>", "text/html"), mixed)
        payload["headers"] = [{"name": "Subject", "value": "Review deadline"}, {"name": "From", "value": "work@example.invalid"}]
        message = {"id": "synthetic", "threadId": "synthetic-thread", "labelIds": ["INBOX"], "payload": payload}
        def get(resource, params=None):
            return {"profile": {"emailAddress": "work@example.invalid"}, "messages": {"messages": [{"id": "synthetic"}]}, "messages/synthetic": message}[resource]
        events, info = gmail_events(get, {"gmail_address": "work@example.invalid"}, "")
        self.assertEqual(len(events), 1)
        self.assertEqual(info["body_pending"], 1)
        self.assertEqual(events[0].body, self.pending_text + "\navailable portion")


if __name__ == "__main__":
    unittest.main()
