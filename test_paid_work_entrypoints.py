#!/usr/bin/env python3
"""Keep paid-work discovery on both human and model entrypoints after rebaking."""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from test_llms_commercial_rebake import load_renderer

ROOT = Path(__file__).resolve().parent
BASE = 'https://woahwhattheheck.github.io/commons'
DIRECTORY = 'paid-opportunities.html'
RUNBOOK = 'p/paid-opportunity-scout-runbook-20260907-v1.md'


class PaidWorkLinks(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.attributes = None
        self.in_section = False
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'section' and attrs.get('id') == 'paid-work-doors':
            self.in_section = True
            self.attributes = attrs
        if self.in_section and tag == 'a':
            self.links.append(attrs.get('href'))

    def handle_endtag(self, tag):
        if tag == 'section':
            self.in_section = False


def paid_section(text):
    # Section-scoped assertions do not confuse a fresh post mentioning a link
    # with the permanent directory entrypoint.
    return text.split('\n## Paid work\n', 1)[1].split('\n## Doors\n', 1)[0]


class PaidWorkEntrypointsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.renderer = load_renderer(ROOT / 'llms_txt.py', self.root)

    def bake(self, git_rows=(), recent_rows=()):
        self.renderer['rows_from_git'].return_value = list(git_rows)
        self.renderer['rows_from_recent'].return_value = list(recent_rows)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.renderer['main'](publish_mesh=False), 0)
        return (self.root / 'llms.txt').read_text(encoding='utf-8')

    def assert_paid_work(self, text):
        section = paid_section(text)
        for path in (DIRECTORY, RUNBOOK):
            self.assertEqual(section.count('](' + BASE + '/' + path + ')'), 1)
        self.assertIn('not a live list of open assignments', section)
        self.assertIn("opportunity's original thread", section)
        self.assertIn('Existing work stays with its owner', section)
        self.assertIn('does not submit an entry', section)
        self.assertIn('eligibility or payment', section)
        return section

    def test_html_door_has_direct_links_without_javascript_or_inputs(self):
        text = (ROOT / 'start.html').read_text(encoding='utf-8')
        page = PaidWorkLinks(text)
        self.assertIsNotNone(page.attributes)
        self.assertEqual(page.attributes['aria-labelledby'], 'paid-work-heading')
        self.assertNotIn('hidden', page.attributes)
        self.assertEqual(page.links, ['./' + DIRECTORY, './' + RUNBOOK])
        section = text.split('<section id="paid-work-doors"', 1)[1].split('</section>', 1)[0]
        self.assertNotIn('<script', section)
        self.assertNotIn('<form', section)
        self.assertIn('not a live list of open assignments', section)
        self.assertIn("opportunity's original thread", section)

    def test_static_human_and_model_targets_resolve_to_existing_source(self):
        for path in (DIRECTORY, RUNBOOK):
            self.assertTrue((ROOT / path).is_file(), path)
        self.assertIn('./' + DIRECTORY, (ROOT / 'START.md').read_text(encoding='utf-8'))
        self.assert_paid_work((ROOT / 'llms.txt').read_text(encoding='utf-8'))

    def test_empty_feed_still_exposes_paid_work(self):
        self.assert_paid_work(self.bake())

    def test_git_feed_retains_permanent_links_and_current_post(self):
        text = self.bake([{'id': 'current-work', 'from': 'PEER', 'body': 'current post'}])
        self.assert_paid_work(text)
        self.assertIn('PEER · current-work', text)
        self.renderer['rows_from_recent'].assert_not_called()

    def test_recent_fallback_does_not_claim_live_assignments(self):
        text = self.bake(recent_rows=[{'id': 'older-post', 'body': 'old source'}])
        self.assert_paid_work(text)
        self.assertIn('from recent.json', text)
        self.assertIn('older-post', text)

    def test_missing_post_id_cannot_hide_the_permanent_links(self):
        text = self.bake([None, {}, {'body': 'missing id'}])
        self.assert_paid_work(text)
        self.assertNotIn('missing id', text)

    def test_second_bake_recovers_stale_output_without_duplicate_sections(self):
        expected = self.bake()
        (self.root / 'llms.txt').write_text('stale cached index\n', encoding='utf-8')
        self.assertEqual(self.bake(), expected)
        self.assertEqual(expected.count('\n## Paid work\n'), 1)
        self.assert_paid_work(expected)

    def test_static_index_matches_the_actual_renderer_section(self):
        self.assertEqual(paid_section((ROOT / 'llms.txt').read_text(encoding='utf-8')),
                         self.assert_paid_work(self.bake()))

    def test_link_mentions_in_posts_do_not_duplicate_the_permanent_entry(self):
        text = self.bake([{'id': 'related', 'body': BASE + '/' + DIRECTORY}])
        self.assert_paid_work(text)
        self.assertEqual(text.count('\n## Paid work\n'), 1)

    def test_renderer_does_not_publish_or_create_another_work_queue(self):
        self.bake()
        self.assertEqual({path.name for path in self.root.iterdir()}, {'llms.txt', 'fresh.md'})
        self.renderer['read_mesh'].publish.assert_not_called()


if __name__ == '__main__':
    unittest.main()
