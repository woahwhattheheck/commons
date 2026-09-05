"""Optional browser smoke: python repair-capsules/browser_smoke.py.

Requires Playwright Python plus Chromium. Uses only an ephemeral localhost server.
Set CHROMIUM_PATH to a system binary, or install Playwright's Chromium normally.
"""
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT))
    )
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    report = []
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        binary = os.environ.get("CHROMIUM_PATH") or shutil.which("chromium")
        browser = p.chromium.launch(headless=True, **({"executable_path": binary} if binary else {}))
        try:
            page = browser.new_page(viewport={"width": 1360, "height": 1080}, accept_downloads=True)
            errors, requests = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            page.goto(f"http://127.0.0.1:{server.server_port}/", wait_until="networkidle")
            assert page.title() == "Repair Capsules · Commons"
            assert page.locator("h1").is_visible()
            report.append("page loads; meaningful content")

            page.locator("#demo-commons").click()
            page.wait_for_function("document.querySelector('#json').textContent.includes('repair-capsule/1')")
            assert "demo-old" in page.locator("#diff").inner_text()
            assert "demo-new" in page.locator("#diff").inner_text()
            assert "Compare the page revision" in page.locator("#preview-next").inner_text()
            assert "DEMO_ONLY_NOT_A_REAL" not in page.locator("#json").inner_text()
            report.append("Commons demo: visible diff, next action, redaction")
            output_dir = os.environ.get("SMOKE_ARTIFACT_DIR")
            if output_dir:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(Path(output_dir) / "repair-capsules-desktop.png"), full_page=True)

            page.locator("#action").fill("Changed input path after checking directory")
            page.locator("#result").fill("Observed exit_code=0 token=history-secret")
            page.locator("#record").click()
            page.wait_for_function("document.querySelector('#status').textContent.startsWith('Intervention recorded')")
            assert "exit_code=0" in page.locator("#attempts").inner_text()
            with page.expect_download() as dl:
                page.locator("#export").click()
            path = Path(tmp) / "capsule.json"
            dl.value.save_as(path)
            exported = json.loads(path.read_text())
            assert len(exported["attempts"]) == 1
            assert "history-secret" not in path.read_text()
            report.append("record intervention and download redacted capsule")

            page.locator("#clear").click()
            assert page.locator("#title").input_value() == ""
            assert page.locator("#inspection").is_hidden()
            page.locator("#import").set_input_files(str(path))
            page.wait_for_function("document.querySelector('#status').textContent.startsWith('Imported checksum: MATCH')")
            assert "Changed input path" in page.locator("#attempts").inner_text()
            report.append("clear and reopen download; checksum MATCH and history preserved")

            exported["next_action"] = '<img src=x onerror="window.capsuleExecuted=true"> changed evidence'
            path.write_text(json.dumps(exported))
            page.locator("#import").set_input_files(str(path))
            page.wait_for_function("document.querySelector('#status').textContent.startsWith('Imported checksum: MISMATCH')")
            assert "changed evidence" in page.locator("#preview-next").inner_text()
            assert page.locator("#preview-next img").count() == 0
            assert page.evaluate("window.capsuleExecuted === undefined")
            report.append("tampered capsule remains inspectable; checksum MISMATCH; HTML inert")

            page.locator("#private").fill("do-not-share-42")
            page.locator("#title").fill("Failure do-not-share-42")
            page.locator("#preview").click()
            page.wait_for_function("document.querySelector('#preview-title').textContent === 'Failure [REDACTED]'")
            assert "do-not-share-42" not in page.locator("#json").inner_text()
            report.append("custom private literal stays out of export")

            page.locator("#known").uncheck()
            page.locator("#preview").click()
            page.wait_for_function("document.querySelector('#diff-note').textContent.includes('unknown')")
            page.locator("#known").check()
            page.locator("#good").fill("")
            page.locator("#preview").click()
            page.wait_for_function("!document.querySelector('#diff-note').textContent.includes('unknown')")
            assert page.locator("#diff .added").count() > 0
            report.append("unknown baseline differs from deliberately empty baseline")

            page.locator("#demo-command").click()
            page.wait_for_function("document.querySelector('#preview-title').textContent.includes('report command')")
            assert "./fixtures/input.csv" in page.locator("#preview-next").inner_text()
            report.append("non-Commons command demo exposes next repair")

            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            if output_dir:
                page.screenshot(path=str(Path(output_dir) / "repair-capsules-mobile.png"), full_page=True)
            report.append("390px mobile layout has no horizontal overflow")

            assert page.evaluate("localStorage.length === 0 && sessionStorage.length === 0")
            assert all(url.startswith(f"http://127.0.0.1:{server.server_port}/") for url in requests)
            assert not errors, errors
            report.append("no script errors, external requests, or automatic browser storage")

            offline = browser.new_page()
            offline.goto((ROOT / "index.html").as_uri())
            offline.locator("#demo-command").click()
            offline.wait_for_function("document.querySelector('#json').textContent.includes('repair-capsule/1')")
            assert "./fixtures/input.csv" in offline.locator("#preview-next").inner_text()
            report.append("direct file:// offline opening works in Chromium")
            print(json.dumps({"status": "PASS", "browser": browser.version, "checks": report}, indent=2))
        finally:
            browser.close()
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)


if __name__ == "__main__":
    main()
