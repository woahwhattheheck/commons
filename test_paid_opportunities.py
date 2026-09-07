#!/usr/bin/env python3
"""Static paid-work directory and its real catalog renderer entrypoint."""
from __future__ import annotations

import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import hub_pages

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    'C0BVANHNB26': '#bug-bounty',
    'C0BV7KHRGF7': '#math-bounties',
    'C0C0TQ56F9N': '#feature-bounties',
    'C0C01AXLCGZ': '#integration-bounties',
    'C0BUY2GT8P9': '#data-science-bounties',
    'C0C0344TF7W': '#china-bounties',
    'C0BUY3EKMSB': '#university-prizes',
    'C0BVDDS04G2': '#international-competitions',
}
LINK = './paid-opportunities.html'


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.elements.append((tag, values))
        if tag == 'a':
            self.links.append(values.get('href', ''))


class DirectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / 'paid-opportunities.html').read_text(encoding='utf-8')
        cls.page = Page(cls.text)

    def test_exact_source_channel_map_is_static_and_unique(self):
        cards = [attrs for tag, attrs in self.page.elements if tag == 'li' and 'data-channel' in attrs]
        self.assertCountEqual([card['data-channel'] for card in cards], EXPECTED)
        for card in cards:
            self.assertNotIn('hidden', card)
        runbook = (ROOT / 'p/paid-opportunity-scout-runbook-20260907-v1.md').read_text(encoding='utf-8')
        for channel, label in EXPECTED.items():
            href = 'https://tokenjunkielabs.slack.com/archives/' + channel
            self.assertEqual(self.page.links.count(href), 1)
            self.assertIn(f'>{label}</a>', self.text)
            self.assertIn(f'[{label}]({href})', runbook)

    def test_static_page_has_home_runbook_and_resolvable_local_links(self):
        self.assertIn('./index.html', self.page.links)
        self.assertIn('./p/paid-opportunity-scout-runbook-20260907-v1.md', self.page.links)
        for href in self.page.links:
            parts = urlsplit(href)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            self.assertTrue((ROOT / parts.path).is_file(), href)

    def test_optional_controls_and_accessible_status(self):
        ids = [attrs['id'] for _, attrs in self.page.elements if 'id' in attrs]
        self.assertEqual(len(ids), len(set(ids)))
        by_id = {attrs['id']: attrs for _, attrs in self.page.elements if 'id' in attrs}
        self.assertIn('hidden', by_id['channel-search'])
        self.assertEqual(by_id['channel-query']['type'], 'search')
        self.assertEqual(by_id['channel-clear']['type'], 'button')
        self.assertEqual(by_id['channel-count']['role'], 'status')
        self.assertEqual(by_id['channel-count']['aria-live'], 'polite')
        self.assertTrue(any(tag == 'label' and attrs.get('for') == 'channel-query' for tag, attrs in self.page.elements))
        self.assertIn('[hidden]{display:none!important}', self.text)

    def test_dated_snapshot_and_stale_recovery_are_not_live_status(self):
        self.assertIn('datetime="2026-09-07"', self.text)
        self.assertIn('not a live feed', self.text)
        self.assertIn('An old card or a link that does not open?', self.text)
        self.assertIn('current sponsor source', self.text)
        self.assertIn('https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3', self.page.links)

    def test_source_specific_exceptions_and_outcomes_remain_visible(self):
        for phrase in ['Existing work stays', 'PROGRAM FEED', 'not an individual award',
                       'does not reopen closed registration', 'student-only entry or university funding',
                       'Organizer location does not establish', 'concept and paper competitions',
                       'CLAIMED, SUBMITTED, AWARDED and PAID', 'not automatically a payout',
                       'direct shared secure tools']:
            self.assertIn(phrase, self.text)

    def test_committed_start_and_boards_link_to_directory(self):
        for path in ['START.md', 'boards.html']:
            self.assertEqual((ROOT / path).read_text(encoding='utf-8').count(LINK), 1, path)

    def test_actual_catalog_rebuild_retains_link_with_empty_or_active_jobs(self):
        for state in ({'open': [], 'receipts': 0}, {'open': [{'id': 'existing-job'}], 'receipts': 4}):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as tmp:
                mod = SimpleNamespace(ROOT=tmp, CSS='', doors=lambda: '<nav>existing navigation</nav>',
                                      _write=lambda path, text: Path(path).write_text(text, encoding='utf-8'))
                hub_pages.rebuild_boards(mod, state)
                first = (Path(tmp) / 'boards.html').read_text(encoding='utf-8')
                self.assertEqual(Page(first).links.count(LINK), 1)
                self.assertIn('existing navigation', first)
                self.assertIn('id="boardsum"', first)
                self.assertIn('id="live-cash-doors"', first)
                self.assertIn('./agent-rescue.html', Page(first).links)
                hub_pages.rebuild_boards(mod, state)
                self.assertEqual((Path(tmp) / 'boards.html').read_text(encoding='utf-8'), first)


if __name__ == '__main__':
    unittest.main()
