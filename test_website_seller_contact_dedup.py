"""Repeated seller cards share the existing JSON-LD first-seen identity rule."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "website_seller_contact_dedup", ROOT / "host" / "website_people_email_book.py"
)
assert SPEC and SPEC.loader
loop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loop)


def card(name="Ava", email="ava@seller.test", *, tag="article", role="Founder", need="Replay"):
    address = f'<a href="mailto:{email}">Email</a>' if email is not None else ""
    return (
        f'<{tag} data-person><h2>{name}</h2><span data-role>{role}</span>'
        f'<span data-need>{need}</span>{address}</{tag}>'
    )


def structured(*people):
    return '<script type="application/ld+json">' + json.dumps(list(people)) + '</script>'


class SellerContactDedupTests(unittest.TestCase):
    def test_repeated_cards_keep_first_email_and_metadata_for_every_card_tag(self):
        for tag in ("article", "div", "section", "li"):
            with self.subTest(tag=tag):
                people = loop._page_people(
                    card(tag=tag) + card("Different label", "AVA@SELLER.TEST?subject=Hi",
                                         tag=tag, role="Later", need="Changed")
                )
                self.assertEqual(people, [{
                    "name": "Ava", "email": "ava@seller.test", "role": "Founder",
                    "need": "Replay", "source": "page-person",
                }])

    def test_repeated_email_free_names_use_squeezed_unicode_casefold(self):
        people = loop._page_people(card("  Stra\u00dfe  Team ", None) + card("STRASSE   TEAM", None))
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0]["name"], "Stra\u00dfe Team")
        self.assertIsNone(people[0]["email"])

    def test_email_free_card_after_addressed_name_is_not_an_extra_person(self):
        people = loop._page_people(card() + card("AVA", None))
        self.assertEqual([p["email"] for p in people], ["ava@seller.test"])

    def test_shared_name_does_not_collapse_distinct_email_addresses(self):
        people = loop._page_people(card() + card("Ava", "other@seller.test"))
        self.assertEqual([p["email"] for p in people], ["ava@seller.test", "other@seller.test"])

    def test_addressed_card_after_email_free_name_preserves_existing_ld_rule(self):
        # Do not infer that an unaddressed namesake and an addressed person are identical.
        people = loop._page_people(card("Ava", None) + card())
        self.assertEqual([p["email"] for p in people], [None, "ava@seller.test"])

    def test_same_email_with_different_name_keeps_first_source(self):
        people = loop._page_people(card() + card("Ava Founder"))
        self.assertEqual([p["name"] for p in people], ["Ava"])

    def test_page_ld_and_footer_share_one_email_identity(self):
        html = card() + card() + structured(
            {"@type": "Person", "name": "Ava JSON", "email": "AVA@seller.test"},
            {"@type": "Person", "name": "Bea", "email": "bea@seller.test"},
        ) + '<footer><a href="mailto:ava@seller.test">Contact</a></footer>'
        people = loop._page_people(html)
        self.assertEqual([(p["email"], p["source"]) for p in people], [
            ("ava@seller.test", "page-person"), ("bea@seller.test", "json-ld"),
        ])

    def test_email_free_page_and_ld_duplicates_share_name_identity(self):
        html = card("Ava", None) * 2 + structured({"@type": "Person", "name": "AVA"})
        self.assertEqual(len(loop._page_people(html)), 1)

    def test_additional_mailbox_in_duplicate_card_remains_discoverable(self):
        repeated = card().replace('</article>', '<a href="mailto:help@seller.test">Help</a></article>')
        people = loop._page_people(card() + repeated)
        self.assertEqual([(p["email"], p["source"]) for p in people], [
            ("ava@seller.test", "page-person"), ("help@seller.test", "mailto"),
        ])

    def test_email_only_cards_and_blank_cards_do_not_inflate_count(self):
        html = card("", "ava@seller.test") * 2 + card("", None)
        people = loop._page_people(html)
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0]["name"], "ava")

    def test_invalid_email_uses_same_name_only_fallback(self):
        people = loop._page_people(card("Ava", "not-an-email") + card("AVA", None))
        self.assertEqual(len(people), 1)
        self.assertIsNone(people[0]["email"])

    def test_first_seen_order_is_stable_with_interleaved_duplicates(self):
        html = (card("Bea", "bea@seller.test") + card() + card("Bea", "BEA@seller.test")
                + card("Cy", "cy@seller.test") + card())
        first = loop._page_people(html)
        self.assertEqual([p["email"] for p in first], [
            "bea@seller.test", "ava@seller.test", "cy@seller.test",
        ])
        self.assertEqual(first, loop._page_people(html))
        finalized = [loop._finish_seller_contact(p) for p in first]
        self.assertEqual(len({p["contact_id"] for p in finalized}), 3)
        self.assertTrue(all("seller context only" in p["next_action"] for p in finalized))

    def test_build_loop_reports_unique_seller_count_without_transport(self):
        # Isolate only the external prospect planner; run real extraction, count and validation.
        with mock.patch.object(loop, "_load_smart_outreach") as planner:
            planner.return_value.build_plan.return_value = {"items": []}
            result = loop.build_loop(card() * 3, "https://seller.test", prospect_catalog={})
        loop.validate_loop(result)
        self.assertEqual(result["truth"]["seller_contacts_observed"], 1)
        self.assertEqual(len(result["seller_contacts"]), 1)
        self.assertEqual(result["emails"], [])
        self.assertEqual(result["bookings"], [])
        self.assertEqual(result["truth"]["transport_actions"], 0)
        self.assertEqual(result["truth"]["calls_booked"], 0)
        self.assertEqual(result["truth"]["cash_usd"], 0)


if __name__ == "__main__":
    unittest.main()
