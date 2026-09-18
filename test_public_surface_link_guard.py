from __future__ import annotations
import tempfile
import unittest
from datetime import date
from pathlib import Path
from tools.public_surface_link_guard.core import SCHEMA, scan_manifest

class Base(unittest.TestCase):

    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)

    def tearDown(self):
        self.t.cleanup()

    def write(self, path: str, text: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')

    def m(self, base: str | None='https://example.com/'):
        surface = {'path': 'site/index.html', 'class': 'STOREFRONT'}
        if base is not None:
            surface['public_base_url'] = base
        return {'schema': SCHEMA, 'surfaces': [surface], 'blocked_destinations': [], 'exceptions': [], 'aliases': []}

    def scan(self, manifest, day: str='2026-09-17'):
        return scan_manifest(root=self.root, manifest=manifest, as_of=date.fromisoformat(day))

class PublicSurfaceLinkGuardTests(Base):

    def test_clean(self):
        self.write('site/index.html', '<a href="https://product.example/demo">Demo</a>')
        result = self.scan(self.m())
        self.assertEqual(result['state'], 'PASS_NO_PUBLIC_COMMONS_BACKLINK')
        self.assertEqual(result['evaluation_mode'], 'HISTORICAL_EXPLICIT')

    def test_markdown_pages(self):
        self.write('site/index.html', 'See [work](https://woahwhattheheck.github.io/commons/offer.html).\n')
        result = self.scan(self.m())
        self.assertEqual((result['violations'][0]['reason'], result['violations'][0]['line']), ('COMMONS_PAGES', 1))
        self.assertIn('product-specific', result['violations'][0]['remediation'])

    def test_html_github_case(self):
        self.write('site/index.html', '<a href="HTTPS://GITHUB.COM/WOAHWHATTHEHECK/COMMONS/blob/main/x.md">x</a>')
        self.assertEqual(self.scan(self.m())['violations'][0]['reason'], 'COMMONS_GITHUB')

    def test_percent_encoded(self):
        self.write('site/index.html', 'https://github.com/%77oahwhattheheck/%63ommons/tree/main/demo')
        self.assertEqual(len(self.scan(self.m())['violations']), 1)

    def test_query_fragment(self):
        self.write('site/index.html', 'https://woahwhattheheck.github.io/commons/index.html?x=1#sale')
        self.assertEqual(len(self.scan(self.m())['violations']), 1)

    def test_relative_declared_base(self):
        self.write('site/index.html', '<a href="offer.html">offer</a>')
        self.assertEqual(self.scan(self.m('https://woahwhattheheck.github.io/commons/'))['violations'][0]['reason'], 'COMMONS_PAGES')

    def test_relative_no_base_not_guessed(self):
        self.write('site/index.html', '<a href="offer.html">offer</a>')
        self.assertEqual(self.scan(self.m(None))['violations'], [])

    def test_protocol_relative_without_base(self):
        self.write('site/index.html', '//github.com/woahwhattheheck/commons/tree/main/x')
        self.assertEqual(self.scan(self.m(None))['violations'][0]['reason'], 'COMMONS_GITHUB')

    def test_json_escaped_slashes(self):
        self.write('site/index.html', '{"context":"https:\\/\\/github.com\\/woahwhattheheck\\/commons\\/tree\\/main\\/x"}')
        self.assertEqual(self.scan(self.m(None))['violations'][0]['reason'], 'COMMONS_GITHUB')

    def test_backslash_browser_equivalent(self):
        self.write('site/index.html', '<a href="https:\\\\github.com\\woahwhattheheck\\commons\\tree\\main\\x">x</a>')
        self.assertEqual(self.scan(self.m(None))['violations'][0]['reason'], 'COMMONS_GITHUB')

    def test_terminal_parenthesis(self):
        self.write('site/index.html', 'See (https://github.com/woahwhattheheck/commons).')
        self.assertEqual(self.scan(self.m(None))['violations'][0]['destination'], 'https://github.com/woahwhattheheck/commons')

    def test_alias(self):
        self.write('site/index.html', 'https://go.example/context')
        manifest = self.m()
        manifest['aliases'] = [{'alias': 'https://go.example/context', 'target': 'https://woahwhattheheck.github.io/commons/'}]
        self.assertEqual(self.scan(manifest)['violations'][0]['via_alias'], 'https://go.example/context')

    def test_custom_blocked_board(self):
        self.write('site/index.html', 'https://ops.example/internal/commons-board/card/17')
        manifest = self.m()
        manifest['blocked_destinations'] = [{'id': 'board', 'kind': 'COMMONS_BOARD', 'destination': 'https://ops.example/internal/commons-board/', 'match': 'SUBTREE'}]
        self.assertEqual(self.scan(manifest)['violations'][0]['reason'], 'COMMONS_BOARD')

    def test_alias_to_custom_blocked_action(self):
        self.write('site/index.html', 'https://go.example/action')
        manifest = self.m()
        manifest['blocked_destinations'] = [{'id': 'action', 'kind': 'COMMONS_ACTION', 'destination': 'https://ops.example/private/action/', 'match': 'SUBTREE'}]
        manifest['aliases'] = [{'alias': 'https://go.example/action', 'target': 'https://ops.example/private/action/17'}]
        result = self.scan(manifest)
        self.assertEqual(result['violations'][0]['reason'], 'COMMONS_ACTION')
        self.assertEqual(result['violations'][0]['via_alias'], 'https://go.example/action')

    def test_explicit_internal_classification(self):
        self.write('site/index.html', 'https://product.example')
        self.write('internal/provenance.md', 'https://github.com/woahwhattheheck/commons/tree/main/receipt')
        manifest = self.m()
        manifest['surfaces'].append({'path': 'internal/provenance.md', 'class': 'INTERNAL'})
        result = self.scan(manifest)
        self.assertEqual(result['violations'], [])
        internal = [row for row in result['scanned_surfaces'] if row['class'] == 'INTERNAL'][0]
        self.assertEqual(internal['enforcement'], 'EXPLICIT_INTERNAL')

    def test_active_exception(self):
        destination = 'https://github.com/woahwhattheheck/commons/tree/main/special'
        self.write('site/index.html', destination)
        manifest = self.m()
        manifest['exceptions'] = [{'path': 'site/index.html', 'destination': destination, 'expires_on': '2026-09-18', 'reason': 'owner'}]
        result = self.scan(manifest)
        self.assertEqual(result['violations'], [])
        self.assertEqual(len(result['active_exemptions']), 1)

    def test_expired_exception(self):
        destination = 'https://github.com/woahwhattheheck/commons/tree/main/special'
        self.write('site/index.html', destination)
        manifest = self.m()
        manifest['exceptions'] = [{'path': 'site/index.html', 'destination': destination, 'expires_on': '2026-09-17', 'reason': 'owner'}]
        self.assertEqual(self.scan(manifest, '2026-09-18')['violations'][0]['reason'], 'EXPIRED_EXCEPTION')

    def test_generated_artifact_reintroduction(self):
        self.write('site/index.html', 'https://product.example')
        self.write('dist/generated/customer.html', '<a href="https://woahwhattheheck.github.io/commons/receipt/17">context</a>')
        manifest = self.m()
        manifest['surfaces'].append({'path': 'dist/generated/customer.html', 'class': 'PUBLIC_DELIVERABLE', 'public_base_url': 'https://product.example/'})
        result = self.scan(manifest)
        self.assertEqual(result['state'], 'HOLD_PUBLIC_COMMONS_BACKLINK')
        self.assertEqual(result['violations'][0]['path'], 'dist/generated/customer.html')

    def test_authority_false(self):
        self.write('site/index.html', 'https://product.example')
        self.assertEqual(self.scan(self.m())['authority'], {'network_access_performed': False, 'external_send_authorized': False, 'deployment_authorized': False, 'owner_exception_inferred': False})
if __name__ == '__main__':
    unittest.main()
