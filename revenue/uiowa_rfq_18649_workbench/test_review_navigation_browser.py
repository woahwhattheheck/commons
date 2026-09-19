"""UIOWA-128 real-Chromium integration of the existing UI-only demonstration.

Requires Playwright + Chromium. Uses the actual workbench HTTP handler and browser
assets by default. Set UIOWA_NAV_DOM_ONLY=1 for managed browsers that disallow URL
navigation: this explicitly renders local asset bytes and captures export bytes
without network navigation or downloads; it does NOT count as HTTP/download proof.
The compiler is NOT called or simulated. No hosted-CI claim is implied.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from playwright.sync_api import sync_playwright, expect
from server import create_server, WorkbenchError

ROOT = Path(__file__).resolve().parent
# Explicit local-content test mode does not navigate around a URL blocklist.
# It renders known local bytes directly; HTTP delivery/download coverage is separate.
DOM_ONLY = os.environ.get('UIOWA_NAV_DOM_ONLY') == '1' 

class NoCompiler:
    def inspect(self, candidate, authority):
        raise WorkbenchError('This UI-only navigation test does not invoke the compiler.')

class NavigationBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = create_server(port=0, adapter=NoCompiler(), static_root=ROOT)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:%d/' % cls.httpd.server_address[1]
        print('BROWSER_MODE=' + ('LOCAL_CONTENT_NO_HTTP_NO_DOWNLOAD' if DOM_ONLY else 'HTTP'))
        cls.pw = sync_playwright().start()
        executable = os.environ.get('CHROMIUM_PATH') or shutil.which('chromium')
        cls.browser = cls.pw.chromium.launch(executable_path=executable, headless=True, args=['--no-sandbox'])
        cls.temp = tempfile.TemporaryDirectory(prefix='uiowa128-')

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()
        cls.httpd.shutdown(); cls.httpd.server_close(); cls.thread.join(timeout=5)
        cls.temp.cleanup()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':1280,'height':900}, color_scheme='light')
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda e:self.errors.append(str(e)))
        self.load_workbench()
        self.page.locator('#demoBtn').click()
        self.page.locator('#reviewDemoBtn').click()
        self.packet = self.page.evaluate('UIowaReviewNavigation.syntheticPacket()')

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def load_workbench(self):
        if not DOM_ONLY:
            self.page.goto(self.base)
            return
        html = (ROOT / 'index.html').read_text()
        html = re.sub(r'<link[^>]+rel="stylesheet"[^>]*>', '', html)
        html = re.sub(r'<script[^>]*src="[^"]+"[^>]*></script>', '', html)
        self.page.set_content(html)
        for name in ('style.css', 'review_navigation.css'):
            self.page.add_style_tag(content=(ROOT / name).read_text())
        for name in ('review_navigation.js', 'app.js'):
            self.page.add_script_tag(content=(ROOT / name).read_text())

    def reload_workbench(self):
        self.page.reload()
        if DOM_ONLY:
            self.load_workbench()

    def status(self, name):
        expect(self.page.locator('#reviewStatus')).to_have_attribute('data-state', name)

    def comment(self):
        self.page.locator('#reviewQueue a').last.click()
        self.status('FOUND')
        expect(self.page.locator('#reviewDetail h3')).to_contain_text('COMMENT-SYN-128/é + #1')

    def upload(self, packet):
        self.page.locator('#reviewFile').set_input_files({'name':'review.json','mimeType':'application/json','buffer':json.dumps(packet,ensure_ascii=False).encode()})

    def test_exact_chain_keyboard_and_cell_selection(self):
        link = self.page.locator('#reviewQueue a').last
        link.focus(); self.page.keyboard.press('Enter'); self.status('FOUND')
        expect(self.page.locator('#reviewDetail')).to_be_focused()
        expect(self.page.locator('#detail')).to_contain_text('software_development')
        expect(self.page.locator('#detail')).to_contain_text('ESS')
        for kind in ['recommendation','finding','source']:
            self.page.locator('#reviewDetail ul a').first.click()
            self.status('FOUND')
            expect(self.page.locator('#reviewDetail h3')).to_contain_text(kind)
        expect(self.page.locator('#reviewDetail')).to_contain_text('does not contain the source document')
        self.assertNotEqual(self.page.locator('#reviewCurrentLink').input_value(), '')

    def test_reload_then_matching_import_reopens_same_record(self):
        self.comment(); saved = self.page.url
        self.reload_workbench(); self.status('WAITING_FOR_REPORT')
        self.assertEqual(self.page.url, saved)
        self.page.locator('#demoBtn').click(); self.status('WAITING_FOR_RECORDS')
        self.upload(self.packet); self.status('FOUND')
        expect(self.page.locator('#reviewDetail h3')).to_contain_text('COMMENT-SYN-128/é + #1')
        self.assertEqual(self.page.url, saved)

    def test_source_route_survives_without_extra_packet(self):
        self.page.locator('#reviewSources summary').click()
        self.page.locator('#reviewSourceQueue a').first.click(); self.status('FOUND')
        self.reload_workbench(); self.status('WAITING_FOR_REPORT')
        self.page.locator('#demoBtn').click(); self.status('FOUND')
        expect(self.page.locator('#reviewDetail h3')).to_contain_text('source')

    def test_same_receipt_reimport_clears_records_and_notes(self):
        self.comment(); self.page.locator('#note').fill('draft note retained only for this generation')
        self.page.locator('#demoBtn').click(); self.status('WAITING_FOR_RECORDS')
        expect(self.page.locator('#note')).to_be_disabled()
        self.assertEqual(self.page.locator('#note').input_value(),'')
        expect(self.page.locator('#reviewPacketBtn')).to_be_disabled()
        self.page.locator('#reviewDemoBtn').click(); self.status('FOUND')
        self.assertEqual(self.page.locator('#note').input_value(),'')

    def test_wrong_report_and_missing_revision_do_not_show_stale_selection(self):
        self.comment()
        self.page.evaluate("installReport({...syntheticReport(),receipt_sha256:'a'.repeat(64)})")
        self.status('REPORT_MISMATCH')
        expect(self.page.locator('#note')).to_be_disabled()
        expect(self.page.locator('#detail')).to_contain_text('No cell selected')
        self.page.locator('#demoBtn').click();self.page.locator('#reviewDemoBtn').click()
        self.page.evaluate("location.hash=UIowaReviewNavigation.routeFor('d'.repeat(64),{...UIowaReviewNavigation.syntheticPacket().records[2],revision:'missing-v2'})")
        self.status('MISSING_RECORD')
        expect(self.page.locator('#reviewDetail')).to_contain_text('available_versions_not_substituted')
        expect(self.page.locator('#note')).to_be_disabled()

    def test_duplicate_reference_diagnosed_and_invalid_import_invalidates_old(self):
        self.comment(); p=json.loads(json.dumps(self.packet));p['records'].append(p['records'][2].copy())
        self.upload(p); self.status('AMBIGUOUS_RECORD')
        expect(self.page.locator('#reviewDetail h3')).to_have_count(0)
        self.page.locator('#reviewFile').set_input_files({'name':'broken.json','mimeType':'application/json','buffer':b'{broken'})
        expect(self.page.locator('#reviewError')).not_to_be_empty()
        self.status('WAITING_FOR_RECORDS')
        expect(self.page.locator('#reviewPacketBtn')).to_be_disabled()

    def test_replacement_during_async_file_read_cannot_resurrect_stale_records(self):
        self.comment()
        self.page.evaluate("""() => {
          window.releaseRead=null;
          File.prototype.text=function(){return new Promise(resolve=>{window.releaseRead=resolve})};
        }""")
        self.upload(self.packet)
        self.page.wait_for_function('window.releaseRead !== null')
        self.page.locator('#resetBtn').click();self.status('WAITING_FOR_REPORT')
        self.page.evaluate('(p)=>window.releaseRead(JSON.stringify(p))', self.packet)
        self.page.wait_for_timeout(50)
        self.status('WAITING_FOR_REPORT')
        expect(self.page.locator('#reviewQueue a')).to_have_count(0)
        expect(self.page.locator('#reviewPacketBtn')).to_be_disabled()

    def test_exports_round_trip_and_every_guide_link_opens(self):
        self.comment()
        packet_path=Path(self.temp.name)/'packet.json'
        guide_path=Path(self.temp.name)/'guide.html'
        if DOM_ONLY:
            # Observe bytes generated by the real export button without initiating a download.
            self.page.evaluate("""() => {
              const original=URL.createObjectURL;
              URL.createObjectURL=blob=>{window.testExportBlob=blob; return original(blob)};
              const click=HTMLAnchorElement.prototype.click;
              HTMLAnchorElement.prototype.click=function(){if(!this.download)click.call(this)};
            }""")
            self.page.locator('#reviewPacketBtn').click()
            packet_path.write_text(self.page.evaluate('window.testExportBlob.text()'))
            self.page.locator('#reviewGuideBtn').click()
            guide_path.write_text(self.page.evaluate('window.testExportBlob.text()'))
            self.page.set_content(guide_path.read_text())
        else:
            with self.page.expect_download() as event: self.page.locator('#reviewPacketBtn').click()
            event.value.save_as(packet_path)
            with self.page.expect_download() as event: self.page.locator('#reviewGuideBtn').click()
            event.value.save_as(guide_path)
            self.page.goto(guide_path.as_uri())
        self.assertEqual(json.loads(packet_path.read_text()),self.packet)
        self.assertEqual(self.page.locator('section').count(),15)
        bad = self.page.locator('a').evaluate_all("as=>as.filter(a=>!document.getElementById(decodeURIComponent(a.hash.slice(1)))).map(a=>a.href)")
        self.assertEqual(bad,[])
        anchors=self.page.locator('#review-index a'); count=anchors.count()
        for i in range(count):
            anchor=anchors.nth(i); expected=anchor.inner_text();anchor.click()
            heading=self.page.evaluate("document.getElementById(decodeURIComponent(location.hash.slice(1))).querySelector('h2').textContent")
            self.assertEqual(heading,expected)
        self.page.reload()
        if DOM_ONLY: self.page.set_content(guide_path.read_text())
        expect(self.page.locator(':target h2')).to_contain_text('COMMENT-SYN-128/é + #1')
        output=os.environ.get('UIOWA_NAV_CAPTURE_DIR')
        if output:
            path=Path(output);path.mkdir(parents=True,exist_ok=True)
            shutil.copy2(guide_path,path/'synthetic-linked-review-guide.html')
            shutil.copy2(packet_path,path/'synthetic-review-navigation.json')

    def test_literal_text_is_not_markup(self):
        p=json.loads(json.dumps(self.packet));p['records'][2]['text']='<b data-test="literal">Not markup & not a link</b>'
        self.upload(p);self.comment()
        expect(self.page.locator('#reviewDetail')).to_contain_text('<b data-test="literal">')
        expect(self.page.locator('#reviewDetail b')).to_have_count(0)

    def test_visual_views_and_navigation_panel_overflow(self):
        self.comment()
        out=Path(os.environ.get('UIOWA_NAV_CAPTURE_DIR',self.temp.name));out.mkdir(parents=True,exist_ok=True)
        for width in (1280,390):
            self.page.set_viewport_size({'width':width,'height':900})
            self.page.locator('#review-navigation').scroll_into_view_if_needed()
            # Scope the layout assertion to this feature; the matrix presentation has another owner.
            overflow=self.page.locator('#review-navigation').evaluate('(e)=>e.scrollWidth>e.clientWidth+1')
            self.assertFalse(overflow, f'navigation overflow at {width}px')
            self.page.locator('#review-navigation').screenshot(path=str(out/f'review-navigation-{width}.png'))

if __name__=='__main__': unittest.main(verbosity=2)
