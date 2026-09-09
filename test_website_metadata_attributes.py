#!/usr/bin/env python3
"""Exercise real website attribute extraction without mail or calendar transport."""
from __future__ import annotations

import importlib.util
import itertools
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "website_metadata_subject", ROOT / "host" / "website_people_email_book.py"
)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


class WebsiteMetadataAttributeTests(unittest.TestCase):
    def extract(self, html: str) -> dict:
        return subject.extract_website(html, "https://seller.test/")

    def test_description_attribute_permutations(self):
        for attrs in itertools.permutations([
            'name="description"', 'content="Source description"', 'id="summary"'
        ]):
            with self.subTest(attrs=attrs):
                self.assertEqual(self.extract("<meta " + " ".join(attrs) + ">")
                                 ["description"], "Source description")

    def test_og_attribute_permutations(self):
        for attrs in itertools.permutations([
            'property="og:description"', 'content="OG description"', 'id="summary"'
        ]):
            with self.subTest(attrs=attrs):
                self.assertEqual(self.extract("<meta " + " ".join(attrs) + ">")
                                 ["description"], "OG description")

    def test_booking_attribute_permutations(self):
        for attrs in itertools.permutations([
            'data-book-url', 'href="https://seller.test/book"', 'class="booking"'
        ]):
            with self.subTest(attrs=attrs):
                self.assertEqual(self.extract("<a " + " ".join(attrs) + ">Book</a>")
                                 ["book_url"], "https://seller.test/book")

    def test_single_and_unquoted_attributes(self):
        for html in [
            "<meta content='A description' name='description'>",
            "<meta content=Description name=description>",
        ]:
            with self.subTest(html=html):
                self.assertTrue(self.extract(html)["description"])
        self.assertEqual(self.extract('<a href=/book data-book-url>Book</a>')["book_url"],
                         "https://seller.test/book")

    def test_case_whitespace_and_self_closing_meta(self):
        html = '<META CONTENT = "A description" NAME = "DESCRIPTION" />'
        self.assertEqual(self.extract(html)["description"], "A description")
        html = '<A HREF = "/book" DATA-BOOK-URL = "">Book</A>'
        self.assertEqual(self.extract(html)["book_url"], "https://seller.test/book")

    def test_apostrophe_in_double_quoted_description(self):
        html = '<meta name="description" content="Customer\'s description">'
        self.assertEqual(self.extract(html)["description"], "Customer's description")

    def test_apostrophe_in_double_quoted_booking_url(self):
        html = '<a data-book-url href="/book/team\'s-slot">Book</a>'
        self.assertEqual(self.extract(html)["book_url"], "https://seller.test/book/team's-slot")

    def test_description_entities_decode_once_and_preserve_literal_text(self):
        html = '<meta content="A &amp; B &lt;offer&gt; &amp;lt;" name="description">'
        self.assertEqual(self.extract(html)["description"], "A & B <offer> &lt;")

    def test_booking_entities_decode_once(self):
        html = '<a href="/book?team=one&amp;label=&amp;lt;" data-book-url>Book</a>'
        self.assertEqual(self.extract(html)["book_url"], "https://seller.test/book?team=one&label=&lt;")

    def test_quoted_angle_brackets_do_not_end_tag(self):
        html = '<meta data-note="x > y" content="A > B" name="description">'
        self.assertEqual(self.extract(html)["description"], "A > B")

    def test_comments_do_not_supply_attributes(self):
        html = '<!-- <meta name="description" content="Not metadata">' \
               '<a data-book-url href="/wrong">Wrong</a> -->'
        result = self.extract(html)
        self.assertEqual(result["description"], "")
        self.assertIsNone(result["book_url"])

    def test_script_and_style_text_do_not_supply_attributes(self):
        for tag in ["script", "style"]:
            html = f'<{tag}>const example = \'<meta name="description" ' \
                   f'content="Not metadata"><a data-book-url href="/wrong">\';</{tag}>'
            with self.subTest(tag=tag):
                result = self.extract(html)
                self.assertEqual(result["description"], "")
                self.assertIsNone(result["book_url"])

    def test_attribute_names_are_exact(self):
        html = '<meta data-name="description" content="Not metadata">' \
               '<meta name="description" data-content="Not metadata">' \
               '<a data-book-url-extra href="/wrong">Wrong</a>'
        result = self.extract(html)
        self.assertEqual(result["description"], "")
        self.assertIsNone(result["book_url"])

    def test_standard_description_keeps_precedence_over_og(self):
        html = '<meta property="og:description" content="OG">' \
               '<meta name="description" content="Standard">'
        self.assertEqual(self.extract(html)["description"], "Standard")

    def test_first_nonempty_candidate_wins(self):
        html = '<meta name="description" content=" ">' \
               '<meta name="description" content="First">' \
               '<meta name="description" content="Later">' \
               '<a data-book-url>Missing href</a>' \
               '<a data-book-url href=" ">Blank href</a>' \
               '<a data-book-url href="/first">First</a>' \
               '<a data-book-url href="/later">Later</a>'
        result = self.extract(html)
        self.assertEqual(result["description"], "First")
        self.assertEqual(result["book_url"], "https://seller.test/first")

    def test_duplicate_attributes_use_first_value(self):
        html = '<meta name="description" content="First" content="Later">' \
               '<a data-book-url href="/first" href="/later">Book</a>'
        result = self.extract(html)
        self.assertEqual(result["description"], "First")
        self.assertEqual(result["book_url"], "https://seller.test/first")

    def test_existing_calendar_fallback_and_explicit_precedence(self):
        fallback = '<a href="https://cal.com/seller/intro">Book</a>'
        self.assertEqual(self.extract(fallback)["book_url"], "https://cal.com/seller/intro")
        explicit = '<a data-book-url href="/custom-book">Book</a>'
        self.assertEqual(self.extract(fallback + explicit)["book_url"], "https://seller.test/custom-book")

    def test_existing_title_headline_icp_and_missing_values(self):
        html = '<title>Seller title</title><h1>Seller headline</h1>' \
               '<p data-icp>Operations teams</p>'
        result = self.extract(html)
        self.assertEqual(result, {
            "source": "https://seller.test/", "title": "Seller title",
            "headline": "Seller headline", "description": "",
            "icp": "Operations teams", "book_url": None,
        })

    def test_draft_and_staged_booking_consume_extracted_values(self):
        website = self.extract('<h1>Seller</h1><meta content="A &amp; B" '
                               'name="description"><a href="/book?x=1&amp;y=2" '
                               'data-book-url>Book</a>')
        prospect = {"organization": "Buyer fixture", "owner_role": None,
                    "prospect_id": "buyer-fixture", "evidence": {
                        "exact_quote": "A fixture need",
                        "source_url": "https://buyer.test/need",
                    }}
        draft = subject._draft(prospect, website)
        booking = subject._booking(prospect, website)
        self.assertIn("A & B", draft["body"])
        self.assertIn("/book?x=1&y=2", draft["body"])
        self.assertEqual(booking["book_url"], "https://seller.test/book?x=1&y=2")
        self.assertEqual(booking["state"], "STAGED_NOT_BOOKED")
        self.assertEqual(booking["calls_booked"], 0)


if __name__ == "__main__":
    unittest.main()
