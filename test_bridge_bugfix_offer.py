"""Offline contract checks for the standalone bugfix offer; no network calls."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import unittest

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / 'sites' / 'bugfix' / 'index.html'

class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.text = []
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
    def handle_data(self, data):
        self.text.append(data)

class BugfixOfferTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding='utf-8')
        cls.doc = Document(cls.html)
        cls.text = ' '.join(cls.doc.text)
    def test_document_language_and_viewport(self):
        self.assertIn(('html', {'lang': 'en'}), self.doc.elements)
        self.assertTrue(any(tag == 'meta' and attrs.get('name') == 'viewport' for tag, attrs in self.doc.elements))
        self.assertEqual(sum(tag == 'h1' for tag, _ in self.doc.elements), 1)
    def test_no_missing_or_duplicate_fragment_targets(self):
        ids = [attrs['id'] for _, attrs in self.doc.elements if 'id' in attrs]
        self.assertEqual(len(ids), len(set(ids)))
        for tag, attrs in self.doc.elements:
            href = attrs.get('href', '')
            if tag == 'a' and href.startswith('#'):
                self.assertIn(href[1:], ids)
    def test_real_email_recipient_and_primary_intake(self):
        targets = [attrs['href'] for tag, attrs in self.doc.elements if tag == 'a' and attrs.get('href', '').startswith('mailto:')]
        self.assertTrue(targets)
        self.assertTrue(all(urlsplit(target).path == 'tokenjunkielabs@gmail.com' for target in targets))
        self.assertIn('Request a scoped quote', self.text)
        self.assertIn('Nothing is submitted to us until you send the email.', self.text)
    def test_external_evidence_is_exact_accepted_pr(self):
        urls = [attrs['href'] for tag, attrs in self.doc.elements if tag == 'a' and attrs.get('href', '').startswith('https:')]
        self.assertEqual(urls, ['https://github.com/Lilly-Protocol/agentlily-runtime/pull/384'])
        self.assertIn('not a customer endorsement, payment receipt or guarantee', self.text)
        self.assertIn('reported passing', self.text)
    def test_new_tab_links_are_isolated(self):
        for tag, attrs in self.doc.elements:
            if tag == 'a' and attrs.get('target') == '_blank':
                self.assertTrue({'noopener', 'noreferrer'}.issubset(set(attrs.get('rel', '').split())))
    def test_no_external_assets_or_data_submission(self):
        for tag, attrs in self.doc.elements:
            self.assertFalse(tag in ('script', 'iframe', 'img') and attrs.get('src'))
            self.assertFalse(tag == 'link' and attrs.get('rel') == 'stylesheet')
            self.assertFalse(tag == 'form' and attrs.get('action', '').startswith('http'))
        for forbidden in ('fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'document.cookie', 'innerHTML', 'buy.stripe.com', 'type="file"'):
            self.assertNotIn(forbidden, self.html)
    def test_intake_controls_are_labeled_and_bounded(self):
        labels = {attrs.get('for') for tag, attrs in self.doc.elements if tag == 'label'}
        for tag, attrs in self.doc.elements:
            if tag in ('input', 'textarea'):
                self.assertIn(attrs['id'], labels)
                self.assertLessEqual(int(attrs['maxlength']), 1800)
        self.assertIn('role="status"', self.html)
        self.assertIn("encodeURIComponent(body)", self.html)
    def test_scope_and_existing_offer_stay_distinct(self):
        for text in ('before paid work starts', 'separately scoped engagement', 'does not include this service', 'AI assistance is disclosed', 'passwords, API keys', 'third-party maintainer'):
            self.assertIn(text, self.text)
        self.assertNotIn('$90', self.text)
    def test_mobile_and_reduced_motion_rules(self):
        self.assertIn('@media(max-width:760px)', self.html)
        self.assertIn('prefers-reduced-motion:reduce', self.html)
        self.assertIn('focus-visible', self.html)

if __name__ == '__main__':
    unittest.main()
