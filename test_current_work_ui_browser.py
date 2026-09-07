"""Optional real-Chromium UI regression tests. Uses offline DOM content and fetch fixtures; no live HTTP."""
from pathlib import Path
import base64
import re
import json
import shutil
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parent
SHA = "a" * 40
API = "https://api.github.com/repos/woahwhattheheck/commons"


def work(kind="BUILDABLE", paths=None, title="Café work"):
    return {"id": "example-work-01", "title": title, "kind": kind,
            "from": "TEST", "claimed_paths": ["example.py"] if paths is None else paths}


@unittest.skipIf(sync_playwright is None, "optional Playwright package not installed")
class CurrentWorkBrowser(unittest.TestCase):
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
        self.context = self.browser.new_context(viewport={"width": 430, "height": 900})
        self.page = self.context.new_page()
        self.calls = []
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.items = [work(), work("OWNER_PLATFORM", [], "External step"), work("DEVICE_PINNED", title="Device remains pinned"), None]
        self.path_status = 200
        self.main_status = 200
        # Stay in about:blank: no domain, network policy changes, or live services.
        html = (ROOT / "current-work.html").read_text(encoding="utf-8")
        html = re.sub(r'<script\b[^>]*>.*?</script>|<link\b[^>]*>', '', html, flags=re.S)
        self.page.set_content(html)
        self.page.expose_function("fixtureResponse", self.reply)
        self.page.evaluate("""() => {
          window.fetch = async url => {
            const reply = await window.fixtureResponse(url);
            return new Response(JSON.stringify(reply.data), {status: reply.status});
          };
        }""")

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def reply(self, url):
        self.calls.append(("GET", url))
        if url == API + "/git/ref/heads/main":
            return {"status": self.main_status, "data": {"object": {"sha": SHA}}}
        if "/contents/ground/CURRENT_WORK.json?" in url:
            data = {"schema": "commons-current-work-v1", "items": self.items}
            encoded = base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()
            return {"status": 200, "data": {"encoding": "base64", "content": encoded}}
        if url.startswith(API + "/contents/"):
            return {"status": self.path_status, "data": {}}
        raise AssertionError("Unexpected fixture URL: " + url)

    def start(self):
        self.page.add_script_tag(content=(ROOT / "current_work_ui.js").read_text(encoding="utf-8"))

    def load(self):
        self.start()
        self.page.wait_for_function("document.querySelector('#cw-count').textContent === '4 of 4 ledger items'")

    def test_render_filter_safe_text_and_pinned_rows(self):
        self.items[0]["title"] = '<img src=x onerror="window.injected=true"> Café work'
        self.load()
        self.assertEqual(self.page.locator("#cw-items article").count(), 4)
        self.assertEqual(self.page.locator("#cw-items img").count(), 0)
        self.assertFalse(self.page.evaluate("Boolean(window.injected)"))
        self.page.locator("#cw-kind").select_option("DEVICE_PINNED")
        self.assertEqual(self.page.locator("#cw-items article").count(), 1)
        self.assertEqual(self.page.locator("#cw-items button").count(), 0)
        self.assertIn("PINNED", self.page.locator("#cw-items").inner_text())
        self.page.locator("#cw-kind").select_option("")
        self.page.locator("#cw-search").fill("café")
        self.assertEqual(self.page.locator("#cw-items article").count(), 1)
        self.assertTrue(self.page.locator("#cw-items a").first.get_attribute("href").endswith(f"/{SHA}/example.py"))
        self.assertTrue(all(method == "GET" for method, _ in self.calls))
        self.assertFalse(any("/contents/example.py?" in url for _, url in self.calls))

    def test_check_paths_and_retry_transport_failure(self):
        self.load()
        self.path_status = 429
        self.page.get_by_role("button", name="Check listed paths").click()
        self.page.wait_for_function("document.querySelector('#cw-items').textContent.includes('HTTP 429')")
        self.assertNotIn("CLOSED", self.page.locator("#cw-items").inner_text())
        self.path_status = 200
        self.page.get_by_role("button", name="Check listed paths").click()
        self.page.wait_for_function("document.querySelector('#cw-items').textContent.includes('CLOSED')")
        self.assertIn("not a test, payment, or live-service result", self.page.locator("#cw-items").inner_text())

    def test_unavailable_source_and_search_do_not_claim_empty_queue(self):
        self.main_status = 403
        self.start()
        self.page.wait_for_function("document.querySelector('#cw-source').textContent.includes('HTTP 403')")
        self.page.locator("#cw-search").fill("missing")
        self.assertEqual(self.page.locator("#cw-count").inner_text(), "")
        self.assertEqual(self.page.locator("#cw-items").inner_text(), "")
        self.assertIn("No empty-queue or completion claim", self.page.locator("#cw-source").inner_text())

    def test_refresh_ignores_an_older_request_even_if_transport_ignores_abort(self):
        self.page.evaluate("""() => {
          const oldSHA = 'a'.repeat(40), newSHA = 'b'.repeat(40);
          let refs = 0;
          window.fetch = async function(url) {
            if (url.endsWith('/git/ref/heads/main')) {
              if (++refs === 1) return new Promise(resolve => { window.releaseOld = () => resolve(new Response(JSON.stringify({object:{sha:oldSHA}}))); });
              return new Response(JSON.stringify({object:{sha:newSHA}}));
            }
            const catalog = {schema:'commons-current-work-v1', items:[{id:'new-work-01',title:url.includes(newSHA)?'New snapshot':'Old snapshot',kind:'BUILDABLE',claimed_paths:[]}]};
            return new Response(JSON.stringify({encoding:'base64',content:btoa(JSON.stringify(catalog))}));
          };
        }""")
        self.start()
        self.page.wait_for_function("typeof window.releaseOld === 'function'")
        self.page.locator("#cw-refresh").click()
        self.page.wait_for_function("document.querySelector('#cw-items').textContent.includes('New snapshot')")
        self.page.evaluate("window.releaseOld()")
        self.page.wait_for_timeout(50)
        self.assertIn("New snapshot", self.page.locator("#cw-items").inner_text())
        self.assertNotIn("Old snapshot", self.page.locator("#cw-items").inner_text())
        self.assertIn("b" * 40, self.page.locator("#cw-source").inner_text())


if __name__ == "__main__":
    unittest.main()
