"""Real offline Chromium regressions for current-work disclosure state."""
from pathlib import Path
import shutil
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parent
DOM = """<!doctype html><html lang="en"><meta charset="utf-8"><body>
<input id="cw-search" type="search" aria-label="Search work">
<select id="cw-kind" aria-label="Work kind"><option value="">All kinds</option>
<option value="BUILDABLE">Buildable</option>
<option value="DEVICE_PINNED">Device pinned</option></select>
<button id="cw-refresh">Refresh from main</button><p id="cw-source"></p>
<p id="cw-count"></p><div id="cw-items"></div></body></html>"""


@unittest.skipIf(sync_playwright is None, "optional Playwright package not installed")
class CurrentWorkDetailsBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = sync_playwright().start()
        try:
            cls.browser = cls.runtime.chromium.launch(
                headless=True, executable_path=shutil.which("chromium") or None)
        except Exception as error:
            cls.runtime.stop()
            raise unittest.SkipTest("Chromium unavailable: " + str(error).splitlines()[0])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.runtime.stop()

    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        # Only the existing viewer DOM contract is needed; no live page or HTTP.
        self.page.set_content(DOM)
        self.page.evaluate("""() => {
          window.testSHA = 'a'.repeat(40);
          window.pathRequests = 0;
          window.requests = [];
          const items = [
            {id:'same-work-01', title:'Alpha sources', kind:'BUILDABLE', claimed_paths:['alpha.py']},
            {id:'same-work-01', title:'Beta sources', kind:'BUILDABLE', claimed_paths:['beta.py']},
            {id:'device-work-01', title:'Device sources', kind:'DEVICE_PINNED', claimed_paths:['device.py']}
          ];
          window.fetch = async (url, options = {}) => {
            window.requests.push({url, method:options.method || 'GET'});
            if (url.endsWith('/git/ref/heads/main')) {
              return new Response(JSON.stringify({object:{sha:window.testSHA}}));
            }
            if (url.includes('/contents/ground/CURRENT_WORK.json?')) {
              return new Response(JSON.stringify({encoding:'base64',
                content:btoa(JSON.stringify({schema:'commons-current-work-v1', items}))}));
            }
            window.pathRequests++;
            if (window.holdPaths) return new Promise(resolve => {
              window.finishPath = status => resolve(new Response('{}', {status}));
            });
            return new Response('{}', {status:200});
          };
        }""")
        self.page.add_script_tag(content=(ROOT / "current_work_ui.js").read_text(encoding="utf-8"))
        self.page.wait_for_function("document.querySelector('#cw-count').textContent === '3 of 3 ledger items'")

    def tearDown(self):
        self.assertTrue(self.page.evaluate("window.requests.every(request => request.method === 'GET')"))
        self.context.close()
        self.assertEqual(self.errors, [])

    def card(self, name):
        return self.page.locator("#cw-items article").filter(has=self.page.get_by_role("heading", name=name, exact=True))

    def opened(self, name):
        return self.card(name).locator("details").evaluate("node => node.open")

    def open_details(self, name):
        self.card(name).locator("summary").click()
        self.assertTrue(self.opened(name))

    def test_search_preserves_open_and_explicitly_closed_details(self):
        self.open_details("Alpha sources")
        self.page.locator("#cw-search").fill("sources")
        self.assertTrue(self.opened("Alpha sources"))
        self.assertFalse(self.opened("Beta sources"))
        self.card("Alpha sources").locator("summary").click()
        self.page.locator("#cw-search").fill("alpha")
        self.assertFalse(self.opened("Alpha sources"))
        self.assertEqual(self.page.evaluate("window.pathRequests"), 0)

    def test_filtered_rows_keep_independent_state_even_with_duplicate_ids(self):
        self.open_details("Alpha sources")
        self.page.locator("#cw-search").fill("Beta")
        self.assertFalse(self.opened("Beta sources"))
        self.page.locator("#cw-search").fill("")
        self.assertTrue(self.opened("Alpha sources"))
        self.assertFalse(self.opened("Beta sources"))
        self.page.locator("#cw-kind").select_option("DEVICE_PINNED")
        self.page.locator("#cw-kind").select_option("")
        self.assertTrue(self.opened("Alpha sources"))
        self.assertFalse(self.opened("Beta sources"))

    def test_pending_failure_retry_and_success_keep_details_and_button_focus(self):
        self.open_details("Alpha sources")
        self.page.evaluate("window.holdPaths = true")
        for code in (429, 200):
            with self.subTest(code=code):
                self.page.evaluate("delete window.finishPath")
                self.card("Alpha sources").get_by_role("button").focus()
                self.page.keyboard.press("Enter")
                self.page.wait_for_function("typeof window.finishPath === 'function'")
                self.assertTrue(self.opened("Alpha sources"))
                self.assertEqual(self.page.evaluate("document.activeElement.textContent"), "Checking paths…")
                count = self.page.evaluate("window.pathRequests")
                self.page.keyboard.press("Enter")
                self.assertEqual(self.page.evaluate("window.pathRequests"), count)
                self.page.evaluate("code => window.finishPath(code)", code)
                self.page.wait_for_function("document.querySelector('#cw-items button').getAttribute('aria-disabled') === 'false'")
                self.assertTrue(self.opened("Alpha sources"))
                self.assertEqual(self.page.evaluate("document.activeElement.textContent"), "Check listed paths")
                outcome = self.card("Alpha sources").inner_text()
                self.assertIn("HTTP 429" if code == 429 else "CLOSED", outcome)
        self.assertEqual(self.page.evaluate("window.pathRequests"), 2)

    def test_other_row_completion_keeps_sources_open_without_stealing_search_focus(self):
        self.open_details("Alpha sources")
        self.page.evaluate("window.holdPaths = true")
        self.card("Beta sources").get_by_role("button").click()
        self.page.wait_for_function("typeof window.finishPath === 'function'")
        self.assertTrue(self.opened("Alpha sources"))
        self.page.locator("#cw-search").fill("sources")
        self.page.evaluate("window.finishPath(200)")
        self.page.wait_for_function("document.querySelector('#cw-items').textContent.includes('CLOSED')")
        self.assertTrue(self.opened("Alpha sources"))
        self.assertEqual(self.page.evaluate("document.activeElement.id"), "cw-search")

    def test_same_task_toggle_and_render_read_actual_dom_state(self):
        self.page.evaluate("""() => {
          document.querySelector('#cw-items details').open = true;
          document.querySelector('#cw-search').dispatchEvent(new Event('input'));
        }""")
        self.assertTrue(self.opened("Alpha sources"))
        self.page.evaluate("""() => {
          document.querySelector('#cw-items details').open = false;
          document.querySelector('#cw-search').dispatchEvent(new Event('input'));
        }""")
        self.assertFalse(self.opened("Alpha sources"))

    def test_refresh_starts_fresh_disclosure_state_and_source_snapshot(self):
        self.open_details("Alpha sources")
        self.page.evaluate("window.testSHA = 'b'.repeat(40)")
        self.page.locator("#cw-refresh").click()
        self.page.wait_for_function("document.querySelector('#cw-source').textContent.includes('b'.repeat(40))")
        self.assertFalse(self.opened("Alpha sources"))
        self.assertTrue(self.card("Alpha sources").locator("a").get_attribute("href").endswith("/" + "b" * 40 + "/alpha.py"))
        self.assertIn("UNVERIFIED", self.card("Alpha sources").inner_text())
        self.assertEqual(self.page.evaluate("window.pathRequests"), 0)

    def test_pinned_row_keeps_disclosure_without_adding_execution(self):
        self.open_details("Device sources")
        self.page.locator("#cw-kind").select_option("DEVICE_PINNED")
        self.assertTrue(self.opened("Device sources"))
        self.assertEqual(self.card("Device sources").locator("button").count(), 0)
        self.assertIn("PINNED", self.card("Device sources").inner_text())
        self.assertEqual(self.page.evaluate("window.pathRequests"), 0)


if __name__ == "__main__":
    unittest.main()
