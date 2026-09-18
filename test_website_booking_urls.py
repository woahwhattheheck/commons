#!/usr/bin/env python3
"""Resolve source-relative booking URLs before using them outside the page."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "website_booking_urls_subject", ROOT / "host" / "website_people_email_book.py"
)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


class WebsiteBookingURLTests(unittest.TestCase):
    def extract(self, href: str, source: str = "https://seller.test/company/about/",
                before: str = "") -> dict:
        return subject.extract_website(
            before + '<h1>Fixture seller</h1><a href="' + href + '" data-book-url>Book</a>',
            source,
        )

    def test_parent_relative_link(self):
        self.assertEqual(self.extract("../book")["book_url"],
                         "https://seller.test/company/book")

    def test_root_relative_link(self):
        self.assertEqual(self.extract("/book")["book_url"], "https://seller.test/book")

    def test_document_relative_link(self):
        self.assertEqual(self.extract("book")["book_url"],
                         "https://seller.test/company/about/book")

    def test_source_filename_is_not_a_directory(self):
        self.assertEqual(self.extract("book", "https://seller.test/about.html")["book_url"],
                         "https://seller.test/book")

    def test_query_and_fragment_links(self):
        self.assertEqual(self.extract("?slot=two")["book_url"],
                         "https://seller.test/company/about/?slot=two")
        self.assertEqual(self.extract("#booking")["book_url"],
                         "https://seller.test/company/about/#booking")

    def test_network_path_inherits_source_scheme(self):
        self.assertEqual(self.extract("//calendar.test/team")["book_url"],
                         "https://calendar.test/team")
        self.assertEqual(self.extract("//calendar.test/team", "http://seller.test/")
                         ["book_url"], "http://calendar.test/team")

    def test_absolute_link_retains_other_origin(self):
        url = "https://calendar.test/team?x=one#slot"
        self.assertEqual(self.extract(url)["book_url"], url)

    def test_query_entities_decode_once(self):
        self.assertEqual(self.extract("../book?x=one&amp;y=&amp;lt;")["book_url"],
                         "https://seller.test/company/book?x=one&y=&lt;")

    def test_absolute_base_href(self):
        self.assertEqual(self.extract("book", before='<base href="https://calendar.test/team/">')
                         ["book_url"], "https://calendar.test/team/book")

    def test_relative_base_href(self):
        self.assertEqual(self.extract("book", before='<base href="../../calendar/">')
                         ["book_url"], "https://seller.test/calendar/book")

    def test_first_base_href_wins(self):
        bases = '<base href="/first/"><base href="/later/">'
        self.assertEqual(self.extract("book", before=bases)["book_url"],
                         "https://seller.test/first/book")

    def test_empty_first_base_href_still_wins(self):
        bases = '<base href=""><base href="/later/">'
        self.assertEqual(self.extract("book", before=bases)["book_url"],
                         "https://seller.test/company/about/book")

    def test_base_without_href_does_not_replace_document_base(self):
        bases = '<base target="_blank"><base href="/calendar/">'
        self.assertEqual(self.extract("book", before=bases)["book_url"],
                         "https://seller.test/calendar/book")

    def test_local_source_does_not_invent_a_web_origin(self):
        for source in ("fixture.html", "/tmp/fixture.html", "file:///tmp/fixture.html"):
            with self.subTest(source=source):
                self.assertEqual(self.extract("../book", source)["book_url"], "../book")

    def test_missing_booking_link_remains_missing(self):
        website = subject.extract_website('<base href="https://seller.test/">',
                                          "https://seller.test/about/")
        self.assertIsNone(website["book_url"])

    def test_invalid_base_retains_extracted_metadata_and_original_url(self):
        website = self.extract("/book", before='<meta name="description" content="Keep me">'
                               '<base href="https://[broken/">')
        self.assertEqual(website["description"], "Keep me")
        self.assertEqual(website["book_url"], "/book")

    def test_invalid_source_retains_original_url(self):
        self.assertEqual(self.extract("/book", "https://[broken/")["book_url"], "/book")

    def test_actual_draft_and_booking_receive_resolved_url(self):
        website = self.extract("../book?team=one&amp;slot=two")
        prospect = {"organization": "Buyer fixture", "owner_role": None,
                    "prospect_id": "buyer-fixture", "evidence": {
                        "exact_quote": "Fixture need", "source_url": "https://buyer.test/need",
                    }}
        expected = "https://seller.test/company/book?team=one&slot=two"
        self.assertIn("book a call: " + expected, subject._draft(prospect, website)["body"])
        booking = subject._booking(prospect, website)
        self.assertEqual(booking["book_url"], expected)
        self.assertEqual(booking["state"], "STAGED_NOT_BOOKED")
        self.assertEqual(booking["calls_booked"], 0)


if __name__ == "__main__":
    unittest.main()
