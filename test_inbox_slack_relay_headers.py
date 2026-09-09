"""RFC 2047 display/routing regressions; no live messages or providers."""
import base64
import copy
import unittest
from email.header import Header

from host.inbox_slack_relay import gmail_events


def word(text, encoding="utf-8"):
    return Header(text, encoding).encode()


def fixture(title, sender="Person <work@sponsor.example>", labels=None):
    headers = [{"name": "From", "value": sender}]
    if title is not None:
        headers.append({"name": "Subject", "value": title})
    return {"id": "synthetic", "threadId": "synthetic-thread", "labelIds": labels or ["INBOX"],
            "payload": {"mimeType": "text/plain", "headers": headers,
                        "body": {"data": base64.urlsafe_b64encode(b"Synthetic fixture only.").decode()}}}


class MailHeaderTests(unittest.TestCase):
    def parse(self, title, *, sender="Person <work@sponsor.example>", known=True, labels=None):
        message = fixture(title, sender, labels)
        before = copy.deepcopy(message)
        calls = []
        def get(path, params=None):
            calls.append((path, params))
            return {"profile": {"emailAddress": "work@example.invalid"},
                    "messages": {"messages": [{"id": "synthetic"}]},
                    "messages/synthetic": message}[path]
        config = {"gmail_address": "work@example.invalid", "work_sender_domains": ["sponsor.example"] if known else []}
        result = gmail_events(get, config, "")
        self.assertEqual(message, before)
        self.assertEqual([call[0] for call in calls], ["profile", "messages", "messages/synthetic"])
        self.assertEqual(calls[-1][1], {"format": "full"})
        return result

    def test_encoded_work_subject_is_selected_and_readable(self):
        title = "Review résumé"
        events, info = self.parse(word(title), known=False)
        self.assertEqual(info["unclassified_pending"], 0)
        self.assertEqual([e.title for e in events], [title])

    def test_encoded_acknowledgement_keeps_existing_action(self):
        events, info = self.parse(word("Registration received"), known=False)
        self.assertEqual(len(events), 1)
        self.assertEqual(info["unclassified_pending"], 0)
        self.assertTrue(events[0].action.startswith("Acknowledgement only:"))

    def test_legacy_charset_subject_is_readable(self):
        events, _ = self.parse(word("Review résumé", "iso-8859-1"))
        self.assertEqual(events[0].title, "Review résumé")

    def test_folded_adjacent_encoded_words_are_joined(self):
        subject = "=?utf-8?b?UmV2aWV3IA==?=\r\n =?iso-8859-1?q?r=E9sum=E9?="
        events, _ = self.parse(subject)
        self.assertEqual(events[0].title, "Review résumé")

    def test_plain_text_surrounding_encoded_words_is_preserved(self):
        events, _ = self.parse("Review " + word("résumé") + " due Monday")
        self.assertEqual(events[0].title, "Review résumé due Monday")

    def test_encoded_auth_subject_is_omitted_for_known_sender(self):
        for title in ("Password reset", "Sign-in alert", "Verification code"):
            with self.subTest(title=title):
                events, info = self.parse(word(title))
                self.assertEqual(events, [])
                self.assertEqual(info["private_or_auth_omitted"], 1)

    def test_encoded_private_subject_is_omitted_for_known_sender(self):
        events, info = self.parse(word("Medical record"))
        self.assertEqual(events, [])
        self.assertEqual(info["private_or_auth_omitted"], 1)

    def test_sender_display_decodes_without_reparsing_address(self):
        sender = word("Résumé, Team") + " <work@sponsor.example>"
        events, info = self.parse("Hello", sender=sender)
        self.assertEqual(len(events), 1)
        self.assertEqual(info["unclassified_pending"], 0)
        self.assertEqual(events[0].author, "Résumé, Team <work@sponsor.example>")

    def test_display_name_does_not_select_sender_domain(self):
        sender = word("Work <person@sponsor.example>") + " <person@unknown.example>"
        events, info = self.parse("Hello", sender=sender)
        self.assertEqual(events, [])
        self.assertEqual(info["unclassified_pending"], 1)

    def test_github_dedup_uses_original_sender_address(self):
        sender = word("Résumé, Team") + " <notifications@github.com>"
        events, info = self.parse(word("Review résumé"), sender=sender)
        self.assertEqual(events, [])
        self.assertEqual(info["github_mail_deduped"], 1)

    def test_decoded_header_mentions_stay_inert_in_slack(self):
        title = "Review <@U123> @here"
        sender = word("Résumé @channel") + " <work@sponsor.example>"
        events, _ = self.parse(word(title), sender=sender)
        self.assertEqual(events[0].title, title)
        rendered = "\n".join(events[0].messages())
        self.assertIn("Résumé", rendered)
        self.assertNotIn("<@U123>", rendered)
        self.assertNotIn("@here", rendered)
        self.assertNotIn("@channel", rendered)

    def test_plain_folded_header_is_unfolded(self):
        for spacing in (" ", "   "):
            with self.subTest(spacing=spacing):
                events, _ = self.parse("Review\r\n" + spacing + "tomorrow")
                self.assertEqual(events[0].title, "Review" + spacing + "tomorrow")

    def test_plain_headers_are_unchanged(self):
        title, sender = "Review tomorrow", "Person <work@sponsor.example>"
        events, _ = self.parse(title, sender=sender)
        self.assertEqual((events[0].title, events[0].author), (title, sender))

    def test_already_decoded_unicode_headers_are_unchanged(self):
        title, sender = "Review résumé", "Personne <work@sponsor.example>"
        events, _ = self.parse(title, sender=sender)
        self.assertEqual((events[0].title, events[0].author), (title, sender))

    def test_unknown_or_non_text_charset_uses_utf8_fallback(self):
        data = base64.b64encode("Review résumé".encode()).decode()
        for charset in ("unknown-mail-charset", "base64_codec", "rot_13", "漢字"):
            with self.subTest(charset=charset):
                events, _ = self.parse(f"=?{charset}?b?{data}?=")
                self.assertEqual(events[0].title, "Review résumé")

    def test_invalid_text_bytes_use_replacement(self):
        data = base64.b64encode(b"Review before\xffafter").decode()
        events, _ = self.parse(f"=?utf-8?b?{data}?=")
        self.assertEqual(events[0].title, "Review before�after")

    def test_malformed_base64_stays_literal_without_losing_message(self):
        for title in ("Review =?utf-8?b?a?=", "Review =?\x00?b?YWJj?="):
            with self.subTest(title=title):
                events, _ = self.parse(title)
                self.assertEqual(events[0].title, title)

    def test_native_unicode_surrounding_encoded_word_is_preserved(self):
        events, _ = self.parse("Review café " + word("résumé") + " ☃")
        self.assertEqual(events[0].title, "Review café résumé ☃")

    def test_literal_unicode_escape_is_not_interpreted(self):
        events, _ = self.parse(r"Review \u2603 " + word("résumé"))
        self.assertEqual(events[0].title, r"Review \u2603 résumé")

    def test_missing_subject_retains_existing_default(self):
        events, _ = self.parse(None)
        self.assertEqual(events[0].title, "(no subject)")

    def test_promotional_mail_is_still_omitted(self):
        events, info = self.parse(word("Review résumé"), labels=["INBOX", "CATEGORY_PROMOTIONS"])
        self.assertEqual(events, [])
        self.assertEqual(info["promotional_omitted"], 1)

    def test_unknown_nonwork_subject_stays_pending(self):
        events, info = self.parse(word("Bonjour résumé"), known=False)
        self.assertEqual(events, [])
        self.assertEqual(info["unclassified_pending"], 1)


if __name__ == "__main__":
    unittest.main()
