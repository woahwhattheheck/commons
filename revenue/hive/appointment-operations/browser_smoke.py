"""Optional real Chromium workflow test. Requires Playwright and its Chromium build."""
import json
import os
import shutil
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright
from desk import Desk, handler_for
from test_desk import CONTACTS, AVAIL


def main():
    with tempfile.TemporaryDirectory() as tmp:
        desk = Desk(Path(tmp) / 'browser.sqlite3')
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(desk))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or shutil.which('chromium'), args=['--no-sandbox'])
                page = browser.new_page(viewport={'width': 1280, 'height': 900})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(url)
                page.wait_for_function("document.querySelector('#status').textContent.startsWith('Ready.')")
                page.fill('#campaignName', 'Fictional operations walkthrough')
                page.fill('#offer', 'A walkthrough of the supplied operations workflow.')
                page.fill('#offerSource', 'fictional-offer-01')
                page.click('#campaignForm button')
                page.wait_for_function("document.querySelector('#status').textContent==='Campaign created.'")
                page.fill('#contactsCSV', CONTACTS)
                page.click('#importForm button')
                page.wait_for_selector('#prospects button')
                page.click('#prospects button')
                page.click('#starter')
                assert 'supplied operations workflow' in page.input_value('#draftBody')
                page.fill('#draftBody', 'Fictional, reviewed message. Nothing is sent.')
                page.check('#reviewed')
                page.click('#draftForm button:not([type=button])')
                page.wait_for_function("document.querySelector('#status').textContent==='Draft saved. Nothing sent.'")
                with urlopen(url + '/drafts.csv') as r:
                    assert b'alex@example.test' in r.read()
                page.fill('#replyBody', 'Fictional actual reply fixture: interested; source example-message-01.')
                page.click('#replyForm button')
                page.wait_for_function("document.querySelector('#status').textContent.startsWith('Actual reply recorded')")
                page.fill('#availabilityCSV', AVAIL)
                page.click('#availabilityForm button')
                page.wait_for_function("document.querySelector('#status').textContent.startsWith('Imported availability replaced')")
                page.fill('#start', '2035-09-10T09:00:00-05:00')
                page.fill('#end', '2035-09-10T09:30:00-05:00')
                page.fill('#confirmation', 'Fictional exact-slot confirmation; example-message-02.')
                page.click('#bookForm button')
                page.wait_for_function("document.querySelector('#status').textContent.startsWith('Local appointment created')")
                with page.expect_download() as downloaded:
                    page.click('#bookings a')
                calendar = Path(downloaded.value.path()).read_bytes()
                assert b'DTSTART:20350910T140000Z' in calendar
                assert b'ATTENDEE' not in calendar
                page.fill('#reason', 'Fictional later opt-out.')
                page.click('#suppressForm button')
                page.wait_for_function("document.querySelector('#status').textContent.startsWith('Suppressed across')")
                assert page.locator('#bookings a').count() == 0
                assert 'SUPPRESSED' in page.locator('#prospects').inner_text()
                page.click('#bookings button')
                page.wait_for_function("document.querySelector('#status').textContent.startsWith('Canceled locally')")
                page.reload()
                page.wait_for_function("document.querySelector('#status').textContent.startsWith('Ready.')")
                assert 'cancelled' in page.locator('#bookings').inner_text()
                page.set_viewport_size({'width': 390, 'height': 844})
                page.wait_for_timeout(100)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'mobile page overflows viewport'
                assert not errors, errors
                if os.environ.get('SCREENSHOT_DIR'):
                    out = Path(os.environ['SCREENSHOT_DIR'])
                    out.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(out / 'mobile.png'), full_page=True)
                    page.set_viewport_size({'width': 1280, 'height': 900})
                    page.screenshot(path=str(out / 'desktop.png'), full_page=True)
                result = desk.state()
                assert len(result['bookings']) == 1
                assert result['bookings'][0]['state'] == 'cancelled'
                assert len(result['suppressions']) == 1
                print(json.dumps({'browser': browser.version, 'desktop_workflow': 'PASS', 'mobile_390px': 'PASS', 'reload_persistence': 'PASS', 'page_errors': errors, 'bookings': len(result['bookings']), 'provider_updates': 0}))
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    main()
