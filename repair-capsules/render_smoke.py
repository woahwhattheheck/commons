"""In-memory DOM/layout check; not a substitute for browser_smoke.py.

Requires Node.js, Playwright Python and Chromium. No URL navigation or policy
changes. The actual renderer receives a capsule sealed by the tested Node core;
this does not test browser Web Crypto, download, file import, or navigation.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent


def main():
    fixture = subprocess.run(
        ["node", "-e", "const rc=require('./capsule.js');"
         "(async()=>console.log(JSON.stringify(await rc.seal(rc.cleanFields(rc.demo('commons'))))))();"],
        cwd=ROOT, check=True, capture_output=True, text=True, timeout=15,
    )
    capsule = json.loads(fixture.stdout)
    html = (ROOT / "index.html").read_text(encoding="utf-8").replace(
        '<script src="capsule.js"></script>',
        "<script>" + (ROOT / "capsule.js").read_text(encoding="utf-8") + "</script>",
    )
    binary = os.environ.get("CHROMIUM_PATH") or shutil.which("chromium")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, **({"executable_path": binary} if binary else {}))
        try:
            page = browser.new_page(viewport={"width": 1360, "height": 1080})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.set_content(html, wait_until="load")
            page.evaluate("capsule => { populate(capsule); render(capsule); }", capsule)
            assert page.locator("h1").is_visible()
            assert "demo-new" in page.locator("#diff").inner_text()
            assert "demo-old" in page.locator("#diff").inner_text()
            assert "Compare the page revision" in page.locator("#preview-next").inner_text()
            widths = []
            for width in (1360, 390):
                page.set_viewport_size({"width": width, "height": 1080 if width > 800 else 844})
                actual = page.evaluate("document.documentElement.scrollWidth")
                assert actual <= width, f"Horizontal overflow: {actual} > {width}"
                widths.append({"viewport": width, "document": actual})
                if os.environ.get("SMOKE_ARTIFACT_DIR"):
                    target = Path(os.environ["SMOKE_ARTIFACT_DIR"])
                    target.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(target / f"repair-capsules-render-{width}.png"), full_page=True)
            capsule["next_action"] = '<img src=x onerror="window.capsuleExecuted=true"> evidence only'
            page.evaluate("capsule => render(capsule)", capsule)
            assert page.locator("#preview-next img").count() == 0
            assert page.evaluate("window.capsuleExecuted === undefined")
            page.locator("#private").fill("synthetic-private-value")
            page.locator("#clear").click()
            assert page.locator("#private").input_value() == ""
            assert page.locator("#inspection").is_hidden()
            assert not errors, errors
            print(json.dumps({"status": "PASS", "method": "in-memory DOM render only; no browser Web Crypto or navigation tested", "widths": widths, "script_errors": errors, "inert_html": True, "clear_workspace": True}, indent=2))
        finally:
            browser.close()


if __name__ == "__main__":
    main()
