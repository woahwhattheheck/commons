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

    def test_existing_pending_attachment_diagnostic_is_preserved(self):
        pending = {"mimeType": "text/plain", "body": {"attachmentId": "synthetic"}}
        self.assertEqual(mail_body(alternative(pending, part("<p>HTML</p>", "text/html"))), "[Body stored as an attachment; read original in Gmail.]")

    def test_existing_decode_diagnostic_is_preserved(self):
        invalid = {"mimeType": "text/plain", "body": {"data": "a"}}
        self.assertEqual(mail_body(alternative(invalid, part("<p>HTML</p>", "text/html"))), "[Body decoding failed; read original in Gmail.]")

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


if __name__ == "__main__":
    unittest.main()
