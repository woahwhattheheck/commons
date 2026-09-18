"""Offline Chromium URL/path correspondence tests for the existing viewer."""
import base64
from copy import deepcopy
import json
from pathlib import Path
import shutil
import unittest
from urllib.parse import quote

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parent
SHA = 'a' * 40
API = 'https://api.github.com/repos/woahwhattheheck/commons/contents/'
WEB = 'https://github.com/woahwhattheheck/commons/blob/' + SHA + '/'
DOM = '''<!doctype html><html lang="en"><meta charset="utf-8"><body>
<input id="cw-search" type="search"><select id="cw-kind"><option value="">All</option></select>
<button id="cw-refresh">Refresh</button><p id="cw-source"></p><p id="cw-count"></p>
<div id="cw-items"></div></body></html>'''


def item(path, title='Path fixture', kind='BUILDABLE'):
    return {'id': title, 'title': title, 'kind': kind, 'claimed_paths': [path]}


@unittest.skipIf(sync_playwright is None, 'optional Playwright package not installed')
class CurrentWorkPathBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = sync_playwright().start()
        try:
            cls.browser = cls.runtime.chromium.launch(
                headless=True, executable_path=shutil.which('chromium') or None)
        except Exception as error:
            cls.runtime.stop()
            raise unittest.SkipTest('Chromium unavailable: ' + str(error).splitlines()[0])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.runtime.stop()

    def setUp(self):
        self.context = None
        self.errors = []
        self.requests = []
        self.path_requests = []
        self.path_status = 200

    def tearDown(self):
        if self.context:
            self.context.close()
        self.assertEqual(self.errors, [])
        self.assertTrue(all(method == 'GET' for method, _ in self.requests))

    def boot(self, rows):
        if self.context:
            self.context.close()
        self.rows = deepcopy(rows)
        self.requests = []
        self.path_requests = []
        self.context = self.browser.new_context()
        self.context.route('**/*', self.respond)
        self.page = self.context.new_page()
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.set_content(DOM)
        self.page.evaluate('window.module = {exports:{}}')
        self.page.add_script_tag(content=(ROOT / 'current_work_ui.js').read_text(encoding='utf-8'))
        self.page.evaluate('''async () => {
          window.ui = window.module.exports;
          window.viewer = ui.mount(document, window.fetch.bind(window));
          await viewer.ready;
        }''')
        self.assertTrue(self.page.locator('#cw-source').inner_text().startswith('Observed main '),
                        self.page.locator('#cw-source').inner_text())
        self.assertEqual(self.page.locator('#cw-items article').count(), len(rows))

    def respond(self, route):
        # Browser fetch is real. Every outbound request is intercepted before
        # leaving Chromium, including any URL already normalized out of scope.
        url = route.request.url
        self.requests.append((route.request.method, url))
        status = 200
        if url.endswith('/git/ref/heads/main'):
            value = {'object': {'sha': SHA}}
        elif '/contents/ground/CURRENT_WORK.json?' in url:
            raw = json.dumps({'schema': 'commons-current-work-v1', 'items': self.rows}).encode()
            value = {'encoding': 'base64', 'content': base64.b64encode(raw).decode()}
        else:
            self.path_requests.append(url)
            status = self.path_status
            # A 200 here deliberately proves that status alone cannot identify
            # the originally claimed tree path after URL dot normalization.
            value = {'fixture_response': 'HTTP status is not path correspondence'}
        route.fulfill(status=status, headers={'access-control-allow-origin': '*',
                      'content-type': 'application/json'}, body=json.dumps(value))

    def card(self, title='Path fixture'):
        return self.page.locator('#cw-items article').filter(
            has=self.page.get_by_role('heading', name=title, exact=True))

    def assert_invalid(self, title='Path fixture'):
        card = self.card(title)
        self.assertIn('INVALID ROW', card.inner_text())
        self.assertEqual(card.locator('button').count(), 0)
        self.assertEqual(card.locator('a').count(), 0)
        self.assertEqual(self.path_requests, [])

    def check_path(self, title='Path fixture'):
        self.card(title).get_by_role('button').click()
        self.page.wait_for_function("document.querySelector('#cw-items button').getAttribute('aria-disabled') === 'false'")

    def test_parent_and_current_directory_segments_are_not_tree_paths(self):
        for path in ('../', '../../../../', 'a/../../../../', './file.py', 'x/../file.py', '.', '..', 'x/.'):
            with self.subTest(path=path):
                self.boot([item(path)])
                self.assert_invalid()

    def test_absolute_and_empty_interior_segments_remain_inspectable(self):
        for path in ('/file.py', '/', '//server/file', 'dir//file.py', '', 'dir//'):
            with self.subTest(path=path):
                self.boot([item(path)])
                self.assert_invalid()

    def test_unencodable_unicode_or_nul_cannot_abort_all_cards(self):
        for path in ('bad\ud800.py', '\udfff', 'nul\0file'):
            with self.subTest(path=ascii(path)):
                self.boot([item('src/good.py', 'Good work'), item(path)])
                self.assert_invalid()
                self.assertEqual(self.card('Good work').count(), 1)
                self.assertIn('UNVERIFIED', self.card('Good work').inner_text())

    def test_percent_encoded_dot_names_are_encoded_as_literal_names(self):
        for path in ('%2e%2e/file.py', '.%2E/file.py', '%2Froot', 'dir/%5C..%5Cfile'):
            with self.subTest(path=path):
                self.boot([item(path)])
                self.check_path()
                expected = '/'.join(quote(part, safe="~!*'()-._") for part in path.split('/'))
                self.assertEqual(self.path_requests, [API + expected + '?ref=' + SHA])
                self.assertEqual(self.card().locator('a').evaluate('a => a.href'), WEB + expected)
                self.assertIn('CLOSED', self.card().inner_text())

    def test_valid_filename_characters_retain_exact_pinned_destination(self):
        for path in ('dir/café #1.py', 'emoji/🧪.txt', 'literal\\backslash.txt', 'dir/file?name.txt', 'a:b/file.py', '..hidden/file.py'):
            with self.subTest(path=path):
                self.boot([item(path)])
                self.check_path()
                expected = '/'.join(quote(part, safe="~!*'()-._") for part in path.split('/'))
                self.assertEqual(self.path_requests, [API + expected + '?ref=' + SHA])
                self.assertEqual(self.card().locator('a').evaluate('a => a.href'), WEB + expected)
                self.card().locator('summary').click()
                self.assertEqual(self.card().locator('a').inner_text(), path)

    def test_trailing_directory_slash_retains_existing_meaning(self):
        for path in ('ground/', 'dir/subdir/'):
            with self.subTest(path=path):
                self.boot([item(path)])
                self.check_path()
                self.assertEqual(self.path_requests, [API + path + '?ref=' + SHA])
                self.assertEqual(self.card().locator('a').evaluate('a => a.href'), WEB + path)

    def test_invalid_row_does_not_hide_or_verify_a_valid_neighbor(self):
        self.boot([item('../../../../', 'Invalid path'), item('src/good.py', 'Good work')])
        self.assert_invalid('Invalid path')
        self.check_path('Good work')
        self.assertEqual(self.path_requests, [API + 'src/good.py?ref=' + SHA])
        self.assertIn('CLOSED', self.card('Good work').inner_text())
        self.assertIn('INVALID ROW', self.card('Invalid path').inner_text())
        self.page.locator('#cw-search').fill('invalid path')
        self.assertEqual(self.page.locator('#cw-count').inner_text(), '1 of 2 ledger items')

    def test_direct_source_url_rejects_unrepresentable_paths(self):
        self.boot([])
        for path in ('../', '/root', 'a//b', '\ud800', 'nul\0file'):
            with self.subTest(path=ascii(path)):
                # JSON text transports lone surrogates without Python UTF-8
                # encoding inventing a replacement character before the check.
                result = self.page.evaluate('''text => {
                  try { return {url: ui.sourceURL('a'.repeat(40), JSON.parse(text))}; }
                  catch (error) { return {error: error.name}; }
                }''', json.dumps(path))
                self.assertIn('error', result)
        self.assertEqual(self.path_requests, [])

    def test_direct_path_verification_cannot_close_from_unrelated_http_200(self):
        self.boot([])
        result = self.page.evaluate('''async () => {
          let calls = 0;
          const result = await ui.verifyItem({kind:'BUILDABLE', claimed_paths:['../../../../']},
              {sha:'a'.repeat(40), cache:new Map()}, async () => { calls++; return new Response('{}'); });
          return {result, calls};
        }''')
        self.assertEqual(result, {'result': {'status': 'INVALID ROW', 'missing': []}, 'calls': 0})

    def test_one_invalid_member_prevents_partial_path_closure(self):
        self.boot([])
        for paths in (['ok.py', '../'], ['ok.py', None], ['ok.py', 7], ['ok.py', {}]):
            with self.subTest(paths=paths):
                result = self.page.evaluate('''async paths => {
                  let calls = 0;
                  const result = await ui.verifyItem({kind:'BUILDABLE', claimed_paths:paths},
                    {sha:'a'.repeat(40), cache:new Map()}, async () => {calls++; return new Response('{}');});
                  return {result, calls};
                }''', paths)
                self.assertEqual(result, {'result': {'status': 'INVALID ROW', 'missing': []}, 'calls': 0})

    def test_valid_404_preserves_buildable_vs_owner_status(self):
        for kind, status in (('BUILDABLE', 'OPEN'), ('OWNER_PLATFORM', 'NEEDS_OWNER')):
            with self.subTest(kind=kind):
                self.path_status = 404
                self.boot([item('missing.py', kind=kind)])
                self.check_path()
                self.assertIn(status + ' — Missing: missing.py', self.card().inner_text())
                self.assertEqual(self.path_requests, [API + 'missing.py?ref=' + SHA])

    def test_refresh_replaces_invalid_path_without_carrying_closed_state(self):
        self.boot([item('../')])
        self.assert_invalid()
        self.rows = [item('real/file.py')]
        self.page.evaluate('async () => { await viewer.reload(); }')
        self.assertIn('UNVERIFIED', self.card().inner_text())
        self.assertEqual(self.card().locator('a').evaluate('a => a.href'), WEB + 'real/file.py')
        self.assertEqual(self.path_requests, [])
        self.check_path()
        self.assertEqual(self.path_requests, [API + 'real/file.py?ref=' + SHA])


if __name__ == '__main__':
    unittest.main()
