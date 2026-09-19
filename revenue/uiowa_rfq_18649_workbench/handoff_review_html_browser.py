#!/usr/bin/env python3
"""Exercise the actual generated reader in Chromium, preserving execution scope.

Default native mode opens a generated local HTML file. Component mode explicitly
uses an in-memory document and does NOT establish native file navigation. Browser
launch/navigation failures fail the run; missing Playwright is never a skipped pass.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from playwright.sync_api import sync_playwright
import handoff_review as hr
import handoff_review_html as view
from test_handoff_review_html import real_inputs

OPTIONS=None


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play=sync_playwright().start()
        cls.browser=cls.play.chromium.launch(executable_path=OPTIONS.browser,headless=True,args=['--no-sandbox'])
        cls.version=cls.browser.version
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        cls.report,cls.drafts=real_inputs()
        cls.html=view.build_html(cls.report,cls.drafts,classification='SYNTHETIC_REHEARSAL')
        (cls.root/'reader.html').write_text(cls.html,encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.play.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1280,'height':900},accept_downloads=True)
        self.context.set_default_timeout(5000)
        self.addCleanup(self.context.close)
        self.page=self.context.new_page()
        self.errors=[]
        self.requests=[]
        self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.page.on('request',lambda req:self.requests.append(req.url))
        self.load(self.page,self.html)

    def load(self,page,text,*,name='reader.html'):
        if OPTIONS.mode=='native':
            path=self.root/name
            path.write_text(text,encoding='utf-8')
            page.goto(path.as_uri(),wait_until='load',timeout=10000)
        else:
            page.set_content(text,wait_until='load')

    def visible(self):
        return self.page.locator('.cell:visible').count()

    def test_filter_counts_and_pressed_states(self):
        self.assertEqual(self.visible(),12)
        for name,count in [('Pending review',11),('Disagreement',1),('Unreviewed',9),('All cells',12)]:
            button=self.page.get_by_role('button',name=name,exact=True)
            button.click()
            self.assertEqual(self.visible(),count,name)
            self.assertEqual(button.get_attribute('aria-pressed'),'true')
            self.assertIn(f'{count} of 12',self.page.locator('#filter-status').inner_text())

    def test_group_search_and_clear(self):
        self.page.get_by_label('Group',exact=True).select_option('ESS')
        self.assertEqual(self.visible(),4)
        self.page.get_by_label('Search notes, labels and sources').fill('owner record not supplied')
        self.assertEqual(self.visible(),1)
        self.page.get_by_label('Search notes, labels and sources').fill('not-present-in-fixture')
        self.assertEqual(self.visible(),0)
        self.page.get_by_role('button',name='Clear filters').click()
        self.assertEqual(self.visible(),12)

    def test_keyboard_only_reaches_and_operates_filters(self):
        for _ in range(4):
            self.page.keyboard.press('Tab')
        self.assertEqual(self.page.locator(':focus').inner_text(),'Disagreement')
        self.page.keyboard.press('Enter')
        self.assertEqual(self.visible(),1)
        self.assertEqual(self.page.locator(':focus').inner_text(),'Disagreement')
        outline=self.page.locator(':focus').evaluate('(e)=>getComputedStyle(e).outlineWidth')
        self.assertEqual(outline,'3px')

    def test_index_restores_hidden_target_and_focus(self):
        self.page.get_by_role('button',name='Disagreement',exact=True).click()
        self.page.get_by_role('link',name='IAM / AI readiness',exact=True).click()
        self.page.wait_for_function("document.activeElement.textContent==='IAM / AI readiness'")
        self.assertEqual(self.visible(),12)
        self.assertEqual(self.page.locator(':focus').inner_text(),'IAM / AI readiness')
        self.assertEqual(self.page.locator('#missing-target').is_visible(),False)

    def test_unknown_anchor_is_diagnosed_not_invented(self):
        self.page.evaluate("location.hash='cell-unknown'")
        self.page.wait_for_function("!document.getElementById('missing-target').hidden")
        self.assertIn('not present',self.page.locator('#missing-target').inner_text())
        self.assertEqual(self.visible(),12)

    def test_download_retains_exact_engine_bytes(self):
        expected=hr.canonical(hr.reconcile(self.report,self.drafts))+b'\n'
        with self.page.expect_download(timeout=10000) as event:
            self.page.get_by_role('link',name='Download exact reconciliation JSON').click()
        destination=self.root/'download.json'
        event.value.save_as(destination)
        self.assertEqual(destination.read_bytes(),expected)

    def test_literal_multiline_unicode_notes(self):
        drafts=copy.deepcopy(self.drafts)
        note='FICTIONAL: <em>literal</em> & café 研究 🙂\nsecond line\tend'
        drafts[0][1]['cell_notes'][0]['analyst_note']=note
        self.load(self.page,view.build_html(self.report,drafts,classification='SYNTHETIC_REHEARSAL'),name='unicode.html')
        self.assertEqual(self.page.locator('#cell-ESS-software .note-text').first.text_content(),note)
        self.assertEqual(self.page.locator('em').count(),0)

    def test_small_and_large_viewports_do_not_overflow(self):
        for width in [320,480,1280]:
            self.page.set_viewport_size({'width':width,'height':900})
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
            self.assertEqual(self.visible(),12)

    def test_maximum_note_wraps_without_truncation(self):
        drafts=copy.deepcopy(self.drafts)
        note='N'*3999+'Z'
        drafts[0][1]['cell_notes'][0]['analyst_note']=note
        self.load(self.page,view.build_html(self.report,drafts,classification='SYNTHETIC_REHEARSAL'),name='long.html')
        self.page.set_viewport_size({'width':320,'height':900})
        self.assertEqual(self.page.locator('#cell-ESS-software .note-text').first.text_content(),note)
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),320)

    def test_print_includes_hidden_cells(self):
        self.page.get_by_role('button',name='Disagreement',exact=True).click()
        self.assertEqual(self.visible(),1)
        self.page.emulate_media(media='print')
        self.assertEqual(self.visible(),12)
        self.assertFalse(self.page.locator('#reader-controls').is_visible())
        self.assertTrue(self.page.locator('.print-note').is_visible())

    def test_without_javascript_all_records_remain_readable(self):
        context=self.browser.new_context(java_script_enabled=False)
        self.addCleanup(context.close)
        page=context.new_page()
        self.load(page,self.html)
        self.assertEqual(page.locator('.cell:visible').count(),12)
        self.assertFalse(page.locator('#reader-controls').is_visible())
        self.assertEqual(page.locator('.note').count(),24)

    def test_duplicate_imports_never_look_like_twenty_independent_reviews(self):
        draft=copy.deepcopy(self.drafts[0][1])
        for row in draft['cell_notes']:
            row.update(disposition='TECHNICAL_DRAFT_NOTE',analyst_note='FICTIONAL: one draft.')
        drafts=[(f'copy-{i:02}',copy.deepcopy(draft)) for i in range(20)]
        self.load(self.page,view.build_html(self.report,drafts,classification='SYNTHETIC_REHEARSAL'),name='copies.html')
        self.assertEqual(self.page.locator('.stat strong').all_text_contents(),['20','1','12','12'])
        self.assertEqual(self.page.locator('.note').count(),240)
        self.page.get_by_role('button',name='Pending review',exact=True).click()
        self.assertEqual(self.visible(),12)

    def test_monochrome_keeps_literal_reason_labels(self):
        self.page.emulate_media(forced_colors='active')
        self.page.get_by_role('button',name='Disagreement',exact=True).click()
        self.assertIn('DISPOSITION_DISAGREEMENT',self.page.locator('.cell:visible').inner_text())
        self.assertIn('Pending review',self.page.locator('.cell:visible .state').inner_text())

    def test_no_script_errors_or_network_fetches(self):
        self.page.get_by_role('button',name='Pending review',exact=True).click()
        self.assertEqual(self.errors,[])
        self.assertFalse(any(url.startswith(('http:','https:')) for url in self.requests))
        self.assertEqual(self.page.locator('script').count(),1)


def main():
    global OPTIONS
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('native','component'),default='native')
    parser.add_argument('--browser',default='/usr/bin/chromium')
    parser.add_argument('--receipt',type=Path,help='New execution receipt; never overwritten')
    OPTIONS=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(BrowserTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    ok=result.wasSuccessful() and result.testsRun==14 and not result.skipped
    record={'mode':OPTIONS.mode,'native_file_navigation_tested':OPTIONS.mode=='native',
            'status':'PASS' if ok else 'FAIL','tests_run':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),
            'browser_version':getattr(BrowserTests,'version',None),
            'renderer_sha256':hashlib.sha256(Path(view.__file__).read_bytes()).hexdigest(),
            'generated_html_sha256':hashlib.sha256(getattr(BrowserTests,'html','').encode()).hexdigest()}
    if OPTIONS.receipt:
        hr._write_new(OPTIONS.receipt,(json.dumps(record,indent=2)+'\n').encode())
    print(json.dumps(record,sort_keys=True))
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main())
