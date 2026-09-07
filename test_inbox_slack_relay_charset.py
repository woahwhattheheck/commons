"""MIME charset regressions for the real inbox relay; all fixtures are synthetic."""
import base64
import unittest

from host.inbox_slack_relay import mail_body


def part(text, encoding="utf-8", *, mime_type="text/plain", content_type=None):
    data = text if isinstance(text, bytes) else text.encode(encoding)
    result = {
        "mimeType": mime_type,
        "body": {"data": base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")},
    }
    if content_type is not None:
        result["headers"] = [{"name": "Content-Type", "value": content_type}]
    else:
        result["headers"] = [{"name": "Content-Type", "value": f'{mime_type}; charset="{encoding}"'}]
    return result


class MailCharsetTests(unittest.TestCase):
    def test_declared_legacy_charsets_preserve_work_text(self):
        for encoding, text in [
            ("iso-8859-1", "Révision du dépôt"),
            ("windows-1252", "Review “résumé” — €200"),
            ("iso-2022-jp", "登録の締め切り"),
            ("gb18030", "提交截止日期"),
        ]:
            with self.subTest(encoding=encoding):
                self.assertEqual(mail_body(part(text, encoding)), text)

    def test_header_name_and_charset_are_case_insensitive(self):
        payload = part("Révision", "iso-8859-1")
        payload["headers"] = [{"name": "cOnTeNt-TyPe", "value": 'text/plain; CHARSET="ISO-8859-1"'}]
        self.assertEqual(mail_body(payload), "Révision")

    def test_folded_content_type_and_other_parameters(self):
        payload = part("Résumé", "windows-1252", content_type='text/plain; format=flowed;\r\n charset="WINDOWS-1252"')
        self.assertEqual(mail_body(payload), "Résumé")

    def test_utf8_without_charset_remains_the_default(self):
        text = "Résumé — 登録"
        for content_type in (None, "text/plain", 'text/plain; charset=""'):
            payload = part(text)
            if content_type is None:
                payload.pop("headers")
            else:
                payload["headers"][0]["value"] = content_type
            with self.subTest(content_type=content_type):
                self.assertEqual(mail_body(payload), text)

    def test_unknown_or_non_text_codec_falls_back_to_utf8(self):
        text = "Révision — 登録"
        for charset in ("unknown-mail-charset", "base64_codec", "rot_13", "\x00", "漢字"):
            with self.subTest(charset=charset):
                self.assertEqual(mail_body(part(text, content_type=f'text/plain; charset="{charset}"')), text)

    def test_bad_bytes_use_replacement_without_losing_the_message(self):
        self.assertEqual(mail_body(part(b"before\xffafter")), "before�after")
        self.assertEqual(mail_body(part(b"before\xffafter", content_type="text/plain; charset=unknown")), "before�after")
        self.assertEqual(mail_body(part(b"before\x81after", content_type="text/plain; charset=windows-1252")), "before�after")

    def test_html_is_decoded_before_inert_text_extraction(self):
        markup = '<head>hidden</head><p>Révision &amp; dépôt — €200</p><script>hidden()</script><img src="https://example.invalid/pixel">'
        self.assertEqual(mail_body(part(markup, "windows-1252", mime_type="text/html")), "Révision & dépôt — €200")

    def test_mixed_parts_use_their_own_charsets_not_the_container(self):
        payload = {"mimeType": "multipart/mixed", "headers": [{"name": "Content-Type", "value": "multipart/mixed; charset=ascii"}], "parts": [
            part("Révision", "iso-8859-1"), part("登録", "iso-2022-jp"),
        ]}
        self.assertEqual(mail_body(payload), "Révision\n登録")

    def test_nested_alternative_preserves_plain_preference(self):
        payload = {"mimeType": "multipart/mixed", "parts": [
            {"mimeType": "multipart/alternative", "parts": [
                part("Résumé", "windows-1252"), part("<p>duplicate</p>", mime_type="text/html"),
            ]}, part("提交", "gb18030"),
        ]}
        self.assertEqual(mail_body(payload), "Résumé\n提交")

    def test_html_only_alternative_is_decoded(self):
        payload = {"mimeType": "multipart/alternative", "parts": [part("<p>Résumé</p>", "iso-8859-1", mime_type="text/html")]}
        self.assertEqual(mail_body(payload), "Résumé")

    def test_named_attachment_stays_omitted(self):
        payload = part("Attachment résumé", "windows-1252")
        payload["filename"] = "private.txt"
        self.assertEqual(mail_body(payload), "")

    def test_remote_attachment_body_stays_pending(self):
        payload = {"mimeType": "text/plain", "headers": [{"name": "Content-Type", "value": "text/plain; charset=windows-1252"}], "body": {"attachmentId": "synthetic-id"}}
        self.assertEqual(mail_body(payload), "[Body stored as an attachment; read original in Gmail.]")

    def test_invalid_base64_keeps_existing_diagnostic(self):
        payload = part("unused")
        payload["body"]["data"] = "a"
        self.assertEqual(mail_body(payload), "[Body decoding failed; read original in Gmail.]")

    def test_non_text_part_is_not_returned(self):
        self.assertEqual(mail_body(part("not a text body", mime_type="application/octet-stream")), "")

    def test_body_bytes_are_not_transfer_decoded_a_second_time(self):
        payload = part("Literal =E9 and Qm9keQ==")
        payload["headers"].append({"name": "Content-Transfer-Encoding", "value": "quoted-printable"})
        self.assertEqual(mail_body(payload), "Literal =E9 and Qm9keQ==")


if __name__ == "__main__":
    unittest.main()
