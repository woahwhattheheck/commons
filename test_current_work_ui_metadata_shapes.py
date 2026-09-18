"""Offline Chromium checks for JSON metadata isolation in the existing viewer."""
from copy import deepcopy
from pathlib import Path
import shutil
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parent
DOM = '''<!doctype html><html lang="en"><meta charset="utf-8"><body>
<input id="cw-search" type="search" aria-label="Search work">
<select id="cw-kind" aria-label="Work kind"><option value="">All kinds</option>
<option value="BUILDABLE">Buildable</option><option value="OWNER_PLATFORM">Owner</option>
<option value="DEVICE_PINNED">Pinned</option></select>
<button id="cw-refresh">Refresh from main</button><p id="cw-source"></p>
<p id="cw-count"></p><div id="cw-items"></div></body></html>'''
FIELDS = ('id', 'title', 'from', 'kind', 'acceptance', 'notes')
BAD_OBJECT = {'toString': None, 'valueOf': None}
GOOD = {'id': 'good-01', 'title': 'Valid work', 'from': 'Builder',
        'kind': 'BUILDABLE', 'claimed_paths': ['src/good.py'],
        'acceptance': 'Acceptance phrase', 'notes': 'Useful notes'}


@unittest.skipIf(sync_playwright is None, 'optional Playwright package not installed')
class CurrentWorkMetadataBrowser(unittest.TestCase):
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
        self.network = []

    def tearDown(self):
        if self.context:
            self.context.close()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.network, [])

    def boot(self, items, *, schema='commons-current-work-v1', status=200):
        if self.context:
            self.context.close()
        self.context = self.browser.new_context()
        self.context.route('**/*', lambda route: (self.network.append(route.request.url), route.abort()))
        self.page = self.context.new_page()
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.set_content(DOM)
        self.page.evaluate('''data => {
          window.module = {exports:{}};
          window.items = data.items;
          window.schema = data.schema;
          window.testStatus = data.status;
          window.testSHA = 'a'.repeat(40);
          window.requests = [];
          window.pathRequests = 0;
          window.fetch = async (url, options = {}) => {
            window.requests.push({url, method:options.method || 'GET'});
            if (url.endsWith('/git/ref/heads/main')) {
              return new Response(JSON.stringify({object:{sha:window.testSHA}}), {status:window.testStatus});
            }
            if (url.includes('/contents/ground/CURRENT_WORK.json?')) {
              window.sentCatalog = JSON.stringify({schema:window.schema, items:window.items});
              const bytes = new TextEncoder().encode(window.sentCatalog);
              const content = btoa(Array.from(bytes, byte => String.fromCharCode(byte)).join(''));
              return new Response(JSON.stringify({encoding:'base64', content}));
            }
            window.pathRequests++;
            if (window.holdPaths) return new Promise(resolve => {
              window.finishPath = code => resolve(new Response('{}', {status:code}));
            });
            return new Response('{}', {status:window.pathStatus || 200});
          };
        }''', {'items': items, 'schema': schema, 'status': status})
        self.page.add_script_tag(content=(ROOT / 'current_work_ui.js').read_text(encoding='utf-8'))
        self.page.evaluate('''async () => {
          window.viewer = window.module.exports.mount(document, window.fetch);
          await window.viewer.ready;
        }''')
        return self.page.locator('#cw-source').inner_text()

    def assert_loaded(self, count):
        self.assertTrue(self.page.locator('#cw-source').inner_text().startswith('Observed main '),
                        self.page.locator('#cw-source').inner_text())
        self.assertEqual(self.page.locator('#cw-items article').count(), count)
        self.assertEqual(self.page.locator('#cw-count').inner_text(), f'{count} of {count} ledger items')
        self.assertTrue(self.page.evaluate("window.requests.every(r => r.method === 'GET')"))

    def card(self, title='Valid work'):
        return self.page.locator('#cw-items article').filter(
            has=self.page.get_by_role('heading', name=title, exact=True))

    def test_each_noncoercible_metadata_field_cannot_hide_other_rows(self):
        for field in FIELDS:
            with self.subTest(field=field):
                bad = {**deepcopy(GOOD), 'id': 'bad-01', 'title': 'Malformed metadata'}
                bad[field] = deepcopy(BAD_OBJECT)
                self.boot([GOOD, bad])
                self.assert_loaded(2)
                self.assertEqual(self.card().count(), 1)
                self.assertIn('Invalid text fields: ' + field, self.page.locator('#cw-items').inner_text())
                self.assertEqual(self.page.evaluate('window.pathRequests'), 0)

    def test_arrays_and_scalars_are_not_silently_coerced_to_metadata(self):
        for field in FIELDS:
            for value in ([BAD_OBJECT], {'nested': 'not text'}, 123, True):
                with self.subTest(field=field, value=value):
                    bad = {**deepcopy(GOOD), 'id': 'bad-01', 'title': 'Malformed metadata'}
                    bad[field] = deepcopy(value)
                    self.boot([GOOD, bad])
                    self.assert_loaded(2)
                    body = self.page.locator('#cw-items article').nth(1).inner_text()
                    self.assertIn('Invalid text fields: ' + field, body)
                    self.assertNotIn('[object Object]', body)

    def test_nonobject_rows_remain_visible_as_invalid(self):
        self.boot([GOOD, None, 0, False, 'plain string', [BAD_OBJECT]])
        self.assert_loaded(6)
        self.assertEqual(self.page.get_by_role('heading', name='Invalid ledger row', exact=True).count(), 5)
        self.assertEqual(self.page.get_by_role('status').filter(has_text='INVALID ROW').count(), 5)
        self.assertEqual(self.page.locator('#cw-items button').count(), 1)

    def test_every_valid_text_field_and_claimed_path_remains_searchable(self):
        for query in ('good-01', 'valid work', 'builder', 'buildable', 'acceptance phrase', 'useful notes', 'src/good.py'):
            with self.subTest(query=query):
                self.boot([GOOD, {'id': 'other', 'title': 'Other work', 'kind': 'DEVICE_PINNED'}])
                self.page.locator('#cw-search').fill(query)
                self.assertEqual(self.page.locator('#cw-count').inner_text(), '1 of 2 ledger items')
                self.assertEqual(self.card().count(), 1)
                self.assertEqual(self.page.evaluate('window.pathRequests'), 0)

    def test_nested_metadata_does_not_become_search_text_or_mutate_catalog(self):
        bad = {**deepcopy(GOOD), 'id': 'bad-01', 'title': 'Malformed metadata',
               'notes': {'nested': 'should-not-be-indexed', **BAD_OBJECT}}
        self.boot([GOOD, bad])
        self.assert_loaded(2)
        self.page.locator('#cw-search').fill('should-not-be-indexed')
        self.assertEqual(self.page.locator('#cw-count').inner_text(), '0 of 2 ledger items')
        self.page.locator('#cw-search').fill('malformed')
        self.assertEqual(self.page.locator('#cw-count').inner_text(), '1 of 2 ledger items')
        self.assertEqual(self.page.evaluate('window.items[1].notes'), bad['notes'])
        self.assertTrue(self.page.evaluate('JSON.stringify({schema:window.schema, items:window.items}) === window.sentCatalog'))

    def test_valid_path_check_keeps_bad_metadata_row_and_snapshot(self):
        bad = {**deepcopy(GOOD), 'title': 'Malformed metadata', 'from': deepcopy(BAD_OBJECT), 'claimed_paths': []}
        self.boot([GOOD, bad])
        self.assert_loaded(2)
        self.assertIn('UNVERIFIED', self.card().inner_text())
        self.card().get_by_role('button').click()
        self.page.wait_for_function("document.querySelector('#cw-items').textContent.includes('CLOSED')")
        self.assert_loaded(2)
        self.assertIn('OPEN', self.card('Malformed metadata').inner_text())
        self.assertEqual(self.page.evaluate('window.pathRequests'), 1)
        self.assertTrue(self.page.evaluate("window.requests.every(r => r.url.includes('ref=' + testSHA) || r.url.endsWith('/git/ref/heads/main'))"))

    def test_pending_check_filtering_preserves_focus_and_open_details(self):
        bad = {**deepcopy(GOOD), 'title': 'Malformed metadata', 'notes': deepcopy(BAD_OBJECT), 'claimed_paths': []}
        self.boot([GOOD, bad])
        self.assert_loaded(2)
        self.card().locator('summary').click()
        self.page.evaluate('window.holdPaths = true')
        self.card().get_by_role('button').focus()
        self.page.keyboard.press('Enter')
        self.page.wait_for_function("typeof window.finishPath === 'function'")
        self.assertEqual(self.page.evaluate('document.activeElement.textContent'), 'Checking paths…')
        self.assertTrue(self.card().locator('details').evaluate('node => node.open'))
        self.page.locator('#cw-search').fill('valid work')
        self.page.evaluate('window.finishPath(200)')
        self.page.wait_for_function("document.querySelector('#cw-items').textContent.includes('CLOSED')")
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'cw-search')
        self.assertTrue(self.card().locator('details').evaluate('node => node.open'))
        self.page.locator('#cw-search').fill('')
        self.assert_loaded(2)

    def test_refresh_can_replace_malformed_metadata_without_stale_diagnostics(self):
        bad = {**deepcopy(GOOD), 'title': 'Malformed metadata', 'notes': deepcopy(BAD_OBJECT)}
        self.boot([GOOD, bad])
        self.assert_loaded(2)
        self.page.evaluate("window.items[1].notes = 'Recovered notes'; window.testSHA = 'b'.repeat(40)")
        self.page.evaluate('async () => { await window.viewer.reload(); }')
        self.assert_loaded(2)
        self.assertNotIn('Invalid text fields:', self.page.locator('#cw-items').inner_text())
        self.assertIn('Recovered notes', self.card('Malformed metadata').inner_text())
        self.assertIn('b' * 40, self.page.locator('#cw-source').inner_text())
        self.assertEqual(self.page.evaluate('window.pathRequests'), 0)

    def test_actual_fetch_or_schema_error_is_still_unavailable(self):
        for options in ({'schema': 'bad-schema'}, {'status': 429}):
            with self.subTest(options=options):
                status = self.boot([GOOD], **options)
                self.assertTrue(status.startswith('Ledger unavailable:'))
                self.assertEqual(self.page.locator('#cw-items article').count(), 0)
                self.assertEqual(self.page.locator('#cw-count').inner_text(), '')

    def test_invalid_kind_or_path_does_not_gain_a_check_button(self):
        self.boot([GOOD, {**GOOD, 'title': 'Bad kind', 'kind': BAD_OBJECT},
                   {**GOOD, 'title': 'Bad path', 'claimed_paths': [BAD_OBJECT]}])
        self.assert_loaded(3)
        for title in ('Bad kind', 'Bad path'):
            self.assertIn('INVALID ROW', self.card(title).inner_text())
            self.assertEqual(self.card(title).locator('button').count(), 0)
        self.assertEqual(self.page.evaluate('window.pathRequests'), 0)

    def test_unicode_and_markup_remain_literal_text(self):
        title = 'Résumé <img src=x onerror=alert(1)> 🧪'
        item = {**GOOD, 'title': title, 'from': 'Zoë', 'notes': '<script>window.bad=true</script>'}
        self.boot([item])
        self.assert_loaded(1)
        self.assertEqual(self.page.locator('#cw-items h3').inner_text(), title)
        self.assertEqual(self.page.locator('#cw-items img, #cw-items script').count(), 0)
        self.page.locator('#cw-search').fill('résumé')
        self.assert_loaded(1)

    def test_empty_and_missing_text_preserve_existing_placeholders(self):
        self.boot([{'id': '', 'title': '', 'kind': 'BUILDABLE', 'from': None, 'claimed_paths': []},
                   {'kind': 'OWNER_PLATFORM'}, {'kind': 'DEVICE_PINNED'}])
        self.assert_loaded(3)
        self.assertIn('(missing id) · BUILDABLE · From: unspecified', self.page.locator('#cw-items').inner_text())
        self.assertNotIn('Invalid text fields:', self.page.locator('#cw-items').inner_text())
        self.assertEqual([s.inner_text() for s in self.page.get_by_role('status').all()], ['OPEN', 'NEEDS_OWNER', 'PINNED'])


if __name__ == '__main__':
    unittest.main()
